"""Session-scoped test fixtures that generate test patient data.

The test suite requires 5 patient profiles with specific clinical characteristics
to exercise the full pipeline. These are generated at session start and cleaned
up at session end so the production data/patients/ directory can remain empty.
"""

import json
import os

import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PATIENTS_DIR = os.path.join(DATA_DIR, "patients")

# The GDMT engine uses REFERENCE_DATE = date(2026, 2, 28) for day calculations.
# All dates in test data are relative to that.

# ── Patient 001: Stable baseline ─────────────────────────────────────────────
# Trajectory: low (stable weight 30 days). BB: uptitrate metoprolol 25→50.
# Diuretic: maintain (no weight gain). Safety: all safe. Barriers: feasible.
# Escalation: no_escalation. Adherence: adherent.

def _make_patient_001():
    # 30 days of stable weight readings (~75 ± 0.2 kg)
    import random
    random.seed(1)
    weights = []
    for i in range(30):
        d = f"2026-01-{29 + i:02d}" if 29 + i <= 31 else (
            f"2026-02-{29 + i - 31:02d}"
        )
        # Generate dates from 2026-01-29 to 2026-02-27
        day_num = 29 + i
        if day_num <= 31:
            d = f"2026-01-{day_num:02d}"
        else:
            d = f"2026-02-{day_num - 31:02d}"
        weights.append({"value": 75.0 + random.uniform(-0.2, 0.2), "date": d})

    # SBP and HR for 30 days to get high data quality (>=21 unique dates)
    sbp_readings = [{"value": 115.0 + random.uniform(-3, 3), "date": w["date"]} for w in weights]
    hr_readings = [{"value": 72.0 + random.uniform(-2, 2), "date": w["date"]} for w in weights]

    return {
        "patient_id": "001",
        "name": "Maria Santos",
        "age": 67,
        "sex": "F",
        "height_cm": 165.0,
        "weight_kg": 75.0,
        "ejection_fraction": 0.35,
        "nyha_class": 2,
        "medical_history": ["heart_failure", "hypertension"],
        "allergies": [],
        "medications": [
            {
                "drug": "furosemide",
                "dose_mg": 40.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-12-01",
                "last_changed_date": "2025-12-01",
            },
            {
                "drug": "metoprolol succinate",
                "dose_mg": 25.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-12-01",
                "last_changed_date": "2026-01-15",
            },
        ],
        "labs": {
            "potassium": [{"value": 4.1, "date": "2026-02-27"}],
            "creatinine": [{"value": 1.0, "date": "2026-02-27"}],
            "egfr": [{"value": 65.0, "date": "2026-02-27"}],
            "bnp": [{"value": 250.0, "date": "2026-02-27"}],
            "sodium": [{"value": 140.0, "date": "2026-02-27"}],
        },
        "vitals": {
            "weight_kg": weights,
            "systolic_bp": sbp_readings,
            "diastolic_bp": [{"value": 70.0, "date": "2026-02-27"}],
            "heart_rate": hr_readings,
        },
        "social_factors": {
            "lives_alone": False,
            "insurance_tier": "tier1_generic",
            "income_bracket": "medium",
            "works_nights": False,
            "has_refrigeration": True,
            "pharmacy_distance_miles": 1.0,
            "health_literacy": "moderate",
            "preferred_language": "en",
        },
        "adherence": {
            "last_refill_date": "2026-02-19",
            "days_since_refill": 8,
            "refill_on_time": True,
            "reported_barriers": [],
        },
        "conversation_history": [],
    }


# ── Patient 002: Weight gain alert ──────────────────────────────────────────
# Trajectory: high (weight gain >2 lbs in 5 days).
# Diuretic: increase furosemide 40→80. Safety: safe.

def _make_patient_002():
    # Weight gain pattern: ~1.2kg over 5 days = ~2.65 lbs
    weights = [
        {"value": 87.0, "date": "2026-02-15"},
        {"value": 87.0, "date": "2026-02-17"},
        {"value": 87.0, "date": "2026-02-19"},
        {"value": 87.2, "date": "2026-02-22"},  # 5 days before latest
        {"value": 87.5, "date": "2026-02-24"},  # 3 days before latest
        {"value": 88.4, "date": "2026-02-27"},  # latest: 1.2kg > 87.2 = 2.65 lbs in 5d
    ]

    return {
        "patient_id": "002",
        "name": "James Mitchell",
        "age": 72,
        "sex": "M",
        "height_cm": 178.0,
        "weight_kg": 88.0,
        "ejection_fraction": 0.28,
        "nyha_class": 3,
        "medical_history": ["heart_failure", "hypertension", "atrial_fibrillation"],
        "allergies": [],
        "medications": [
            {
                "drug": "furosemide",
                "dose_mg": 40.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-11-01",
                "last_changed_date": "2025-11-01",
            },
            {
                "drug": "carvedilol",
                "dose_mg": 6.25,
                "frequency_per_day": 2,
                "route": "oral",
                "start_date": "2025-11-15",
                "last_changed_date": "2026-01-20",
            },
        ],
        "labs": {
            "potassium": [{"value": 4.0, "date": "2026-02-27"}],
            "creatinine": [{"value": 1.2, "date": "2026-02-27"}],
            "egfr": [{"value": 55.0, "date": "2026-02-27"}],
            "bnp": [{"value": 450.0, "date": "2026-02-27"}],
            "sodium": [{"value": 138.0, "date": "2026-02-27"}],
        },
        "vitals": {
            "weight_kg": weights,
            "systolic_bp": [{"value": 130.0, "date": "2026-02-27"}],
            "diastolic_bp": [{"value": 82.0, "date": "2026-02-27"}],
            "heart_rate": [{"value": 78.0, "date": "2026-02-27"}],
        },
        "social_factors": {
            "lives_alone": False,
            "insurance_tier": "tier2_preferred",
            "income_bracket": "medium",
            "works_nights": False,
            "has_refrigeration": True,
            "pharmacy_distance_miles": 2.0,
            "health_literacy": "moderate",
            "preferred_language": "en",
        },
        "adherence": {
            "last_refill_date": "2026-02-15",
            "days_since_refill": 12,
            "refill_on_time": True,
            "reported_barriers": [],
        },
        "conversation_history": [],
    }


# ── Patient 003: Safety blocks ──────────────────────────────────────────────
# K+ 5.1 blocks spironolactone. Cr rise 50% (1.2→1.8) blocks lisinopril.
# Escalation: escalate (safety blocked meds).

def _make_patient_003():
    return {
        "patient_id": "003",
        "name": "Robert Chen",
        "age": 58,
        "sex": "M",
        "height_cm": 175.0,
        "weight_kg": 82.0,
        "ejection_fraction": 0.30,
        "nyha_class": 2,
        "medical_history": ["heart_failure", "hypertension", "chronic_kidney_disease"],
        "allergies": [],
        "medications": [
            {
                "drug": "lisinopril",
                "dose_mg": 20.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-10-01",
                "last_changed_date": "2026-02-01",
            },
            {
                "drug": "spironolactone",
                "dose_mg": 25.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-10-01",
                "last_changed_date": "2025-10-01",
            },
            {
                "drug": "carvedilol",
                "dose_mg": 12.5,
                "frequency_per_day": 2,
                "route": "oral",
                "start_date": "2025-09-01",
                "last_changed_date": "2026-01-15",
            },
            {
                "drug": "furosemide",
                "dose_mg": 40.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-09-01",
                "last_changed_date": "2025-09-01",
            },
        ],
        "labs": {
            "potassium": [{"value": 5.1, "date": "2026-02-27"}],
            "creatinine": [
                {"value": 1.2, "date": "2026-02-01"},
                {"value": 1.8, "date": "2026-02-27"},
            ],
            "egfr": [{"value": 45.0, "date": "2026-02-27"}],
            "bnp": [{"value": 600.0, "date": "2026-02-27"}],
            "sodium": [{"value": 136.0, "date": "2026-02-27"}],
        },
        "vitals": {
            "weight_kg": [
                {"value": 82.0, "date": "2026-02-20"},
                {"value": 82.3, "date": "2026-02-24"},
                {"value": 82.5, "date": "2026-02-27"},
            ],
            "systolic_bp": [{"value": 110.0, "date": "2026-02-27"}],
            "diastolic_bp": [{"value": 68.0, "date": "2026-02-27"}],
            "heart_rate": [{"value": 68.0, "date": "2026-02-27"}],
        },
        "social_factors": {
            "lives_alone": False,
            "insurance_tier": "tier1_generic",
            "income_bracket": "medium",
            "works_nights": False,
            "has_refrigeration": True,
            "pharmacy_distance_miles": 1.5,
            "health_literacy": "moderate",
            "preferred_language": "en",
        },
        "adherence": {
            "last_refill_date": "2026-02-20",
            "days_since_refill": 7,
            "refill_on_time": True,
            "reported_barriers": [],
        },
        "conversation_history": [],
    }


# ── Patient 004: Adherence & cost barriers ──────────────────────────────────
# Non-adherent (35 days since refill). tier3_nonpreferred, low income.
# Lives alone, low literacy, pharmacy 8 miles. Barriers: identified.

def _make_patient_004():
    return {
        "patient_id": "004",
        "name": "Susan Williams",
        "age": 63,
        "sex": "F",
        "height_cm": 160.0,
        "weight_kg": 85.0,
        "ejection_fraction": 0.32,
        "nyha_class": 3,
        "medical_history": ["heart_failure", "diabetes", "hypertension"],
        "allergies": ["sulfa"],
        "medications": [
            {
                "drug": "furosemide",
                "dose_mg": 20.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-10-01",
                "last_changed_date": "2025-10-01",
            },
            {
                "drug": "metoprolol succinate",
                "dose_mg": 50.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-10-01",
                "last_changed_date": "2026-01-10",
            },
        ],
        "labs": {
            "potassium": [{"value": 4.3, "date": "2026-02-20"}],
            "creatinine": [{"value": 1.1, "date": "2026-02-20"}],
            "egfr": [{"value": 58.0, "date": "2026-02-20"}],
            "bnp": [{"value": 380.0, "date": "2026-02-20"}],
            "sodium": [{"value": 139.0, "date": "2026-02-20"}],
        },
        "vitals": {
            "weight_kg": [
                {"value": 85.0, "date": "2026-02-15"},
                {"value": 85.2, "date": "2026-02-20"},
                {"value": 85.3, "date": "2026-02-27"},
            ],
            "systolic_bp": [{"value": 125.0, "date": "2026-02-27"}],
            "diastolic_bp": [{"value": 78.0, "date": "2026-02-27"}],
            "heart_rate": [{"value": 70.0, "date": "2026-02-27"}],
        },
        "social_factors": {
            "lives_alone": True,
            "insurance_tier": "tier3_nonpreferred",
            "income_bracket": "low",
            "works_nights": False,
            "has_refrigeration": True,
            "pharmacy_distance_miles": 8.0,
            "health_literacy": "low",
            "preferred_language": "en",
        },
        "adherence": {
            "last_refill_date": "2026-01-23",
            "days_since_refill": 35,
            "refill_on_time": False,
            "reported_barriers": ["medication too expensive", "pharmacy too far"],
        },
        "conversation_history": [],
    }


# ── Patient 005: Critical deterioration ─────────────────────────────────────
# Critical trajectory (weight gain >3 lbs in 3 days, >5 lbs in 7 days).
# Furosemide >=80mg → recommend metolazone. Carvedilol at target → maintain.
# K+ 5.3, eGFR 28 → spironolactone blocked. BNP 1800.
# Escalation: escalate, urgency: urgent.

def _make_patient_005():
    # Weight readings to trigger critical trajectory:
    # 3-day delta: 95.5 - 93.5 = 2.0kg = 4.41 lbs > 3 ✓
    # 5-day delta: 95.5 - 93.3 = 2.2kg = 4.85 lbs > 2 ✓
    # 7-day delta: 95.5 - 93.0 = 2.5kg = 5.51 lbs > 5 ✓
    weights = [
        {"value": 93.0, "date": "2026-02-20"},  # 7 days before latest
        {"value": 93.3, "date": "2026-02-22"},  # 5 days before latest
        {"value": 93.5, "date": "2026-02-24"},  # 3 days before latest
        {"value": 94.5, "date": "2026-02-26"},
        {"value": 95.5, "date": "2026-02-27"},  # latest
    ]

    return {
        "patient_id": "005",
        "name": "David Thompson",
        "age": 78,
        "sex": "M",
        "height_cm": 180.0,
        "weight_kg": 95.0,
        "ejection_fraction": 0.20,
        "nyha_class": 4,
        "medical_history": [
            "heart_failure", "atrial_fibrillation", "chronic_kidney_disease",
            "diabetes", "hypertension",
        ],
        "allergies": [],
        "medications": [
            {
                "drug": "furosemide",
                "dose_mg": 80.0,
                "frequency_per_day": 2,
                "route": "oral",
                "start_date": "2025-08-01",
                "last_changed_date": "2026-01-01",
            },
            {
                "drug": "carvedilol",
                "dose_mg": 25.0,
                "frequency_per_day": 2,
                "route": "oral",
                "start_date": "2025-06-01",
                "last_changed_date": "2025-11-01",
            },
            {
                "drug": "spironolactone",
                "dose_mg": 25.0,
                "frequency_per_day": 1,
                "route": "oral",
                "start_date": "2025-08-01",
                "last_changed_date": "2025-08-01",
            },
        ],
        "labs": {
            "potassium": [{"value": 5.3, "date": "2026-02-27"}],
            "creatinine": [{"value": 2.0, "date": "2026-02-27"}],
            "egfr": [{"value": 28.0, "date": "2026-02-27"}],
            "bnp": [{"value": 1800.0, "date": "2026-02-27"}],
            "sodium": [{"value": 132.0, "date": "2026-02-27"}],
        },
        "vitals": {
            "weight_kg": weights,
            "systolic_bp": [{"value": 85.0, "date": "2026-02-27"}],
            "diastolic_bp": [{"value": 55.0, "date": "2026-02-27"}],
            "heart_rate": [{"value": 92.0, "date": "2026-02-27"}],
        },
        "social_factors": {
            "lives_alone": True,
            "insurance_tier": "tier2_preferred",
            "income_bracket": "low",
            "works_nights": False,
            "has_refrigeration": True,
            "pharmacy_distance_miles": 3.0,
            "health_literacy": "moderate",
            "preferred_language": "en",
        },
        "adherence": {
            "last_refill_date": "2026-02-15",
            "days_since_refill": 12,
            "refill_on_time": True,
            "reported_barriers": [],
        },
        "conversation_history": [],
    }


TEST_PATIENTS = {
    "001": _make_patient_001,
    "002": _make_patient_002,
    "003": _make_patient_003,
    "004": _make_patient_004,
    "005": _make_patient_005,
}


@pytest.fixture(scope="session", autouse=True)
def generate_test_patients():
    """Write test patient JSON files before the session and clean up after."""
    os.makedirs(PATIENTS_DIR, exist_ok=True)
    paths = []
    for pid, factory in TEST_PATIENTS.items():
        path = os.path.join(PATIENTS_DIR, f"patient_{pid}.json")
        with open(path, "w") as f:
            json.dump(factory(), f, indent=2)
        paths.append(path)

    yield

    # Clean up test patient files
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
