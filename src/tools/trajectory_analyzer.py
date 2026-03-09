"""Trajectory Analyzer tool.

Analyzes weight and vital sign trends from the patient's vitals data to detect
fluid retention, hypotension, and tachycardia. Returns a single Action Packet.
"""

from datetime import datetime, timedelta

from src.utils.action_packet import create_action_packet

KG_TO_LBS = 2.205


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO date string to a datetime object."""
    return datetime.fromisoformat(date_str)


def _get_readings_in_window(readings: list[dict], days: int) -> list[dict]:
    """Return readings within the last N days, sorted by date ascending."""
    if not readings:
        return []
    sorted_readings = sorted(readings, key=lambda r: r["date"])
    latest_date = _parse_date(sorted_readings[-1]["date"])
    cutoff = latest_date - timedelta(days=days)
    return [r for r in sorted_readings if _parse_date(r["date"]) >= cutoff]


def _find_reading_near_days_ago(
    sorted_readings: list[dict], target_days: int
) -> dict | None:
    """Find the reading closest to target_days ago from the latest reading.

    Searches within a 1 day tolerance window around the target date.
    Returns None if no reading is found within tolerance.
    """
    if not sorted_readings:
        return None
    latest_date = _parse_date(sorted_readings[-1]["date"])
    target_date = latest_date - timedelta(days=target_days)
    best = None
    best_diff = None
    for r in sorted_readings:
        diff = abs((_parse_date(r["date"]) - target_date).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best = r
    # Allow up to 1 day tolerance
    if best_diff is not None and best_diff <= 86400:
        return best
    return None


def _compute_composite_risk(
    weight_delta_5d_lbs: float,
    latest_sbp: float | None,
    latest_hr: float | None,
    patient: dict,
) -> dict:
    """Compute a composite decompensation risk score (0-100).

    Sub-scores weighted:
      - Weight trend (5d): 0.35
      - Blood pressure: 0.20
      - Heart rate: 0.15
      - Adherence: 0.15
      - BNP level: 0.15
    """
    # Weight trend score
    wd = abs(weight_delta_5d_lbs)
    if wd > 4:
        weight_score = 100.0
    elif wd > 2:
        weight_score = 50.0 + (wd - 2) / 2 * 50.0
    else:
        weight_score = wd / 2 * 50.0

    weight_detail = f"{weight_delta_5d_lbs:+.1f} lbs / 5 days"

    # BP score
    if latest_sbp is None:
        bp_score = 0.0
        bp_detail = "no data"
    elif latest_sbp < 85:
        bp_score = 90.0
        bp_detail = f"SBP {latest_sbp:.0f}"
    elif latest_sbp < 90:
        bp_score = 60.0
        bp_detail = f"SBP {latest_sbp:.0f}"
    elif latest_sbp < 100:
        bp_score = 30.0
        bp_detail = f"SBP {latest_sbp:.0f}"
    else:
        bp_score = 0.0
        bp_detail = f"SBP {latest_sbp:.0f}"

    # HR score
    if latest_hr is None:
        hr_score = 0.0
        hr_detail = "no data"
    elif latest_hr > 110:
        hr_score = 80.0
        hr_detail = f"HR {latest_hr:.0f}"
    elif latest_hr > 100:
        hr_score = 60.0
        hr_detail = f"HR {latest_hr:.0f}"
    elif latest_hr > 90:
        hr_score = 30.0
        hr_detail = f"HR {latest_hr:.0f}"
    else:
        hr_score = 0.0
        hr_detail = f"HR {latest_hr:.0f}"

    # Adherence score
    adherence = patient.get("adherence", {})
    days_since_refill = adherence.get("days_since_refill", 0)
    if days_since_refill > 37:
        adh_score = 70.0
        adh_detail = f"{days_since_refill}d since refill"
    elif days_since_refill > 30:
        adh_score = 40.0
        adh_detail = f"{days_since_refill}d since refill"
    else:
        adh_score = 0.0
        adh_detail = "adherent"

    # BNP score
    bnp_values = patient.get("labs", {}).get("bnp", [])
    if bnp_values:
        bnp = bnp_values[-1]["value"]
    else:
        bnp = None

    if bnp is None:
        bnp_score = 0.0
        bnp_detail = "no data"
    elif bnp > 1000:
        bnp_score = 80.0
        bnp_detail = f"BNP {bnp:.0f}"
    elif bnp > 500:
        bnp_score = 50.0
        bnp_detail = f"BNP {bnp:.0f}"
    elif bnp > 300:
        bnp_score = 20.0
        bnp_detail = f"BNP {bnp:.0f}"
    else:
        bnp_score = 0.0
        bnp_detail = f"BNP {bnp:.0f}"

    # Weighted composite
    weights = {
        "weight_trend": 0.35,
        "blood_pressure": 0.20,
        "heart_rate": 0.15,
        "adherence": 0.15,
        "bnp": 0.15,
    }
    scores = {
        "weight_trend": weight_score,
        "blood_pressure": bp_score,
        "heart_rate": hr_score,
        "adherence": adh_score,
        "bnp": bnp_score,
    }
    details = {
        "weight_trend": weight_detail,
        "blood_pressure": bp_detail,
        "heart_rate": hr_detail,
        "adherence": adh_detail,
        "bnp": bnp_detail,
    }

    composite = 0.0
    components = {}
    for key in weights:
        contribution = scores[key] * weights[key]
        composite += contribution
        components[key] = {
            "score": scores[key],
            "weight": weights[key],
            "contribution": round(contribution, 1),
            "detail": details[key],
        }

    composite = max(0, min(100, round(composite)))

    if composite <= 25:
        tier = "low"
    elif composite <= 50:
        tier = "moderate"
    elif composite <= 70:
        tier = "high"
    else:
        tier = "critical"

    return {
        "composite": composite,
        "tier": tier,
        "components": components,
    }


# Symptoms that indicate fluid overload / decompensation
DECOMPENSATION_SYMPTOMS = [
    "edema", "swelling", "swollen", "ankle", "leg swelling",
    "shortness of breath", "breathless", "dyspnea", "orthopnea",
    "can't breathe", "trouble breathing", "waking up at night",
    "paroxysmal", "weight gain", "gained weight",
    "fatigue", "tired", "exhausted",
]


def analyze_trajectory(patient: dict, signals: dict | None = None) -> dict:
    """Analyze weight and vital sign trends for a heart failure patient.

    Args:
        patient: Patient data dictionary following the Patient Data Schema.
        signals: Optional extracted signals from the LLM extractor containing
            symptoms that may indicate decompensation.

    Returns:
        An Action Packet dictionary with the trajectory analysis results.
    """
    signals = signals or {}
    vitals = patient.get("vitals", {})

    # ── Weight analysis ──────────────────────────────────────────────────
    weight_readings = vitals.get("weight_kg", [])
    sorted_weights = sorted(weight_readings, key=lambda r: r["date"])

    latest_weight_kg = sorted_weights[-1]["value"] if sorted_weights else None

    weight_delta_3d_lbs = 0.0
    weight_delta_5d_lbs = 0.0
    weight_delta_7d_lbs = 0.0

    if sorted_weights and latest_weight_kg is not None:
        reading_3d = _find_reading_near_days_ago(sorted_weights, 3)
        reading_5d = _find_reading_near_days_ago(sorted_weights, 5)
        reading_7d = _find_reading_near_days_ago(sorted_weights, 7)

        if reading_3d is not None:
            weight_delta_3d_lbs = (latest_weight_kg - reading_3d["value"]) * KG_TO_LBS
        if reading_5d is not None:
            weight_delta_5d_lbs = (latest_weight_kg - reading_5d["value"]) * KG_TO_LBS
        if reading_7d is not None:
            weight_delta_7d_lbs = (latest_weight_kg - reading_7d["value"]) * KG_TO_LBS

    # ── Determine risk level based on weight thresholds ──────────────────
    risk = "low"
    weight_reason = "Weight is stable with no significant fluid retention trends"

    if weight_delta_3d_lbs > 3:
        risk = "critical"
        weight_reason = (
            f"Weight gained {weight_delta_3d_lbs:.1f} lbs over 3 days "
            "indicating rapid fluid retention requiring urgent assessment"
        )
    elif weight_delta_5d_lbs > 2:
        risk = "high"
        weight_reason = (
            f"Weight gained {weight_delta_5d_lbs:.1f} lbs over 5 days "
            "indicating fluid retention"
        )
    elif weight_delta_7d_lbs > 2:
        risk = "moderate"
        weight_reason = (
            f"Weight gained {weight_delta_7d_lbs:.1f} lbs over 7 days "
            "suggesting gradual fluid accumulation"
        )

    # ── SBP analysis ─────────────────────────────────────────────────────
    sbp_readings = vitals.get("systolic_bp", [])
    sorted_sbp = sorted(sbp_readings, key=lambda r: r["date"])
    latest_sbp = sorted_sbp[-1]["value"] if sorted_sbp else None

    flags: list[str] = []
    if latest_sbp is not None:
        if latest_sbp < 85:
            flags.append("severe hypotension")
        elif latest_sbp < 90:
            flags.append("hypotension")

    # ── HR analysis ──────────────────────────────────────────────────────
    hr_readings = vitals.get("heart_rate", [])
    sorted_hr = sorted(hr_readings, key=lambda r: r["date"])
    latest_hr = sorted_hr[-1]["value"] if sorted_hr else None

    if len(sorted_hr) >= 3:
        last_3_hr = sorted_hr[-3:]
        if all(r["value"] > 100 for r in last_3_hr):
            flags.append("sustained tachycardia")

    # ── Symptom-based risk boost from extracted signals ──────────────────
    reported_symptoms = signals.get("symptoms", [])
    decompensation_symptoms_found = []
    for symptom in reported_symptoms:
        symptom_lower = symptom.lower()
        for keyword in DECOMPENSATION_SYMPTOMS:
            if keyword in symptom_lower:
                decompensation_symptoms_found.append(symptom)
                break

    if decompensation_symptoms_found:
        flags.append(
            "patient reports: " + ", ".join(decompensation_symptoms_found)
        )
        # Boost risk level if symptoms corroborate or add to vitals data
        if risk == "low" and len(decompensation_symptoms_found) >= 2:
            risk = "moderate"
            weight_reason = (
                "Weight is stable but patient reports symptoms suggesting "
                "possible decompensation: "
                + ", ".join(decompensation_symptoms_found)
            )
        elif risk == "moderate":
            risk = "high"

    # ── Combine reason with flags ────────────────────────────────────────
    reason = weight_reason
    if flags:
        reason += ". Additional findings: " + ", ".join(flags)

    # ── Data quality assessment ──────────────────────────────────────────
    # Count unique dates across all vital types for data completeness
    all_dates: set[str] = set()
    for vital_type in ["weight_kg", "systolic_bp", "heart_rate"]:
        for r in vitals.get(vital_type, []):
            all_dates.add(r["date"][:10])  # use date part only

    total_vitals_days = len(all_dates)
    # 70% of 30 expected days = 21
    data_quality = None
    if total_vitals_days < 21:
        data_quality = (
            f"Insufficient data: only {total_vitals_days} days of vitals "
            "recorded out of expected 30 day window"
        )

    # ── Confidence based on weight reading count ─────────────────────────
    num_weight_readings = len(sorted_weights)
    if num_weight_readings >= 21:
        confidence = "high"
    elif num_weight_readings >= 14:
        confidence = "moderate"
    else:
        confidence = "low"

    # ── Monitoring recommendation ────────────────────────────────────────
    monitoring = None
    if risk != "low":
        monitoring = (
            "Daily weight monitoring, contact clinic if weight increases "
            "more than 2 lbs in 24 hours"
        )

    # ── Risk of inaction ─────────────────────────────────────────────────
    risk_of_inaction_map = {
        "low": "Continued monitoring is appropriate; no immediate risk identified",
        "moderate": (
            "Gradual fluid accumulation may worsen if not addressed, "
            "increasing risk of decompensation"
        ),
        "high": (
            "Undetected fluid overload may lead to acute decompensation "
            "and hospitalization"
        ),
        "critical": (
            "Rapid fluid retention poses immediate risk of acute "
            "decompensated heart failure requiring emergency intervention"
        ),
    }

    # ── Projected trajectories (linear extrapolation) ─────────────────
    projected_trajectories = []

    # Weight projection
    if len(sorted_weights) >= 3:
        recent_weights = sorted_weights[-3:]
        recent_values = [r["value"] for r in recent_weights]
        # Linear slope per day
        days_span = max(
            (_parse_date(recent_weights[-1]["date"]) - _parse_date(recent_weights[0]["date"])).days,
            1,
        )
        slope_per_day = (recent_values[-1] - recent_values[0]) / days_span
        projected_no_action = round(recent_values[-1] + slope_per_day * 30, 1)
        # With action: assume slope halved (intervention dampens trend)
        projected_with_action = round(recent_values[-1] + (slope_per_day * 0.3) * 30, 1)

        projected_trajectories.append({
            "metric": "weight_kg",
            "current_values": recent_values,
            "projected_30d_no_action": projected_no_action,
            "projected_30d_with_action": projected_with_action,
            "method": "linear_extrapolation",
            "confidence": confidence,
        })

    # SBP projection
    if len(sorted_sbp) >= 3:
        recent_sbp = sorted_sbp[-3:]
        sbp_values = [r["value"] for r in recent_sbp]
        days_span_sbp = max(
            (_parse_date(recent_sbp[-1]["date"]) - _parse_date(recent_sbp[0]["date"])).days,
            1,
        )
        sbp_slope = (sbp_values[-1] - sbp_values[0]) / days_span_sbp
        projected_trajectories.append({
            "metric": "systolic_bp",
            "current_values": sbp_values,
            "projected_30d_no_action": round(sbp_values[-1] + sbp_slope * 30, 1),
            "projected_30d_with_action": round(sbp_values[-1] + (sbp_slope * 0.3) * 30, 1),
            "method": "linear_extrapolation",
            "confidence": confidence,
        })

    # HR projection
    if len(sorted_hr) >= 3:
        recent_hr = sorted_hr[-3:]
        hr_values = [r["value"] for r in recent_hr]
        days_span_hr = max(
            (_parse_date(recent_hr[-1]["date"]) - _parse_date(recent_hr[0]["date"])).days,
            1,
        )
        hr_slope = (hr_values[-1] - hr_values[0]) / days_span_hr
        projected_trajectories.append({
            "metric": "heart_rate",
            "current_values": hr_values,
            "projected_30d_no_action": round(hr_values[-1] + hr_slope * 30, 1),
            "projected_30d_with_action": round(hr_values[-1] + (hr_slope * 0.3) * 30, 1),
            "method": "linear_extrapolation",
            "confidence": confidence,
        })

    packet = create_action_packet(
        tool_name="trajectory_analyzer",
        decision=risk,
        reason=reason,
        guideline="AHA/ACC 2022 HF Guideline Section 7.3.1",
        confidence=confidence,
        risk_of_inaction=risk_of_inaction_map[risk],
        inputs_used={
            "weight_readings": num_weight_readings,
            "latest_weight_kg": latest_weight_kg,
            "weight_delta_3d_lbs": round(weight_delta_3d_lbs, 2),
            "weight_delta_5d_lbs": round(weight_delta_5d_lbs, 2),
            "latest_sbp": latest_sbp,
            "latest_hr": latest_hr,
            "reported_symptoms": decompensation_symptoms_found,
        },
        drug=None,
        monitoring=monitoring,
        data_quality=data_quality,
    )

    # Attach projected trajectories to the packet
    if projected_trajectories:
        packet["projected_trajectories"] = projected_trajectories

    # Compute composite decompensation risk score
    packet["risk_score"] = _compute_composite_risk(
        weight_delta_5d_lbs, latest_sbp, latest_hr, patient
    )

    return packet
