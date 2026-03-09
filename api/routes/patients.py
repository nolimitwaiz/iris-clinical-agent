"""Patient API routes."""

import random
import string

from fastapi import APIRouter, HTTPException

from api.schemas import PatientSummary, PatientDetail, PatientCreateRequest
from src.utils.data_loader import (
    load_patient,
    list_patient_ids,
    create_minimal_patient,
    save_patient,
)
from src.utils.fhir_mapper import patient_to_fhir_bundle

# In-memory share code store (prototype — single server)
_share_codes: dict[str, str] = {}  # code -> patient_id

router = APIRouter(tags=["patients"])


@router.get("/patients", response_model=list[PatientSummary])
async def list_patients():
    """List all available patients with summary info (dynamic directory scan)."""
    patients = []
    for pid in list_patient_ids():
        try:
            data = load_patient(pid)
            patients.append(
                PatientSummary(
                    patient_id=data["patient_id"],
                    name=data["name"],
                    age=data["age"],
                    sex=data["sex"],
                    ejection_fraction=data["ejection_fraction"],
                    nyha_class=data["nyha_class"],
                )
            )
        except (FileNotFoundError, KeyError):
            continue
    return patients


@router.post("/patients", response_model=PatientDetail)
async def create_patient(request: PatientCreateRequest):
    """Create a new patient from onboarding form data."""
    patient_data = create_minimal_patient(
        name=request.name,
        age=request.age,
        sex=request.sex,
        ejection_fraction=request.ejection_fraction,
        nyha_class=request.nyha_class,
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        medical_history=request.medical_history,
        allergies=request.allergies,
        medications=request.medications,
        insurance_tier=request.insurance_tier,
        initial_vitals=request.initial_vitals.model_dump(exclude_none=True) if request.initial_vitals else None,
        initial_labs=request.initial_labs.model_dump(exclude_none=True) if request.initial_labs else None,
    )
    save_patient(patient_data)
    return PatientDetail(**patient_data)


@router.post("/patients/start", response_model=PatientDetail)
async def start_patient():
    """Create an anonymous patient for conversational onboarding."""
    patient_data = create_minimal_patient(name="New Patient", age=0, sex="U")
    save_patient(patient_data)
    return PatientDetail(**patient_data)


@router.post("/patients/{patient_id}/share")
async def share_patient(patient_id: str):
    """Generate a 6-character share code for family/caregiver access."""
    lookup_id = patient_id.lstrip("P") if patient_id.startswith("P") else patient_id
    try:
        load_patient(lookup_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    # Check if code already exists for this patient
    for code, pid in _share_codes.items():
        if pid == lookup_id:
            return {"code": code, "patient_id": patient_id}

    # Generate new 6-char alphanumeric code
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    _share_codes[code] = lookup_id
    return {"code": code, "patient_id": patient_id}


@router.get("/family/{code}")
async def family_view(code: str):
    """Get simplified patient summary for family/caregiver view.

    Returns only non-clinical information: name, status, recent changes, next dates.
    No raw labs, no clinical detail. Share code is the access control.
    """
    code = code.upper()
    if code not in _share_codes:
        raise HTTPException(status_code=404, detail="Invalid share code")

    lookup_id = _share_codes[code]
    try:
        patient = load_patient(lookup_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Determine status from recent vitals
    vitals = patient.get("vitals", {})
    weights = sorted(vitals.get("weight_kg", []), key=lambda r: r["date"])
    status = "Stable"
    recent_changes = []

    if len(weights) >= 2:
        delta_kg = weights[-1]["value"] - weights[-2]["value"]
        delta_lbs = delta_kg * 2.205
        if delta_lbs > 2:
            status = "Needs Attention"
            recent_changes.append(f"Weight increased by {delta_lbs:.1f} lbs recently")
        elif delta_lbs > 3:
            status = "Urgent"
            recent_changes.append(f"Significant weight gain of {delta_lbs:.1f} lbs detected")
        else:
            recent_changes.append("Weight has been stable")

    # Get medication names for plain-language summary
    meds = patient.get("medications", [])
    if meds:
        med_names = [m.get("drug", "Unknown") for m in meds[:5]]
        recent_changes.append(f"Currently taking {len(meds)} medication(s): {', '.join(med_names)}")

    # Adherence info
    adherence = patient.get("adherence", {})
    if adherence.get("refill_on_time"):
        recent_changes.append("Medication refills are on time")
    elif adherence.get("days_since_refill", 0) > 30:
        status = "Needs Attention"
        recent_changes.append("May need medication refill")

    return {
        "name": patient.get("name", "Patient"),
        "age": patient.get("age"),
        "status": status,
        "recent_changes": recent_changes,
        "next_monitoring": "Daily weight check recommended" if status != "Stable" else "Regular check ins",
        "last_updated": weights[-1]["date"] if weights else None,
    }


@router.get("/patients/{patient_id}", response_model=PatientDetail)
async def get_patient(patient_id: str):
    """Get full patient detail by ID."""
    # Patient files are named patient_001.json but IDs come as P001
    lookup_id = patient_id.lstrip("P") if patient_id.startswith("P") else patient_id
    try:
        data = load_patient(lookup_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return PatientDetail(**data)


@router.get("/patients/{patient_id}/fhir")
async def get_patient_fhir(patient_id: str):
    """Export patient data as a FHIR R4 Bundle.

    Demonstrates EHR integration readiness. Returns a valid FHIR R4
    transaction Bundle with Patient, MedicationRequest, Observation,
    and Condition resources.
    """
    lookup_id = patient_id.lstrip("P") if patient_id.startswith("P") else patient_id
    try:
        data = load_patient(lookup_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient_to_fhir_bundle(data)
