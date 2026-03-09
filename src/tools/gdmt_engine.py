"""GDMT (Guideline-Directed Medical Therapy) Engine.

Evaluates the patient's current medications against evidence-based heart failure
guidelines and returns Action Packets recommending titration, initiation, or
holding of each drug class.

Implements all four GDMT pillars:
  - Beta blocker management (carvedilol / metoprolol succinate titration)
  - ACEi/ARB/ARNI management (sacubitril/valsartan switch and titration)
  - MRA management (spironolactone / eplerenone titration)
  - SGLT2i management (dapagliflozin / empagliflozin single dose)

Plus diuretic management (furosemide titration, metolazone add-on).
"""

from datetime import datetime, date

from src.utils.action_packet import create_action_packet

# Default reference date for day calculations.  In production this uses
# today's date.  Tests can override via the ``reference_date`` parameter
# on ``evaluate_gdmt``.
_DEFAULT_REFERENCE_DATE: date | None = None

DIURETIC_NAMES = ["furosemide", "bumetanide", "torsemide"]
BETA_BLOCKER_NAMES = ["carvedilol", "metoprolol succinate"]
ACE_INHIBITOR_NAMES = ["lisinopril", "enalapril", "ramipril"]
ARB_NAMES = ["losartan", "valsartan"]
ARNI_NAMES = ["sacubitril/valsartan"]
MRA_NAMES = ["spironolactone", "eplerenone"]
SGLT2I_NAMES = ["dapagliflozin", "empagliflozin"]

DIURETIC_GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.2"
BETA_BLOCKER_GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.3"
ARNI_GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.1"
MRA_GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.4"
SGLT2I_GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.5"

# ARNI titration ladder (sacubitril/valsartan doses)
ARNI_DOSES = [24.0, 49.0, 97.0]  # 24/26, 49/51, 97/103 mg BID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_drug_in_db(drug_name: str, drug_db: list[dict]) -> dict | None:
    """Look up a drug entry in the formulary database by name."""
    for d in drug_db:
        if d["drug_name"].lower() == drug_name.lower():
            return d
    return None


def _find_current_med(patient: dict, drug_names: list[str]) -> dict | None:
    """Find first matching medication from the patient's medication list."""
    for med in patient.get("medications", []):
        if med["drug"].lower() in [n.lower() for n in drug_names]:
            return med
    return None


def _days_since_last_change(med: dict, reference_date: date | None = None) -> int:
    """Return the number of days between the reference date and the
    medication's last_changed_date.

    Args:
        med: Medication dict with last_changed_date.
        reference_date: Date to compute from.  Defaults to today.
    """
    ref = reference_date or _DEFAULT_REFERENCE_DATE or date.today()
    last_changed = datetime.strptime(med["last_changed_date"], "%Y-%m-%d").date()
    return (ref - last_changed).days


def _next_titration_dose(current_dose: float, drug_db_entry: dict) -> float | None:
    """Return the next available dose above ``current_dose`` from the drug's
    titration ladder, or None if already at the maximum listed dose."""
    doses = sorted(drug_db_entry["available_doses_mg"])
    for dose in doses:
        if dose > current_dose:
            return dose
    return None


def _latest_lab(patient: dict, lab_name: str) -> float | None:
    """Return the most recent value for a lab, or None if unavailable."""
    labs = patient.get("labs", {}).get(lab_name, [])
    if not labs:
        return None
    return labs[-1]["value"]


def _latest_vital(patient: dict, vital_name: str) -> float | None:
    """Return the most recent value for a vital sign, or None if unavailable."""
    vitals = patient.get("vitals", {}).get(vital_name, [])
    if not vitals:
        return None
    return vitals[-1]["value"]


# ---------------------------------------------------------------------------
# Diuretic evaluation
# ---------------------------------------------------------------------------

def _evaluate_diuretics(
    patient: dict,
    trajectory_packet: dict,
    drug_db: list[dict],
) -> dict:
    """Evaluate diuretic therapy and return a single Action Packet."""

    current_med = _find_current_med(patient, DIURETIC_NAMES)
    current_drug = current_med["drug"] if current_med else None
    current_dose = current_med["dose_mg"] if current_med else None

    potassium = _latest_lab(patient, "potassium")
    egfr = _latest_lab(patient, "egfr")

    inputs_used = trajectory_packet.get("inputs_used", {})
    weight_delta_5d = inputs_used.get("weight_delta_5d_lbs", 0.0)
    weight_delta_3d = inputs_used.get("weight_delta_3d_lbs", 0.0)

    packet_inputs = {
        "current_drug": current_drug,
        "current_dose_mg": current_dose,
        "potassium": potassium,
        "egfr": egfr,
        "weight_delta_5d_lbs": weight_delta_5d,
        "weight_delta_3d_lbs": weight_delta_3d,
    }

    # Assess data quality
    data_quality = None
    if potassium is None or egfr is None:
        missing = []
        if potassium is None:
            missing.append("potassium")
        if egfr is None:
            missing.append("eGFR")
        data_quality = f"Missing lab data: {', '.join(missing)}"

    # ── Priority 1: eGFR too low ──────────────────────────────────────────
    if egfr is not None and egfr < 20:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold",
            drug=current_drug or "furosemide",
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason="eGFR below 20, nephrology input required before diuretic adjustment",
            guideline=DIURETIC_GUIDELINE,
            confidence="high",
            risk_of_inaction="Diuretic adjustment without nephrology guidance at eGFR < 20 risks acute kidney injury",
            inputs_used=packet_inputs,
            monitoring="Nephrology referral, BMP in 3 days",
            data_quality=data_quality,
        )

    # ── Priority 2: Hypokalemia ───────────────────────────────────────────
    if potassium is not None and potassium < 3.5:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold",
            drug=current_drug or "furosemide",
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason="Potassium below 3.5, hold diuretic increase, recommend potassium supplementation",
            guideline=DIURETIC_GUIDELINE,
            confidence="high",
            risk_of_inaction="Continued diuresis with low potassium increases risk of cardiac arrhythmia",
            inputs_used=packet_inputs,
            monitoring="Recheck potassium in 3 days",
            data_quality=data_quality,
        )

    # ── Priority 3: Rapid weight gain (> 3 lbs in 3 days) ────────────────
    if weight_delta_3d > 3:
        # Urgent flag -- still try to dose-adjust if on a diuretic
        if current_med is None:
            new_drug = "furosemide"
            new_dose = 20.0
            decision = "start"
            reason = (
                f"Rapid weight gain of {weight_delta_3d:.1f} lbs over 3 days "
                "with no current diuretic, urgent initiation recommended"
            )
        elif current_drug and current_drug.lower() == "furosemide":
            if current_dose < 40:
                new_drug = "furosemide"
                new_dose = 40.0
                decision = "increase"
            elif current_dose == 40:
                new_drug = "furosemide"
                new_dose = 80.0
                decision = "increase"
            else:
                new_drug = "metolazone"
                new_dose = 2.5
                decision = "increase"
            reason = (
                f"Rapid weight gain of {weight_delta_3d:.1f} lbs over 3 days, "
                "urgent diuretic escalation required"
            )
        else:
            # Non-furosemide diuretic -- flag for clinician
            new_drug = current_drug
            new_dose = None
            decision = "increase"
            reason = (
                f"Rapid weight gain of {weight_delta_3d:.1f} lbs over 3 days, "
                "urgent diuretic review required"
            )

        return create_action_packet(
            tool_name="gdmt_engine",
            decision=decision,
            drug=new_drug,
            current_dose_mg=current_dose,
            new_dose_mg=new_dose,
            reason=reason,
            guideline=DIURETIC_GUIDELINE,
            confidence="high",
            risk_of_inaction=(
                "Rapid fluid retention poses immediate risk of acute "
                "decompensated heart failure requiring emergency intervention"
            ),
            inputs_used=packet_inputs,
            monitoring="BMP in 7 days",
            data_quality=data_quality,
        )

    # ── Priority 4: Weight gain > 2 lbs in 5 days ────────────────────────
    if weight_delta_5d > 2 and (potassium is None or potassium >= 3.5) and (egfr is None or egfr >= 20):
        if current_med is None:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="start",
                drug="furosemide",
                current_dose_mg=None,
                new_dose_mg=20.0,
                reason=(
                    f"Weight gained {weight_delta_5d:.1f} lbs over 5 days with "
                    "signs of congestion, initiating furosemide"
                ),
                guideline=DIURETIC_GUIDELINE,
                confidence="high" if potassium is not None and egfr is not None else "moderate",
                risk_of_inaction="Untreated fluid retention will progress to symptomatic congestion and possible hospitalization",
                inputs_used=packet_inputs,
                monitoring="BMP in 7 days",
                data_quality=data_quality,
            )

        if current_drug and current_drug.lower() == "furosemide":
            if current_dose < 40:
                new_dose = 40.0
            elif current_dose == 40:
                new_dose = 80.0
            else:
                # >= 80 mg -- add metolazone
                return create_action_packet(
                    tool_name="gdmt_engine",
                    decision="increase",
                    drug="metolazone",
                    current_dose_mg=current_dose,
                    new_dose_mg=2.5,
                    reason=(
                        f"Weight gained {weight_delta_5d:.1f} lbs over 5 days, "
                        "already on furosemide >= 80 mg, consider adding metolazone or escalate to clinician"
                    ),
                    guideline=DIURETIC_GUIDELINE,
                    confidence="high",
                    risk_of_inaction="Persistent fluid retention despite high dose loop diuretic increases hospitalization risk",
                    inputs_used=packet_inputs,
                    monitoring="BMP in 7 days",
                    data_quality=data_quality,
                )

            return create_action_packet(
                tool_name="gdmt_engine",
                decision="increase",
                drug="furosemide",
                current_dose_mg=current_dose,
                new_dose_mg=new_dose,
                reason=(
                    f"Weight gained {weight_delta_5d:.1f} lbs over 5 days, "
                    "increasing furosemide for fluid management"
                ),
                guideline=DIURETIC_GUIDELINE,
                confidence="high",
                risk_of_inaction="Unaddressed fluid retention will worsen symptoms and may lead to hospitalization",
                inputs_used=packet_inputs,
                monitoring="BMP in 7 days",
                data_quality=data_quality,
            )

    # ── Priority 5: No weight gain trigger ────────────────────────────────
    return create_action_packet(
        tool_name="gdmt_engine",
        decision="maintain",
        drug=current_drug,
        current_dose_mg=current_dose,
        new_dose_mg=None,
        reason="No significant weight gain trend detected, maintaining current diuretic regimen",
        guideline=DIURETIC_GUIDELINE,
        confidence="high" if data_quality is None else "moderate",
        risk_of_inaction="Continued monitoring is appropriate; no immediate risk identified",
        inputs_used=packet_inputs,
        monitoring=None,
        data_quality=data_quality,
    )


# ---------------------------------------------------------------------------
# Beta-blocker evaluation
# ---------------------------------------------------------------------------

def _evaluate_beta_blockers(
    patient: dict,
    drug_db: list[dict],
    reference_date: date | None = None,
) -> dict:
    """Evaluate beta-blocker therapy and return a single Action Packet."""

    ef = patient.get("ejection_fraction")
    sbp = _latest_vital(patient, "systolic_bp")
    hr = _latest_vital(patient, "heart_rate")

    current_med = _find_current_med(patient, BETA_BLOCKER_NAMES)
    current_drug = current_med["drug"] if current_med else None
    current_dose = current_med["dose_mg"] if current_med else None

    packet_inputs = {
        "ejection_fraction": ef,
        "systolic_bp": sbp,
        "heart_rate": hr,
        "current_drug": current_drug,
        "current_dose_mg": current_dose,
    }

    data_quality = None
    if sbp is None or hr is None:
        missing = []
        if sbp is None:
            missing.append("systolic BP")
        if hr is None:
            missing.append("heart rate")
        data_quality = f"Missing vital data: {', '.join(missing)}"

    # ── Not on a beta blocker ─────────────────────────────────────────────
    if current_med is None:
        # Treat EF == 0.0 as "unknown/not measured" — a true EF of 0% is not
        # clinically plausible.  Without a real EF we cannot recommend initiation.
        if (
            ef is not None
            and ef > 0.0
            and ef <= 0.40
            and sbp is not None
            and sbp > 90
            and hr is not None
            and hr > 60
        ):
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="start",
                drug="carvedilol",
                current_dose_mg=None,
                new_dose_mg=3.125,
                reason="EF <= 40%, eligible for beta blocker initiation",
                guideline=BETA_BLOCKER_GUIDELINE,
                confidence="high" if data_quality is None else "moderate",
                risk_of_inaction="Delaying beta blocker initiation in HFrEF increases mortality risk",
                inputs_used=packet_inputs,
                monitoring="Heart rate and blood pressure in 1 to 2 weeks",
                data_quality=data_quality,
            )

        # Not eligible or data missing
        reasons = []
        if ef is None:
            reasons.append("ejection fraction data unavailable")
        elif ef > 0.40:
            reasons.append(f"EF is {ef*100:.0f}%, above 40% threshold")
        if sbp is not None and sbp <= 90:
            reasons.append(f"systolic BP is {sbp:.0f}, too low for initiation")
        if hr is not None and hr <= 60:
            reasons.append(f"heart rate is {hr:.0f}, too low for initiation")

        return create_action_packet(
            tool_name="gdmt_engine",
            decision="no_change",
            drug=None,
            current_dose_mg=None,
            new_dose_mg=None,
            reason="Beta blocker not indicated: " + "; ".join(reasons) if reasons else "Beta blocker not currently indicated",
            guideline=BETA_BLOCKER_GUIDELINE,
            confidence="high" if data_quality is None else "low",
            risk_of_inaction="No immediate risk; reassess at next visit",
            inputs_used=packet_inputs,
            monitoring=None,
            data_quality=data_quality,
        )

    # ── Currently on a beta blocker ───────────────────────────────────────
    days_since = _days_since_last_change(current_med, reference_date)
    packet_inputs["days_since_last_change"] = days_since

    db_entry = _find_drug_in_db(current_drug, drug_db)
    target_dose = db_entry["target_dose_mg"] if db_entry else None

    # Heart rate too low
    if hr is not None and hr < 55:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"Heart rate below 55 (current {hr:.0f}), consider dose reduction",
            guideline=BETA_BLOCKER_GUIDELINE,
            confidence="high",
            risk_of_inaction="Bradycardia may worsen with further titration; monitoring required",
            inputs_used=packet_inputs,
            monitoring="Heart rate and blood pressure in 1 to 2 weeks",
            data_quality=data_quality,
        )

    # Systolic BP too low
    if sbp is not None and sbp < 85:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"Systolic blood pressure below 85 (current {sbp:.0f}), hold uptitration",
            guideline=BETA_BLOCKER_GUIDELINE,
            confidence="high",
            risk_of_inaction="Hypotension risk increases with further titration",
            inputs_used=packet_inputs,
            monitoring="Heart rate and blood pressure in 1 to 2 weeks",
            data_quality=data_quality,
        )

    # Uptitration interval not met
    if days_since < 14:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="maintain",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"Uptitration interval not met, last change was {days_since} days ago",
            guideline=BETA_BLOCKER_GUIDELINE,
            confidence="high",
            risk_of_inaction="No immediate risk; uptitration should follow recommended interval",
            inputs_used=packet_inputs,
            monitoring=None,
            data_quality=data_quality,
        )

    # Eligible for uptitration: HR >= 60, SBP > 90, >= 14 days
    if (
        hr is not None
        and hr >= 60
        and sbp is not None
        and sbp > 90
        and db_entry is not None
    ):
        if target_dose is not None and current_dose >= target_dose:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug=current_drug,
                current_dose_mg=current_dose,
                new_dose_mg=None,
                reason="At target dose",
                guideline=BETA_BLOCKER_GUIDELINE,
                confidence="high",
                risk_of_inaction="No action needed; patient is at guideline recommended target dose",
                inputs_used=packet_inputs,
                monitoring=None,
                data_quality=data_quality,
            )

        next_dose = _next_titration_dose(current_dose, db_entry)
        if next_dose is not None:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="increase",
                drug=current_drug,
                current_dose_mg=current_dose,
                new_dose_mg=next_dose,
                reason=(
                    f"Eligible for uptitration: HR {hr:.0f}, SBP {sbp:.0f}, "
                    f"{days_since} days since last change"
                ),
                guideline=BETA_BLOCKER_GUIDELINE,
                confidence="high",
                risk_of_inaction="Delaying uptitration to target dose reduces potential mortality benefit",
                inputs_used=packet_inputs,
                monitoring="Heart rate and blood pressure in 1 to 2 weeks",
                data_quality=data_quality,
            )

    # Fallback: maintain
    return create_action_packet(
        tool_name="gdmt_engine",
        decision="maintain",
        drug=current_drug,
        current_dose_mg=current_dose,
        new_dose_mg=None,
        reason="Maintaining current beta blocker therapy",
        guideline=BETA_BLOCKER_GUIDELINE,
        confidence="moderate",
        risk_of_inaction="Continued monitoring is appropriate",
        inputs_used=packet_inputs,
        monitoring=None,
        data_quality=data_quality,
    )


# ---------------------------------------------------------------------------
# ARNI / ACEi / ARB evaluation
# ---------------------------------------------------------------------------

def _evaluate_arni_acei_arb(
    patient: dict,
    drug_db: list[dict],
    reference_date: date | None = None,
) -> dict:
    """Evaluate ARNI/ACEi/ARB therapy and return a single Action Packet."""

    ef = patient.get("ejection_fraction")
    sbp = _latest_vital(patient, "systolic_bp")
    egfr = _latest_lab(patient, "egfr")

    current_acei = _find_current_med(patient, ACE_INHIBITOR_NAMES)
    current_arb = _find_current_med(patient, ARB_NAMES)
    current_arni = _find_current_med(patient, ARNI_NAMES)

    # Determine which RAAS med is active
    current_med = current_arni or current_acei or current_arb
    current_drug = current_med["drug"] if current_med else None
    current_dose = current_med["dose_mg"] if current_med else None

    packet_inputs = {
        "ejection_fraction": ef,
        "systolic_bp": sbp,
        "egfr": egfr,
        "current_drug": current_drug,
        "current_dose_mg": current_dose,
    }

    data_quality = None
    if sbp is None:
        data_quality = "Missing vital data: systolic BP"

    # Check for angioedema history (contraindication for ARNI switch from ACEi)
    allergies = [a.lower() for a in patient.get("allergies", [])]
    history = [h.lower() for h in patient.get("medical_history", [])]
    has_angioedema = "angioedema" in allergies or "angioedema" in history

    # ── SBP too low: hold / do not initiate ────────────────────────────────
    if sbp is not None and sbp < 100:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold" if current_med else "no_change",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"Systolic BP {sbp:.0f} is below 100, {'holding' if current_med else 'not initiating'} ARNI/ACEi/ARB",
            guideline=ARNI_GUIDELINE,
            confidence="high",
            risk_of_inaction="Hypotension risk outweighs benefit of RAAS blockade initiation or uptitration",
            inputs_used=packet_inputs,
            monitoring="Blood pressure monitoring, reassess when SBP > 100",
            data_quality=data_quality,
        )

    # ── EF check: only recommend for HFrEF (EF <= 40%) ────────────────────
    if ef is None or ef > 0.40:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="maintain" if current_med else "no_change",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"EF {'unavailable' if ef is None else f'{ef*100:.0f}%'}, ARNI/ACEi/ARB {'maintained' if current_med else 'not indicated for HFpEF'}",
            guideline=ARNI_GUIDELINE,
            confidence="high" if ef is not None else "low",
            risk_of_inaction="No immediate risk; reassess at next visit",
            inputs_used=packet_inputs,
            monitoring=None,
            data_quality=data_quality,
        )

    # ── Currently on ACEi: recommend switch to ARNI ────────────────────────
    if current_acei:
        if has_angioedema:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug=current_acei["drug"],
                current_dose_mg=current_acei["dose_mg"],
                new_dose_mg=None,
                reason="History of angioedema contraindicates ARNI switch, maintaining ACEi",
                guideline=ARNI_GUIDELINE,
                confidence="high",
                risk_of_inaction="ACEi provides RAAS blockade; ARNI switch not possible due to angioedema risk",
                inputs_used=packet_inputs,
                monitoring=None,
                data_quality=data_quality,
            )

        days_since = _days_since_last_change(current_acei, reference_date)
        if days_since < 2:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug=current_acei["drug"],
                current_dose_mg=current_acei["dose_mg"],
                new_dose_mg=None,
                reason=f"ACEi last changed {days_since} days ago, 36 hour washout required before ARNI switch",
                guideline=ARNI_GUIDELINE,
                confidence="high",
                risk_of_inaction="Premature switch risks angioedema; wait for washout period",
                inputs_used=packet_inputs,
                monitoring="Recheck in 2 days for ARNI switch eligibility",
                data_quality=data_quality,
            )

        starting_dose = 24.0
        if egfr is not None and egfr < 30:
            monitoring = "BMP and renal function in 1 to 2 weeks, close monitoring for renal impairment"
        else:
            monitoring = "BMP in 1 to 2 weeks, blood pressure monitoring"

        return create_action_packet(
            tool_name="gdmt_engine",
            decision="start",
            drug="sacubitril/valsartan",
            current_dose_mg=current_acei["dose_mg"],
            new_dose_mg=starting_dose,
            reason=f"EF {ef*100:.0f}%, on ACEi, eligible for switch to ARNI (36h washout met, {days_since} days since last ACEi change)",
            guideline=ARNI_GUIDELINE,
            confidence="high",
            risk_of_inaction="ARNI provides superior mortality reduction over ACEi in HFrEF (PARADIGM-HF)",
            inputs_used=packet_inputs,
            monitoring=monitoring,
            data_quality=data_quality,
        )

    # ── Currently on ARB: recommend switch to ARNI ─────────────────────────
    if current_arb:
        starting_dose = 24.0
        monitoring = "BMP in 1 to 2 weeks, blood pressure monitoring"
        if egfr is not None and egfr < 30:
            monitoring = "BMP and renal function in 1 to 2 weeks, close monitoring for renal impairment"

        return create_action_packet(
            tool_name="gdmt_engine",
            decision="start",
            drug="sacubitril/valsartan",
            current_dose_mg=current_arb["dose_mg"],
            new_dose_mg=starting_dose,
            reason=f"EF {ef*100:.0f}%, on ARB, eligible for switch to ARNI (no washout needed)",
            guideline=ARNI_GUIDELINE,
            confidence="high",
            risk_of_inaction="ARNI provides superior mortality reduction over ARB in HFrEF",
            inputs_used=packet_inputs,
            monitoring=monitoring,
            data_quality=data_quality,
        )

    # ── Currently on ARNI ──────────────────────────────────────────────────
    if current_arni:
        db_entry = _find_drug_in_db("sacubitril/valsartan", drug_db)
        target_dose = db_entry["target_dose_mg"] if db_entry else 97.0
        days_since = _days_since_last_change(current_arni, reference_date)
        packet_inputs["days_since_last_change"] = days_since

        if current_dose >= target_dose:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug="sacubitril/valsartan",
                current_dose_mg=current_dose,
                new_dose_mg=None,
                reason="At target ARNI dose",
                guideline=ARNI_GUIDELINE,
                confidence="high",
                risk_of_inaction="No action needed; patient is at guideline recommended target dose",
                inputs_used=packet_inputs,
                monitoring=None,
                data_quality=data_quality,
            )

        if days_since < 14:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug="sacubitril/valsartan",
                current_dose_mg=current_dose,
                new_dose_mg=None,
                reason=f"ARNI uptitration interval not met, last change was {days_since} days ago",
                guideline=ARNI_GUIDELINE,
                confidence="high",
                risk_of_inaction="No immediate risk; uptitration should follow recommended interval",
                inputs_used=packet_inputs,
                monitoring=None,
                data_quality=data_quality,
            )

        # Uptitrate
        next_dose = None
        for d in ARNI_DOSES:
            if d > current_dose:
                next_dose = d
                break

        if next_dose:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="increase",
                drug="sacubitril/valsartan",
                current_dose_mg=current_dose,
                new_dose_mg=next_dose,
                reason=f"Eligible for ARNI uptitration: SBP {sbp:.0f}, {days_since} days since last change",
                guideline=ARNI_GUIDELINE,
                confidence="high",
                risk_of_inaction="Delaying uptitration to target dose reduces potential mortality benefit",
                inputs_used=packet_inputs,
                monitoring="BMP in 1 to 2 weeks, blood pressure monitoring",
                data_quality=data_quality,
            )

        # At max available dose
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="maintain",
            drug="sacubitril/valsartan",
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason="At maximum available ARNI dose",
            guideline=ARNI_GUIDELINE,
            confidence="high",
            risk_of_inaction="No action needed; at maximum dose",
            inputs_used=packet_inputs,
            monitoring=None,
            data_quality=data_quality,
        )

    # ── Not on any RAAS agent: start ARNI ──────────────────────────────────
    starting_dose = 24.0
    monitoring = "BMP in 1 to 2 weeks, blood pressure monitoring"
    if egfr is not None and egfr < 30:
        monitoring = "BMP and renal function in 1 to 2 weeks, close monitoring for renal impairment"

    return create_action_packet(
        tool_name="gdmt_engine",
        decision="start",
        drug="sacubitril/valsartan",
        current_dose_mg=None,
        new_dose_mg=starting_dose,
        reason=f"EF {ef*100:.0f}%, not on RAAS agent, initiating ARNI per guideline",
        guideline=ARNI_GUIDELINE,
        confidence="high",
        risk_of_inaction="Delaying ARNI initiation in HFrEF increases mortality and hospitalization risk",
        inputs_used=packet_inputs,
        monitoring=monitoring,
        data_quality=data_quality,
    )


# ---------------------------------------------------------------------------
# MRA evaluation
# ---------------------------------------------------------------------------

def _evaluate_mra(
    patient: dict,
    drug_db: list[dict],
    reference_date: date | None = None,
) -> dict:
    """Evaluate MRA (mineralocorticoid receptor antagonist) therapy."""

    ef = patient.get("ejection_fraction")
    nyha = patient.get("nyha_class", 0)
    potassium = _latest_lab(patient, "potassium")
    egfr = _latest_lab(patient, "egfr")

    current_med = _find_current_med(patient, MRA_NAMES)
    current_drug = current_med["drug"] if current_med else None
    current_dose = current_med["dose_mg"] if current_med else None

    packet_inputs = {
        "ejection_fraction": ef,
        "nyha_class": nyha,
        "potassium": potassium,
        "egfr": egfr,
        "current_drug": current_drug,
        "current_dose_mg": current_dose,
    }

    data_quality = None
    if potassium is None or egfr is None:
        missing = []
        if potassium is None:
            missing.append("potassium")
        if egfr is None:
            missing.append("eGFR")
        data_quality = f"Missing lab data: {', '.join(missing)}"

    # ── Potassium >= 5.5: stop MRA, escalate ───────────────────────────────
    if potassium is not None and potassium >= 5.5:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="stop" if current_med else "no_change",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"Potassium {potassium:.1f} >= 5.5, {'stop MRA and escalate' if current_med else 'MRA contraindicated'}",
            guideline=MRA_GUIDELINE,
            confidence="high",
            risk_of_inaction="Hyperkalemia risk is life threatening, immediate intervention required",
            inputs_used=packet_inputs,
            monitoring="Recheck potassium in 48 hours, urgent clinician review",
            data_quality=data_quality,
        )

    # ── Potassium >= 5.0: hold MRA ─────────────────────────────────────────
    if potassium is not None and potassium >= 5.0:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold" if current_med else "no_change",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"Potassium {potassium:.1f} >= 5.0, {'holding MRA' if current_med else 'MRA not safe to initiate'}",
            guideline=MRA_GUIDELINE,
            confidence="high",
            risk_of_inaction="Hyperkalemia risk requires monitoring before MRA adjustment",
            inputs_used=packet_inputs,
            monitoring="Recheck potassium in 3 to 5 days",
            data_quality=data_quality,
        )

    # ── eGFR < 30: avoid MRA ──────────────────────────────────────────────
    if egfr is not None and egfr < 30:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold" if current_med else "no_change",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason=f"eGFR {egfr:.0f} < 30, {'holding' if current_med else 'avoiding'} MRA due to renal impairment",
            guideline=MRA_GUIDELINE,
            confidence="high",
            risk_of_inaction="MRA use with eGFR < 30 significantly increases hyperkalemia risk",
            inputs_used=packet_inputs,
            monitoring="Renal function monitoring, nephrology input recommended",
            data_quality=data_quality,
        )

    # ── Currently on MRA ──────────────────────────────────────────────────
    if current_med:
        db_entry = _find_drug_in_db(current_drug, drug_db)
        target_dose = db_entry["target_dose_mg"] if db_entry else 25.0
        days_since = _days_since_last_change(current_med, reference_date)
        packet_inputs["days_since_last_change"] = days_since

        if current_dose >= target_dose:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug=current_drug,
                current_dose_mg=current_dose,
                new_dose_mg=None,
                reason="At target MRA dose",
                guideline=MRA_GUIDELINE,
                confidence="high",
                risk_of_inaction="No action needed; patient is at guideline recommended target dose",
                inputs_used=packet_inputs,
                monitoring="Potassium and renal function every 3 to 6 months",
                data_quality=data_quality,
            )

        if days_since < 14:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="maintain",
                drug=current_drug,
                current_dose_mg=current_dose,
                new_dose_mg=None,
                reason=f"MRA uptitration interval not met, last change was {days_since} days ago",
                guideline=MRA_GUIDELINE,
                confidence="high",
                risk_of_inaction="No immediate risk; uptitration should follow recommended interval",
                inputs_used=packet_inputs,
                monitoring=None,
                data_quality=data_quality,
            )

        # Uptitrate
        next_dose = _next_titration_dose(current_dose, db_entry) if db_entry else None
        if next_dose:
            return create_action_packet(
                tool_name="gdmt_engine",
                decision="increase",
                drug=current_drug,
                current_dose_mg=current_dose,
                new_dose_mg=next_dose,
                reason=f"Eligible for MRA uptitration: K+ {potassium:.1f}, eGFR {egfr:.0f}, {days_since} days since last change",
                guideline=MRA_GUIDELINE,
                confidence="high",
                risk_of_inaction="Delaying uptitration reduces potential mortality benefit",
                inputs_used=packet_inputs,
                monitoring="Potassium and creatinine in 1 to 2 weeks",
                data_quality=data_quality,
            )

        return create_action_packet(
            tool_name="gdmt_engine",
            decision="maintain",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason="Maintaining current MRA therapy",
            guideline=MRA_GUIDELINE,
            confidence="moderate",
            risk_of_inaction="Continued monitoring is appropriate",
            inputs_used=packet_inputs,
            monitoring=None,
            data_quality=data_quality,
        )

    # ── Not on MRA: evaluate for initiation ────────────────────────────────
    if (
        ef is not None
        and ef <= 0.35
        and nyha >= 2
        and (potassium is None or potassium < 5.0)
        and (egfr is None or egfr >= 30)
    ):
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="start",
            drug="spironolactone",
            current_dose_mg=None,
            new_dose_mg=12.5,
            reason=f"EF {ef*100:.0f}%, NYHA {nyha}, K+ {f'{potassium:.1f}' if potassium else 'N/A'}, eligible for MRA initiation",
            guideline=MRA_GUIDELINE,
            confidence="high" if potassium is not None and egfr is not None else "moderate",
            risk_of_inaction="Delaying MRA initiation in HFrEF with NYHA >= II increases mortality risk",
            inputs_used=packet_inputs,
            monitoring="Potassium and creatinine in 1 to 2 weeks",
            data_quality=data_quality,
        )

    # Not eligible
    reasons = []
    if ef is None or ef > 0.35:
        reasons.append(f"EF {'unavailable' if ef is None else f'{ef*100:.0f}%'}")
    if nyha < 2:
        reasons.append(f"NYHA {nyha}")
    return create_action_packet(
        tool_name="gdmt_engine",
        decision="no_change",
        drug=None,
        current_dose_mg=None,
        new_dose_mg=None,
        reason="MRA not indicated: " + ", ".join(reasons) if reasons else "MRA not currently indicated",
        guideline=MRA_GUIDELINE,
        confidence="high",
        risk_of_inaction="No immediate risk; reassess at next visit",
        inputs_used=packet_inputs,
        monitoring=None,
        data_quality=data_quality,
    )


# ---------------------------------------------------------------------------
# SGLT2i evaluation
# ---------------------------------------------------------------------------

def _evaluate_sglt2i(
    patient: dict,
    drug_db: list[dict],
) -> dict:
    """Evaluate SGLT2 inhibitor therapy."""

    ef = patient.get("ejection_fraction")
    egfr = _latest_lab(patient, "egfr")
    history = [h.lower() for h in patient.get("medical_history", [])]

    current_med = _find_current_med(patient, SGLT2I_NAMES)
    current_drug = current_med["drug"] if current_med else None
    current_dose = current_med["dose_mg"] if current_med else None

    packet_inputs = {
        "ejection_fraction": ef,
        "egfr": egfr,
        "current_drug": current_drug,
        "current_dose_mg": current_dose,
    }

    data_quality = None

    # ── Type 1 diabetes contraindication ───────────────────────────────────
    if "type_1_diabetes" in history:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="hold" if current_med else "no_change",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason="Type 1 diabetes is a contraindication for SGLT2i",
            guideline=SGLT2I_GUIDELINE,
            confidence="high",
            risk_of_inaction="SGLT2i contraindicated in type 1 diabetes due to DKA risk",
            inputs_used=packet_inputs,
            monitoring=None,
            data_quality=data_quality,
        )

    # ── Already on SGLT2i: maintain ────────────────────────────────────────
    if current_med:
        # Can continue even with eGFR < 20 if already on it
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="maintain",
            drug=current_drug,
            current_dose_mg=current_dose,
            new_dose_mg=None,
            reason="Maintaining current SGLT2i therapy (single fixed dose, no titration needed)",
            guideline=SGLT2I_GUIDELINE,
            confidence="high",
            risk_of_inaction="No action needed; patient is on SGLT2i therapy",
            inputs_used=packet_inputs,
            monitoring="Renal function monitoring per routine",
            data_quality=data_quality,
        )

    # ── eGFR < 20: do not initiate ────────────────────────────────────────
    if egfr is not None and egfr < 20:
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="no_change",
            drug=None,
            current_dose_mg=None,
            new_dose_mg=None,
            reason=f"eGFR {egfr:.0f} < 20, do not initiate SGLT2i",
            guideline=SGLT2I_GUIDELINE,
            confidence="high",
            risk_of_inaction="No immediate risk; SGLT2i initiation deferred until renal function improves",
            inputs_used=packet_inputs,
            monitoring="Monitor renal function, reassess when eGFR >= 20",
            data_quality=data_quality,
        )

    # ── EF <= 40% and eGFR >= 20: start ───────────────────────────────────
    if ef is not None and ef <= 0.40 and (egfr is None or egfr >= 20):
        return create_action_packet(
            tool_name="gdmt_engine",
            decision="start",
            drug="dapagliflozin",
            current_dose_mg=None,
            new_dose_mg=10.0,
            reason=f"EF {ef*100:.0f}%, eGFR {f'{egfr:.0f}' if egfr else 'N/A'}, eligible for SGLT2i initiation",
            guideline=SGLT2I_GUIDELINE,
            confidence="high" if egfr is not None else "moderate",
            risk_of_inaction="SGLT2i reduces HF hospitalization and cardiovascular death in HFrEF (DAPA-HF)",
            inputs_used=packet_inputs,
            monitoring="Renal function and volume status in 1 to 2 weeks",
            data_quality=data_quality,
        )

    # Not eligible
    return create_action_packet(
        tool_name="gdmt_engine",
        decision="no_change",
        drug=None,
        current_dose_mg=None,
        new_dose_mg=None,
        reason=f"SGLT2i not indicated: EF {'unavailable' if ef is None else f'{ef*100:.0f}%'}",
        guideline=SGLT2I_GUIDELINE,
        confidence="high" if ef is not None else "low",
        risk_of_inaction="No immediate risk; reassess at next visit",
        inputs_used=packet_inputs,
        monitoring=None,
        data_quality=data_quality,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def evaluate_gdmt(
    patient: dict,
    trajectory_packet: dict,
    drug_db: list[dict],
    reference_date: date | None = None,
) -> list[dict]:
    """Run the GDMT engine across all implemented drug classes.

    Args:
        patient: Patient data dictionary following the Patient Data Schema.
        trajectory_packet: Action Packet output from the Trajectory Analyzer,
            containing weight deltas in ``inputs_used``.
        drug_db: List of drug database entries (formulary).
        reference_date: Optional date to use for day calculations.  Defaults
            to today.  Pass a fixed date for reproducible tests.

    Returns:
        A list of Action Packets, one per evaluated drug class.
        Index order: 0=diuretic, 1=beta blocker, 2=ARNI/ACEi/ARB, 3=MRA, 4=SGLT2i.
    """
    ref = reference_date or _DEFAULT_REFERENCE_DATE or date.today()
    packets: list[dict] = []

    # 1. Diuretics
    packets.append(_evaluate_diuretics(patient, trajectory_packet, drug_db))

    # 2. Beta blockers
    packets.append(_evaluate_beta_blockers(patient, drug_db, reference_date=ref))

    # 3. ARNI / ACEi / ARB
    packets.append(_evaluate_arni_acei_arb(patient, drug_db, reference_date=ref))

    # 4. MRA
    packets.append(_evaluate_mra(patient, drug_db, reference_date=ref))

    # 5. SGLT2i
    packets.append(_evaluate_sglt2i(patient, drug_db))

    return packets
