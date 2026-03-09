"""Medication Optimization Score (MOS) calculator.

Computes a 0-100 score reflecting how close a patient's GDMT regimen is to
guideline-directed target doses across the four GDMT pillars:
  - Beta Blocker (25 points)
  - ARNI / ACEi / ARB (25 points)
  - MRA (25 points)
  - SGLT2i (25 points)

Contraindicated pillars receive full credit (25/25) so patients are not
penalized for legitimate clinical reasons.
"""

BETA_BLOCKER_NAMES = ["carvedilol", "metoprolol succinate"]
ACEI_NAMES = ["lisinopril", "enalapril", "ramipril"]
ARB_NAMES = ["losartan", "valsartan"]
ARNI_NAMES = ["sacubitril/valsartan"]
MRA_NAMES = ["spironolactone", "eplerenone"]
SGLT2I_NAMES = ["dapagliflozin", "empagliflozin"]

MAX_PILLAR_SCORE = 25


def _find_med(patient: dict, drug_names: list[str]) -> dict | None:
    for med in patient.get("medications", []):
        if med["drug"].lower() in [n.lower() for n in drug_names]:
            return med
    return None


def _find_drug_db(drug_name: str, drug_db: list[dict]) -> dict | None:
    for d in drug_db:
        if d["drug_name"].lower() == drug_name.lower():
            return d
    return None


def _is_contraindicated(pillar: str, patient: dict, drug_db: list[dict]) -> bool:
    """Check if a pillar is contraindicated for this patient."""
    allergies = [a.lower() for a in patient.get("allergies", [])]
    history = [h.lower() for h in patient.get("medical_history", [])]

    if pillar == "SGLT2i":
        if "type_1_diabetes" in history:
            return True

    if pillar == "ARNI/ACEi/ARB":
        if "angioedema" in allergies or "angioedema" in history:
            # Check if they can still use ARB (angioedema only contraindicates ACEi/ARNI in some cases)
            # For simplicity, if on ARB it's not contraindicated
            pass

    # Check drug-level contraindications from drug_db
    pillar_drug_names = {
        "Beta Blocker": BETA_BLOCKER_NAMES,
        "ARNI/ACEi/ARB": ARNI_NAMES + ACEI_NAMES + ARB_NAMES,
        "MRA": MRA_NAMES,
        "SGLT2i": SGLT2I_NAMES,
    }

    for drug_name in pillar_drug_names.get(pillar, []):
        db_entry = _find_drug_db(drug_name, drug_db)
        if db_entry:
            for contra in db_entry.get("contraindications", []):
                if contra.lower() in history:
                    return True

    return False


def _score_pillar(
    current_dose: float | None,
    target_dose: float,
) -> int:
    """Score a single pillar based on current vs target dose."""
    if current_dose is None or target_dose <= 0:
        return 0
    ratio = min(current_dose / target_dose, 1.0)
    return round(ratio * MAX_PILLAR_SCORE)


def calculate_mos(patient: dict, drug_db: list[dict]) -> dict:
    """Calculate the Medication Optimization Score for a patient.

    Args:
        patient: Patient data dictionary.
        drug_db: Drug database (formulary).

    Returns:
        Dict with mos_score (0-100) and per-pillar breakdown.
    """
    pillars = []

    # 1. Beta Blocker
    bb_med = _find_med(patient, BETA_BLOCKER_NAMES)
    bb_contraindicated = _is_contraindicated("Beta Blocker", patient, drug_db)
    if bb_contraindicated:
        pillars.append({
            "name": "Beta Blocker",
            "drug": bb_med["drug"] if bb_med else None,
            "current_dose_mg": bb_med["dose_mg"] if bb_med else None,
            "target_dose_mg": None,
            "score": MAX_PILLAR_SCORE,
            "max_score": MAX_PILLAR_SCORE,
            "status": "contraindicated",
        })
    elif bb_med:
        db_entry = _find_drug_db(bb_med["drug"], drug_db)
        target = db_entry["target_dose_mg"] if db_entry else 200.0
        score = _score_pillar(bb_med["dose_mg"], target)
        status = "at_target" if score >= MAX_PILLAR_SCORE else "below_target"
        pillars.append({
            "name": "Beta Blocker",
            "drug": bb_med["drug"],
            "current_dose_mg": bb_med["dose_mg"],
            "target_dose_mg": target,
            "score": score,
            "max_score": MAX_PILLAR_SCORE,
            "status": status,
        })
    else:
        pillars.append({
            "name": "Beta Blocker",
            "drug": None,
            "current_dose_mg": None,
            "target_dose_mg": None,
            "score": 0,
            "max_score": MAX_PILLAR_SCORE,
            "status": "not_started",
        })

    # 2. ARNI / ACEi / ARB (pick whichever is active, prefer ARNI)
    raas_med = _find_med(patient, ARNI_NAMES) or _find_med(patient, ACEI_NAMES) or _find_med(patient, ARB_NAMES)
    raas_contraindicated = _is_contraindicated("ARNI/ACEi/ARB", patient, drug_db)
    if raas_contraindicated:
        pillars.append({
            "name": "ARNI/ACEi/ARB",
            "drug": raas_med["drug"] if raas_med else None,
            "current_dose_mg": raas_med["dose_mg"] if raas_med else None,
            "target_dose_mg": None,
            "score": MAX_PILLAR_SCORE,
            "max_score": MAX_PILLAR_SCORE,
            "status": "contraindicated",
        })
    elif raas_med:
        db_entry = _find_drug_db(raas_med["drug"], drug_db)
        target = db_entry["target_dose_mg"] if db_entry else 97.0
        score = _score_pillar(raas_med["dose_mg"], target)
        status = "at_target" if score >= MAX_PILLAR_SCORE else "below_target"
        pillars.append({
            "name": "ARNI/ACEi/ARB",
            "drug": raas_med["drug"],
            "current_dose_mg": raas_med["dose_mg"],
            "target_dose_mg": target,
            "score": score,
            "max_score": MAX_PILLAR_SCORE,
            "status": status,
        })
    else:
        pillars.append({
            "name": "ARNI/ACEi/ARB",
            "drug": None,
            "current_dose_mg": None,
            "target_dose_mg": None,
            "score": 0,
            "max_score": MAX_PILLAR_SCORE,
            "status": "not_started",
        })

    # 3. MRA
    mra_med = _find_med(patient, MRA_NAMES)
    mra_contraindicated = _is_contraindicated("MRA", patient, drug_db)
    if mra_contraindicated:
        pillars.append({
            "name": "MRA",
            "drug": mra_med["drug"] if mra_med else None,
            "current_dose_mg": mra_med["dose_mg"] if mra_med else None,
            "target_dose_mg": None,
            "score": MAX_PILLAR_SCORE,
            "max_score": MAX_PILLAR_SCORE,
            "status": "contraindicated",
        })
    elif mra_med:
        db_entry = _find_drug_db(mra_med["drug"], drug_db)
        target = db_entry["target_dose_mg"] if db_entry else 25.0
        score = _score_pillar(mra_med["dose_mg"], target)
        status = "at_target" if score >= MAX_PILLAR_SCORE else "below_target"
        pillars.append({
            "name": "MRA",
            "drug": mra_med["drug"],
            "current_dose_mg": mra_med["dose_mg"],
            "target_dose_mg": target,
            "score": score,
            "max_score": MAX_PILLAR_SCORE,
            "status": status,
        })
    else:
        pillars.append({
            "name": "MRA",
            "drug": None,
            "current_dose_mg": None,
            "target_dose_mg": None,
            "score": 0,
            "max_score": MAX_PILLAR_SCORE,
            "status": "not_started",
        })

    # 4. SGLT2i
    sglt2_med = _find_med(patient, SGLT2I_NAMES)
    sglt2_contraindicated = _is_contraindicated("SGLT2i", patient, drug_db)
    if sglt2_contraindicated:
        pillars.append({
            "name": "SGLT2i",
            "drug": sglt2_med["drug"] if sglt2_med else None,
            "current_dose_mg": sglt2_med["dose_mg"] if sglt2_med else None,
            "target_dose_mg": None,
            "score": MAX_PILLAR_SCORE,
            "max_score": MAX_PILLAR_SCORE,
            "status": "contraindicated",
        })
    elif sglt2_med:
        db_entry = _find_drug_db(sglt2_med["drug"], drug_db)
        target = db_entry["target_dose_mg"] if db_entry else 10.0
        score = _score_pillar(sglt2_med["dose_mg"], target)
        status = "at_target" if score >= MAX_PILLAR_SCORE else "below_target"
        pillars.append({
            "name": "SGLT2i",
            "drug": sglt2_med["drug"],
            "current_dose_mg": sglt2_med["dose_mg"],
            "target_dose_mg": target,
            "score": score,
            "max_score": MAX_PILLAR_SCORE,
            "status": status,
        })
    else:
        pillars.append({
            "name": "SGLT2i",
            "drug": None,
            "current_dose_mg": None,
            "target_dose_mg": None,
            "score": 0,
            "max_score": MAX_PILLAR_SCORE,
            "status": "not_started",
        })

    mos_score = sum(p["score"] for p in pillars)

    return {
        "mos_score": mos_score,
        "pillars": pillars,
    }
