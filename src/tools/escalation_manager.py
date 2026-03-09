"""Escalation Manager tool.

Reviews all Action Packets from the entire pipeline and determines whether
clinician escalation is needed. Returns a single Action Packet.
"""

from datetime import datetime, timedelta

from src.utils.action_packet import create_action_packet

TOOL_NAME = "escalation_manager"
GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.9"

KG_TO_LBS = 2.205


def _get_latest_lab(patient: dict, lab_name: str) -> float | None:
    """Return the most recent lab value for a given lab type, or None."""
    labs = patient.get("labs", {}).get(lab_name, [])
    if not labs:
        return None
    sorted_labs = sorted(labs, key=lambda r: r["date"])
    return sorted_labs[-1]["value"]


def _get_latest_vitals(patient: dict, vital_name: str, count: int = 1) -> list[dict]:
    """Return the latest N vital sign readings, sorted by date ascending."""
    readings = patient.get("vitals", {}).get(vital_name, [])
    if not readings:
        return []
    sorted_readings = sorted(readings, key=lambda r: r["date"])
    return sorted_readings[-count:] if len(sorted_readings) >= count else sorted_readings


def _get_readings_in_window(readings: list[dict], days: int) -> list[dict]:
    """Return readings within the last N days, sorted by date ascending."""
    if not readings:
        return []
    sorted_readings = sorted(readings, key=lambda r: r["date"])
    latest_date = datetime.fromisoformat(sorted_readings[-1]["date"])
    cutoff = latest_date - timedelta(days=days)
    return [
        r for r in sorted_readings
        if datetime.fromisoformat(r["date"]) >= cutoff
    ]


def _weight_gain_7_days(patient: dict) -> float:
    """Calculate weight gain in lbs over the last 7 days.

    Returns 0.0 if insufficient data.
    """
    weight_readings = patient.get("vitals", {}).get("weight_kg", [])
    if not weight_readings:
        return 0.0

    sorted_weights = sorted(weight_readings, key=lambda r: r["date"])
    latest = sorted_weights[-1]
    latest_date = datetime.fromisoformat(latest["date"])
    target_date = latest_date - timedelta(days=7)

    # Find the reading closest to 7 days ago within 1 day tolerance
    best = None
    best_diff = None
    for r in sorted_weights:
        diff = abs((datetime.fromisoformat(r["date"]) - target_date).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best = r

    if best is None or best_diff is None or best_diff > 86400:
        return 0.0

    return (latest["value"] - best["value"]) * KG_TO_LBS


def _format_med_list(patient: dict) -> str:
    """Format the patient's medication list for the clinician summary."""
    meds = patient.get("medications", [])
    if not meds:
        return "No current medications on record"
    lines = []
    for med in meds:
        freq = med.get("frequency_per_day", 1)
        freq_str = f"{freq}x daily" if freq > 1 else "daily"
        lines.append(f"  {med['drug']} {med['dose_mg']}mg {freq_str}")
    return "\n".join(lines)


def _format_vital_trends(patient: dict, days: int = 3) -> str:
    """Format recent vital sign trends for the clinician summary."""
    parts: list[str] = []

    weight_readings = _get_readings_in_window(
        patient.get("vitals", {}).get("weight_kg", []), days
    )
    if weight_readings:
        vals = [f"{r['value']}kg ({r['date']})" for r in weight_readings[-3:]]
        parts.append(f"  Weight: {', '.join(vals)}")

    sbp_readings = _get_readings_in_window(
        patient.get("vitals", {}).get("systolic_bp", []), days
    )
    if sbp_readings:
        vals = [f"{r['value']} ({r['date']})" for r in sbp_readings[-3:]]
        parts.append(f"  SBP: {', '.join(vals)}")

    dbp_readings = _get_readings_in_window(
        patient.get("vitals", {}).get("diastolic_bp", []), days
    )
    if dbp_readings:
        vals = [f"{r['value']} ({r['date']})" for r in dbp_readings[-3:]]
        parts.append(f"  DBP: {', '.join(vals)}")

    hr_readings = _get_readings_in_window(
        patient.get("vitals", {}).get("heart_rate", []), days
    )
    if hr_readings:
        vals = [f"{r['value']} ({r['date']})" for r in hr_readings[-3:]]
        parts.append(f"  HR: {', '.join(vals)}")

    if not parts:
        return "  No recent vitals available"
    return "\n".join(parts)


def _format_latest_labs(patient: dict) -> str:
    """Format latest lab values for the clinician summary."""
    lab_names = ["potassium", "creatinine", "egfr", "bnp", "sodium"]
    parts: list[str] = []
    for lab_name in lab_names:
        val = _get_latest_lab(patient, lab_name)
        if val is not None:
            label = lab_name.upper() if lab_name in ("egfr", "bnp") else lab_name.capitalize()
            if lab_name == "potassium":
                label = "K+"
            elif lab_name == "creatinine":
                label = "Cr"
            parts.append(f"  {label}: {val}")
    if not parts:
        return "  No recent labs available"
    return "\n".join(parts)


def evaluate_escalation(all_packets: list[dict], patient: dict) -> dict:
    """Review all pipeline packets and determine if clinician escalation is needed.

    Args:
        all_packets: List of all Action Packets from the entire pipeline
            (trajectory, GDMT, safety, barriers).
        patient: Patient data dictionary following the Patient Data Schema.

    Returns:
        A single Action Packet with the escalation decision.
    """
    triggers: list[str] = []
    is_urgent = False

    # ── Trigger 1: Trajectory decision is "critical" ─────────────────────
    for packet in all_packets:
        if packet.get("tool_name") == "trajectory_analyzer":
            if packet.get("decision") == "critical":
                triggers.append("Trajectory analysis indicates critical status")
                is_urgent = True

    # ── Trigger 2: Safety blocked with no alternative ────────────────────
    blocked_drugs: list[str] = []
    for packet in all_packets:
        if packet.get("tool_name") == "safety_checker" and packet.get("decision") == "blocked":
            blocked_drugs.append(packet.get("drug", "unknown"))

    # Check if barrier planner found alternatives for the blocked drugs
    barrier_alternatives: set[str] = set()
    for packet in all_packets:
        if packet.get("tool_name") == "barrier_planner":
            inputs = packet.get("inputs_used", {})
            if inputs.get("alternative_suggested"):
                drug = inputs.get("drug", "")
                if drug:
                    barrier_alternatives.add(drug.lower())

    for drug in blocked_drugs:
        if drug and drug.lower() not in barrier_alternatives:
            triggers.append(
                f"Safety check blocked {drug} with no alternative available"
            )

    # ── Trigger 3: Potassium > 5.5 ──────────────────────────────────────
    potassium = _get_latest_lab(patient, "potassium")
    if potassium is not None and potassium > 5.5:
        triggers.append(f"Potassium critically elevated at {potassium}")
        is_urgent = True

    # ── Trigger 4: SBP < 85 AND declining ───────────────────────────────
    sbp_readings = _get_latest_vitals(patient, "systolic_bp", 2)
    if len(sbp_readings) >= 2:
        latest_sbp = sbp_readings[-1]["value"]
        previous_sbp = sbp_readings[-2]["value"]
        if latest_sbp < 85 and latest_sbp < previous_sbp:
            triggers.append(
                f"Systolic BP critically low at {latest_sbp} and declining "
                f"(previous reading: {previous_sbp})"
            )
            is_urgent = True

    # ── Trigger 5: eGFR < 15 ────────────────────────────────────────────
    egfr = _get_latest_lab(patient, "egfr")
    if egfr is not None and egfr < 15:
        triggers.append(f"eGFR critically low at {egfr}, nephrology input required")
        is_urgent = True

    # ── Trigger 6: BNP > 1000 ───────────────────────────────────────────
    bnp = _get_latest_lab(patient, "bnp")
    if bnp is not None and bnp > 1000:
        triggers.append(f"BNP critically elevated at {bnp}")

    # ── Trigger 7: Weight gain > 5 lbs in 7 days ────────────────────────
    weight_gain_7d = _weight_gain_7_days(patient)
    if weight_gain_7d > 5:
        triggers.append(
            f"Weight gain of {weight_gain_7d:.1f} lbs over 7 days "
            "indicating significant fluid retention"
        )

    # ── Build result ─────────────────────────────────────────────────────
    if triggers:
        # Determine urgency level
        if is_urgent:
            monitoring = "Urgent clinician review within 4 hours"
            urgency_level = "urgent"
        else:
            monitoring = "Clinician review within 24 hours"
            urgency_level = "routine"

        # Summarize what the pipeline attempted and what was blocked
        pipeline_attempted: list[str] = []
        pipeline_blocked: list[str] = []
        for packet in all_packets:
            tool = packet.get("tool_name", "unknown")
            pkt_decision = packet.get("decision", "unknown")
            drug = packet.get("drug")
            if pkt_decision == "blocked":
                drug_str = drug if drug else "unspecified"
                pipeline_blocked.append(f"{tool}: {drug_str} blocked")
            elif pkt_decision in ("increase", "start", "stop"):
                drug_str = drug if drug else "unspecified"
                pipeline_attempted.append(f"{tool}: {pkt_decision} {drug_str}")

        # Build the clinician summary
        patient_name = patient.get("name", "Unknown")
        patient_age = patient.get("age", "Unknown")
        patient_sex = patient.get("sex", "Unknown")

        clinician_summary = (
            f"ESCALATION SUMMARY\n"
            f"==================\n"
            f"Patient: {patient_name}, {patient_age}y {patient_sex}\n"
            f"Urgency: {urgency_level.upper()}\n"
            f"\n"
            f"Primary Concern:\n"
            f"  {'; '.join(triggers)}\n"
            f"\n"
            f"Vital Trends (last 3 days):\n"
            f"{_format_vital_trends(patient, days=3)}\n"
            f"\n"
            f"Latest Labs:\n"
            f"{_format_latest_labs(patient)}\n"
            f"\n"
            f"Current Medications:\n"
            f"{_format_med_list(patient)}\n"
            f"\n"
            f"Pipeline Actions Attempted:\n"
            f"  {'; '.join(pipeline_attempted) if pipeline_attempted else 'None'}\n"
            f"\n"
            f"Pipeline Actions Blocked:\n"
            f"  {'; '.join(pipeline_blocked) if pipeline_blocked else 'None'}\n"
            f"\n"
            f"Recommended Next Steps:\n"
            f"  {monitoring}\n"
        )

        reason = ". ".join(triggers)

        return create_action_packet(
            tool_name=TOOL_NAME,
            decision="escalate",
            reason=reason,
            guideline=GUIDELINE,
            confidence="high",
            risk_of_inaction=(
                "Delayed clinician involvement in deteriorating patient may "
                "result in preventable hospitalization or death"
            ),
            inputs_used={
                "triggers": triggers,
                "urgency_level": urgency_level,
                "clinician_summary": clinician_summary,
            },
            drug=None,
            monitoring=monitoring,
        )
    else:
        return create_action_packet(
            tool_name=TOOL_NAME,
            decision="no_escalation",
            reason="No escalation triggers met. Patient management can continue per protocol.",
            guideline=GUIDELINE,
            confidence="high",
            risk_of_inaction="No immediate risk requiring clinician involvement",
            inputs_used={
                "triggers": [],
                "urgency_level": "none",
            },
            drug=None,
            monitoring=None,
        )
