"""Safety Checker tool.

Validates proposed medication changes against drug interactions,
contraindications, and lab values. Returns a list of safety Action Packets,
one per proposed change.
"""

from datetime import datetime, timedelta

from src.utils.action_packet import create_action_packet

# Drug classes used for interaction grouping
ACE_INHIBITORS = {"lisinopril", "enalapril", "ramipril"}
ARBS = {"losartan", "valsartan"}
ARNIS = {"sacubitril/valsartan"}
MRAS = {"spironolactone", "eplerenone"}
RAAS_DRUGS = ACE_INHIBITORS | ARBS | ARNIS | MRAS
NSAID_NAMES = {"ibuprofen", "naproxen", "celecoxib", "diclofenac", "meloxicam", "indomethacin", "aspirin_nsaid"}

TOOL_NAME = "safety_checker"
GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.4"


def _get_latest_lab(patient: dict, lab_name: str) -> float | None:
    """Return the most recent lab value for a given lab type, or None."""
    labs = patient.get("labs", {}).get(lab_name, [])
    if not labs:
        return None
    sorted_labs = sorted(labs, key=lambda r: r["date"])
    return sorted_labs[-1]["value"]


def _get_patient_drug_names(patient: dict) -> set[str]:
    """Return a set of all drug names the patient is currently taking."""
    return {med["drug"].lower() for med in patient.get("medications", [])}


def _find_drug_in_db(drug_name: str, drug_db: list[dict]) -> dict | None:
    """Look up a drug by name in the drug database."""
    for entry in drug_db:
        if entry["drug_name"].lower() == drug_name.lower():
            return entry
    return None


def _get_drug_class(drug_name: str, drug_db: list[dict]) -> str | None:
    """Return the drug_class for a drug name from the database."""
    entry = _find_drug_in_db(drug_name, drug_db)
    if entry:
        return entry["drug_class"]
    return None


def _patient_on_nsaid(patient: dict) -> bool:
    """Check if the patient is taking an NSAID or has NSAID in allergies list
    that might indicate current use (we check medications and allergies)."""
    drug_names = _get_patient_drug_names(patient)
    for name in drug_names:
        if name in NSAID_NAMES or "nsaid" in name.lower():
            return True
    # Also check medications list for NSAIDs listed in interactions
    for med in patient.get("medications", []):
        if med["drug"].lower() in NSAID_NAMES:
            return True
    return False


def _check_creatinine_rise(patient: dict, drug_name: str) -> dict | None:
    """Check if creatinine rose more than 30% after a recent ACEi/ARB/ARNI change.

    Looks at the medication's last_changed_date. If it was within the last 14
    days, compares oldest and newest creatinine in that window.

    Returns a dict with rise info if problematic, or None.
    """
    # Find the medication record for this drug
    med_record = None
    for med in patient.get("medications", []):
        if med["drug"].lower() == drug_name.lower():
            med_record = med
            break

    if med_record is None:
        return None

    last_changed = med_record.get("last_changed_date")
    if not last_changed:
        return None

    change_date = datetime.fromisoformat(last_changed)
    now = datetime.fromisoformat(
        sorted(patient.get("labs", {}).get("creatinine", []),
               key=lambda r: r["date"])[-1]["date"]
    ) if patient.get("labs", {}).get("creatinine") else datetime.now()

    days_since_change = (now - change_date).days
    if days_since_change > 14:
        return None

    # Get creatinine readings in the window since the change
    creatinine_readings = patient.get("labs", {}).get("creatinine", [])
    if len(creatinine_readings) < 2:
        return None

    sorted_cr = sorted(creatinine_readings, key=lambda r: r["date"])
    readings_in_window = [
        r for r in sorted_cr
        if datetime.fromisoformat(r["date"]) >= change_date
    ]

    if len(readings_in_window) < 2:
        # Use the reading just before the change as baseline
        readings_before = [
            r for r in sorted_cr
            if datetime.fromisoformat(r["date"]) <= change_date
        ]
        if not readings_before or not readings_in_window:
            return None
        baseline = readings_before[-1]["value"]
        latest = readings_in_window[-1]["value"]
    else:
        baseline = readings_in_window[0]["value"]
        latest = readings_in_window[-1]["value"]

    if baseline <= 0:
        return None

    rise_pct = ((latest - baseline) / baseline) * 100.0

    if rise_pct > 30:
        return {
            "baseline": baseline,
            "latest": latest,
            "rise_pct": round(rise_pct, 1),
            "days_since_change": days_since_change,
        }
    return None


def _check_creatinine_rise_broad(patient: dict, drug_name: str) -> dict | None:
    """Check if creatinine rose more than 30% since a medication was last changed.

    Similar to _check_creatinine_rise but uses a 30-day window instead of 14,
    for proactive detection of ongoing renal decline.
    """
    med_record = None
    for med in patient.get("medications", []):
        if med["drug"].lower() == drug_name.lower():
            med_record = med
            break

    if med_record is None:
        return None

    last_changed = med_record.get("last_changed_date")
    if not last_changed:
        return None

    change_date = datetime.fromisoformat(last_changed)
    creatinine_readings = patient.get("labs", {}).get("creatinine", [])
    if len(creatinine_readings) < 2:
        return None

    sorted_cr = sorted(creatinine_readings, key=lambda r: r["date"])
    now = datetime.fromisoformat(sorted_cr[-1]["date"])
    days_since_change = (now - change_date).days

    if days_since_change > 30:
        return None

    # Find baseline: reading closest to (at or before) the change date
    readings_before = [
        r for r in sorted_cr
        if datetime.fromisoformat(r["date"]) <= change_date
    ]
    if not readings_before:
        # Use the earliest reading as baseline
        baseline = sorted_cr[0]["value"]
    else:
        baseline = readings_before[-1]["value"]

    latest = sorted_cr[-1]["value"]

    if baseline <= 0:
        return None

    rise_pct = ((latest - baseline) / baseline) * 100.0
    if rise_pct > 30:
        return {
            "baseline": baseline,
            "latest": latest,
            "rise_pct": round(rise_pct, 1),
            "days_since_change": days_since_change,
        }
    return None


def _check_proactive_lab_safety(
    patient: dict,
    drug_db: list[dict],
    proposed_drugs: set[str],
) -> list[dict]:
    """Proactively check existing medications against current labs.

    Even when GDMT does not propose changes to a medication, dangerous lab
    values may require holding it. This function generates "hold" packets
    for medications not already addressed by GDMT proposals.
    """
    results: list[dict] = []
    potassium = _get_latest_lab(patient, "potassium")
    egfr = _get_latest_lab(patient, "egfr")

    for med in patient.get("medications", []):
        drug_name = med["drug"]
        drug_lower = drug_name.lower()

        # Skip drugs already evaluated in proposed changes
        if drug_lower in proposed_drugs:
            continue

        db_entry = _find_drug_in_db(drug_name, drug_db)
        drug_class = db_entry["drug_class"] if db_entry else None

        issues: list[str] = []
        monitoring_notes: list[str] = []

        # K+ > 5.5: hold ACEi/ARB/ARNI/MRA
        if potassium is not None and potassium > 5.5:
            if drug_class in ("ace_inhibitor", "arb", "arni", "mra"):
                issues.append(
                    f"Potassium critically elevated at {potassium}, "
                    f"hold {drug_name}"
                )
                monitoring_notes.append(
                    "Recheck potassium in 48 hours, hold ACEi/ARB/ARNI/MRA"
                )

        # K+ > 5.0: hold MRA and potassium supplements
        elif potassium is not None and potassium > 5.0:
            if drug_class == "mra" or drug_lower in (
                "potassium chloride", "potassium supplements"
            ):
                issues.append(
                    f"Potassium elevated at {potassium}, hold {drug_name}"
                )
                monitoring_notes.append("Recheck potassium in 48 hours")

        # eGFR < 15: flag for nephrology
        if egfr is not None and egfr < 15:
            if drug_class in ("ace_inhibitor", "arb", "arni", "mra"):
                issues.append(
                    f"eGFR critically low at {egfr}, hold {drug_name} "
                    "pending nephrology input"
                )
                monitoring_notes.append(
                    "Refer to nephrology before any medication adjustment"
                )

        # eGFR < 30: avoid/reduce spironolactone/eplerenone
        elif egfr is not None and egfr < 30:
            if drug_lower in ("spironolactone", "eplerenone"):
                issues.append(
                    f"eGFR below 30 at {egfr}, consider reducing or "
                    f"stopping {drug_name}"
                )
                monitoring_notes.append(
                    "Monitor renal function closely, consider nephrology consultation"
                )

        # Creatinine rise > 30% for ACEi/ARB/ARNI (broader window for proactive)
        if drug_class in ("ace_inhibitor", "arb", "arni"):
            cr_rise = _check_creatinine_rise_broad(patient, drug_name)
            if cr_rise is not None:
                issues.append(
                    f"Creatinine rose {cr_rise['rise_pct']}% after "
                    f"{drug_name}, hold medication and escalate"
                )
                monitoring_notes.append(
                    f"Creatinine baseline {cr_rise['baseline']} rose to "
                    f"{cr_rise['latest']} over {cr_rise['days_since_change']} days"
                )

        if issues:
            results.append(create_action_packet(
                tool_name=TOOL_NAME,
                decision="blocked",
                reason=". ".join(issues),
                guideline=GUIDELINE,
                confidence="high",
                risk_of_inaction=(
                    "Continuing medication with dangerous lab values "
                    "could cause life threatening complications"
                ),
                inputs_used={
                    "drug": drug_name,
                    "drug_class": drug_class,
                    "potassium": potassium,
                    "egfr": egfr,
                    "proactive_check": True,
                },
                drug=drug_name,
                current_dose_mg=med.get("dose_mg"),
                new_dose_mg=None,
                monitoring=". ".join(monitoring_notes) if monitoring_notes else None,
            ))

    return results


def check_safety(
    proposed_changes: list[dict],
    patient: dict,
    drug_db: list[dict],
) -> list[dict]:
    """Check each proposed medication change for safety concerns.

    Also proactively checks existing medications against current lab values
    even when no change is proposed (e.g. hold MRA if K+ > 5.0).

    Args:
        proposed_changes: List of Action Packets from the GDMT engine.
        patient: Patient data dictionary following the Patient Data Schema.
        drug_db: List of drug database entries.

    Returns:
        A list of safety Action Packets, one per proposed change evaluated,
        plus any proactive lab-based hold recommendations.
    """
    results: list[dict] = []

    # Gather patient context once
    current_drugs = _get_patient_drug_names(patient)
    potassium = _get_latest_lab(patient, "potassium")
    creatinine = _get_latest_lab(patient, "creatinine")
    egfr = _get_latest_lab(patient, "egfr")

    # Track which drugs are addressed by proposed changes
    proposed_drug_names: set[str] = set()
    for packet in proposed_changes:
        drug = packet.get("drug")
        if drug:
            proposed_drug_names.add(drug.lower())

    for packet in proposed_changes:
        decision = packet.get("decision", "")
        drug_name = packet.get("drug")
        print(f"DEBUG GDMT: {drug_name} = {decision}")

        # Evaluate all decisions except "stop" (stopping a drug is inherently resolving a safety issue)
        if decision == "stop":
            results.append(create_action_packet(
                tool_name=TOOL_NAME,
                decision="safe",
                reason=f"No safety evaluation needed for decision '{decision}'",
                guideline=GUIDELINE,
                confidence="high",
                risk_of_inaction="No risk identified for stopping a medication",
                inputs_used={"original_packet_decision": decision, "drug": drug_name},
                drug=drug_name,
                current_dose_mg=packet.get("current_dose_mg"),
                new_dose_mg=packet.get("new_dose_mg"),
                monitoring=None,
            ))
            continue

        if not drug_name:
            results.append(create_action_packet(
                tool_name=TOOL_NAME,
                decision="safe",
                reason="No drug specified in proposed change, no safety check applicable",
                guideline=GUIDELINE,
                confidence="high",
                risk_of_inaction="No drug to evaluate",
                inputs_used={"original_packet_decision": decision},
                drug=None,
                monitoring=None,
            ))
            continue

        drug_lower = drug_name.lower()
        db_entry = _find_drug_in_db(drug_name, drug_db)
        drug_class = db_entry["drug_class"] if db_entry else None

        issues: list[str] = []
        monitoring_notes: list[str] = []
        blocked = False

        # ── Drug interaction checks ──────────────────────────────────────

        # ARNI + ACE inhibitor
        if drug_lower in {d.lower() for d in ARNIS}:
            for ace in ACE_INHIBITORS:
                if ace in current_drugs:
                    issues.append(
                        "ARNI and ACE inhibitor combination is contraindicated. "
                        "36 hour washout required."
                    )
                    blocked = True
                    break
        elif drug_lower in {d.lower() for d in ACE_INHIBITORS}:
            for arni in ARNIS:
                if arni.lower() in current_drugs:
                    issues.append(
                        "ARNI and ACE inhibitor combination is contraindicated. "
                        "36 hour washout required."
                    )
                    blocked = True
                    break

        # ACE inhibitor + ARB (dual RAAS blockade)
        if drug_lower in {d.lower() for d in ACE_INHIBITORS}:
            for arb in ARBS:
                if arb.lower() in current_drugs:
                    issues.append("Dual RAAS blockade should be avoided")
                    blocked = True
                    break
        elif drug_lower in {d.lower() for d in ARBS}:
            for ace in ACE_INHIBITORS:
                if ace.lower() in current_drugs:
                    issues.append("Dual RAAS blockade should be avoided")
                    blocked = True
                    break

        # Potassium sparing diuretic (MRA) + potassium supplements
        if drug_lower in {d.lower() for d in MRAS}:
            if "potassium chloride" in current_drugs or "potassium supplements" in current_drugs:
                issues.append(
                    "High risk for hyperkalemia with potassium sparing diuretic "
                    "and MRA combination"
                )
                blocked = True
        elif drug_lower in ("potassium chloride", "potassium supplements"):
            for mra in MRAS:
                if mra.lower() in current_drugs:
                    issues.append(
                        "High risk for hyperkalemia with potassium sparing diuretic "
                        "and MRA combination"
                    )
                    blocked = True
                    break

        # NSAID + any HF medication
        if drug_lower in NSAID_NAMES or "nsaid" in drug_lower:
            issues.append(
                "NSAIDs should be avoided in heart failure as they worsen fluid retention"
            )
            blocked = True
        elif _patient_on_nsaid(patient):
            # The proposed drug interacts with active NSAID use
            if db_entry and "NSAIDs" in db_entry.get("interactions", []):
                issues.append(
                    "Patient is currently on an NSAID which worsens fluid retention "
                    "in heart failure. NSAID should be discontinued."
                )
                monitoring_notes.append("Recommend discontinuing NSAID use")

        # ── Lab based checks ─────────────────────────────────────────────

        # Potassium > 5.5: block ACEi/ARB/ARNI/MRA
        if potassium is not None and potassium > 5.5:
            if drug_class in ("ace_inhibitor", "arb", "arni", "mra"):
                issues.append(
                    f"Potassium critically elevated at {potassium}, urgent flag"
                )
                monitoring_notes.append(
                    "Recheck potassium in 48 hours, hold ACEi/ARB/ARNI/MRA"
                )
                blocked = True

        # Potassium > 5.0: block MRA and potassium supplements
        elif potassium is not None and potassium > 5.0:
            if drug_class == "mra" or drug_lower in ("potassium chloride", "potassium supplements"):
                issues.append(f"Potassium elevated at {potassium}")
                monitoring_notes.append("Recheck potassium in 48 hours")
                blocked = True

        # eGFR < 15: block most adjustments
        if egfr is not None and egfr < 15:
            issues.append("eGFR below 15, nephrology input required")
            monitoring_notes.append("Refer to nephrology before any medication adjustment")
            blocked = True

        # eGFR < 30: block spironolactone/eplerenone increases
        elif egfr is not None and egfr < 30:
            if drug_lower in ("spironolactone", "eplerenone"):
                issues.append("eGFR below 30, avoid or reduce MRA dose")
                monitoring_notes.append("Monitor renal function closely, consider nephrology consultation")
                blocked = True

        # ── Creatinine rise check for ACEi/ARB/ARNI ─────────────────────
        if drug_class in ("ace_inhibitor", "arb", "arni"):
            cr_rise = _check_creatinine_rise(patient, drug_name)
            if cr_rise is not None:
                issues.append(
                    "Creatinine rose more than 30% after recent ACEi/ARB/ARNI change, "
                    "hold medication and escalate"
                )
                monitoring_notes.append(
                    f"Creatinine baseline {cr_rise['baseline']} rose to {cr_rise['latest']} "
                    f"({cr_rise['rise_pct']}% increase over {cr_rise['days_since_change']} days)"
                )
                blocked = True

        # ── Build monitoring string ──────────────────────────────────────
        if not monitoring_notes:
            # Default monitoring for drug class changes
            if drug_class in ("ace_inhibitor", "arb", "arni"):
                monitoring_notes.append("Potassium and creatinine in 1 to 2 weeks after change")
            elif drug_class == "mra":
                monitoring_notes.append("Potassium in 1 week then monthly")
            elif drug_class == "loop_diuretic":
                monitoring_notes.append("BMP in 7 days after dose change")
            elif drug_class == "beta_blocker":
                monitoring_notes.append("Heart rate and blood pressure monitoring")
            else:
                monitoring_notes.append("Standard monitoring per prescribing guidelines")

        monitoring_str = ". ".join(monitoring_notes)

        # ── Build the safety packet ──────────────────────────────────────
        if blocked:
            reason = ". ".join(issues)
            risk_of_inaction = (
                "Proceeding with unsafe medication change could cause "
                "life threatening complications"
            )
            if potassium is not None and potassium > 5.5:
                risk_of_inaction = (
                    "Proceeding with unsafe medication change could cause "
                    "life threatening hyperkalemia"
                )

            results.append(create_action_packet(
                tool_name=TOOL_NAME,
                decision="blocked",
                reason=reason,
                guideline=GUIDELINE,
                confidence="high",
                risk_of_inaction=risk_of_inaction,
                inputs_used={
                    "proposed_decision": decision,
                    "drug": drug_name,
                    "current_drugs": sorted(current_drugs),
                    "potassium": potassium,
                    "creatinine": creatinine,
                    "egfr": egfr,
                    "issues_found": issues,
                },
                drug=drug_name,
                current_dose_mg=packet.get("current_dose_mg"),
                new_dose_mg=packet.get("new_dose_mg"),
                monitoring=monitoring_str,
            ))
        else:
            results.append(create_action_packet(
                tool_name=TOOL_NAME,
                decision="safe",
                reason=f"No safety concerns identified for {drug_name} {decision}",
                guideline=GUIDELINE,
                confidence="high",
                risk_of_inaction="No unsafe changes proposed, continued optimization is appropriate",
                inputs_used={
                    "proposed_decision": decision,
                    "drug": drug_name,
                    "current_drugs": sorted(current_drugs),
                    "potassium": potassium,
                    "creatinine": creatinine,
                    "egfr": egfr,
                },
                drug=drug_name,
                current_dose_mg=packet.get("current_dose_mg"),
                new_dose_mg=packet.get("new_dose_mg"),
                monitoring=monitoring_str,
            ))

    # Proactive lab-based safety checks on existing medications
    proactive_results = _check_proactive_lab_safety(
        patient, drug_db, proposed_drug_names
    )
    results.extend(proactive_results)

    return results
