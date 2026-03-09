"""Data loading utilities for patient profiles, drug database, and alternatives."""

import glob
import json
import os
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_patient(patient_id: str) -> dict:
    """Load a patient profile from data/patients/patient_{id}.json."""
    path = os.path.join(DATA_DIR, "patients", f"patient_{patient_id}.json")
    with open(path, "r") as f:
        return json.load(f)


def load_drug_database() -> list[dict]:
    """Load the heart failure drug database."""
    path = os.path.join(DATA_DIR, "drugs", "heart_failure_drugs.json")
    with open(path, "r") as f:
        return json.load(f)


def load_alternatives() -> list[dict]:
    """Load the drug alternatives mapping."""
    path = os.path.join(DATA_DIR, "mappings", "alternatives.json")
    with open(path, "r") as f:
        return json.load(f)


def get_drug_by_name(name: str, drug_db: list[dict]) -> dict | None:
    """Find a drug in the database by name (case insensitive)."""
    name_lower = name.lower()
    for drug in drug_db:
        if drug["drug_name"].lower() == name_lower:
            return drug
    return None


def get_drugs_by_class(drug_class: str, drug_db: list[dict]) -> list[dict]:
    """Filter drugs by class."""
    return [d for d in drug_db if d["drug_class"] == drug_class]


def list_patient_ids() -> list[str]:
    """Return sorted list of all patient IDs from data/patients/ directory."""
    patients_dir = os.path.join(DATA_DIR, "patients")
    ids = []
    for path in sorted(glob.glob(os.path.join(patients_dir, "patient_*.json"))):
        filename = os.path.basename(path)
        # patient_001.json -> 001
        pid = filename.replace("patient_", "").replace(".json", "")
        ids.append(pid)
    return ids


def _next_patient_id() -> str:
    """Generate the next patient ID (e.g. '006' if 5 patients exist)."""
    existing = list_patient_ids()
    if not existing:
        return "001"
    max_num = max(int(pid) for pid in existing)
    return f"{max_num + 1:03d}"


def validate_onboarding_data(data: dict, drug_db: list[dict] | None = None) -> tuple[dict, list[str]]:
    """Validate and sanitize onboarding data. Returns (cleaned_data, warnings).

    Enforces bounds on age, validates sex, and checks medication names
    against the drug database if provided.

    Args:
        data: Raw collected data from the onboarding session.
        drug_db: Optional drug database for medication name validation.

    Returns:
        Tuple of (cleaned data dict, list of warning strings).
    """
    cleaned = dict(data)
    warnings: list[str] = []

    # Age validation: must be 0-120
    age = cleaned.get("age")
    if age is not None:
        if not isinstance(age, (int, float)):
            try:
                age = int(age)
            except (TypeError, ValueError):
                age = 0
                warnings.append("Could not parse age, defaulting to 0")
        age = int(age)
        if age < 0 or age > 120:
            warnings.append(f"Age {age} is outside valid range (0 to 120), clamping")
            age = max(0, min(120, age))
        cleaned["age"] = age

    # Sex validation: must be M or F
    sex = cleaned.get("sex")
    if sex is not None:
        sex = str(sex).strip().upper()
        if sex not in ("M", "F"):
            warnings.append(f"Sex '{sex}' not recognized, defaulting to U")
            sex = "U"
        cleaned["sex"] = sex

    # Name validation: must not be empty
    name = cleaned.get("name")
    if name is not None:
        name = str(name).strip()
        if not name or len(name) < 2:
            warnings.append("Name is too short, defaulting to 'New Patient'")
            name = "New Patient"
        elif len(name) > 100:
            name = name[:100]
            warnings.append("Name truncated to 100 characters")
        cleaned["name"] = name

    # Medication name validation against drug database
    medications = cleaned.get("medications", [])
    if medications and drug_db:
        known_drugs = {d["drug_name"].lower() for d in drug_db}
        # Also accept brand names
        for d in drug_db:
            if d.get("brand_name"):
                known_drugs.add(d["brand_name"].lower())
        validated_meds = []
        for med in medications:
            med_name = med if isinstance(med, str) else str(med)
            if med_name.lower() in known_drugs:
                validated_meds.append(med_name)
            else:
                warnings.append(
                    f"Medication '{med_name}' not found in drug database, "
                    "keeping for manual review"
                )
                validated_meds.append(med_name)
        cleaned["medications"] = validated_meds

    # Insurance tier validation
    insurance = cleaned.get("insurance")
    valid_tiers = {"tier1_generic", "tier2_preferred", "tier3_nonpreferred", "uninsured"}
    if insurance is not None and insurance not in valid_tiers:
        warnings.append(f"Insurance tier '{insurance}' not recognized, defaulting to tier1_generic")
        cleaned["insurance"] = "tier1_generic"

    return cleaned, warnings


def create_minimal_patient(
    name: str,
    age: int,
    sex: str,
    ejection_fraction: float = 0.0,
    nyha_class: int = 2,
    weight_kg: float = 70.0,
    height_cm: float = 170.0,
    medical_history: list[str] | None = None,
    allergies: list[str] | None = None,
    medications: list[dict] | None = None,
    insurance_tier: str = "tier1_generic",
    initial_vitals: dict | None = None,
    initial_labs: dict | None = None,
) -> dict:
    """Create a valid patient dict with optional initial labs/vitals for onboarding."""
    pid = _next_patient_id()
    today = date.today().isoformat()

    # Build vitals arrays, seeding with initial values when provided
    vitals_data = initial_vitals or {}
    vitals = {
        "weight_kg": [{"value": weight_kg, "date": today}] if weight_kg else [],
        "systolic_bp": [{"value": vitals_data["systolic_bp"], "date": today}] if vitals_data.get("systolic_bp") else [],
        "diastolic_bp": [{"value": vitals_data["diastolic_bp"], "date": today}] if vitals_data.get("diastolic_bp") else [],
        "heart_rate": [{"value": vitals_data["heart_rate"], "date": today}] if vitals_data.get("heart_rate") else [],
    }

    # Build labs arrays, seeding with initial values when provided
    labs_data = initial_labs or {}
    labs = {
        "potassium": [{"value": labs_data["potassium"], "date": today}] if labs_data.get("potassium") else [],
        "creatinine": [{"value": labs_data["creatinine"], "date": today}] if labs_data.get("creatinine") else [],
        "egfr": [{"value": labs_data["egfr"], "date": today}] if labs_data.get("egfr") else [],
        "bnp": [],
        "sodium": [],
    }

    return {
        "patient_id": pid,
        "name": name,
        "age": age,
        "sex": sex,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "ejection_fraction": ejection_fraction,
        "nyha_class": nyha_class,
        "medical_history": medical_history or [],
        "allergies": allergies or [],
        "medications": medications or [],
        "labs": labs,
        "vitals": vitals,
        "social_factors": {
            "lives_alone": False,
            "insurance_tier": insurance_tier,
            "income_bracket": "medium",
            "works_nights": False,
            "has_refrigeration": True,
            "pharmacy_distance_miles": 1.0,
            "health_literacy": "moderate",
            "preferred_language": "en",
        },
        "adherence": {
            "last_refill_date": today,
            "days_since_refill": 0,
            "refill_on_time": True,
            "reported_barriers": [],
        },
        "conversation_history": [],
    }


def save_patient(patient_data: dict) -> str:
    """Save patient data to data/patients/patient_{id}.json.

    Returns the patient_id.
    """
    pid = patient_data["patient_id"]
    # Strip "P" prefix — IDs are "P001" but files are patient_001.json
    file_id = pid.lstrip("P") if pid.startswith("P") else pid
    patients_dir = os.path.join(DATA_DIR, "patients")
    os.makedirs(patients_dir, exist_ok=True)
    path = os.path.join(patients_dir, f"patient_{file_id}.json")
    with open(path, "w") as f:
        json.dump(patient_data, f, indent=2)
    return pid
