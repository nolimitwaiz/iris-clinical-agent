"""FHIR R4 Mapper — converts internal patient schema to/from FHIR R4 Bundle.

Demonstrates EHR integration readiness without actual EHR connection.
Maps to standard FHIR R4 resources: Patient, MedicationRequest, Observation, Condition.
"""

from datetime import datetime
from typing import Any
import uuid


def _make_id() -> str:
    """Generate a UUID for FHIR resource IDs."""
    return str(uuid.uuid4())


def patient_to_fhir_bundle(patient: dict) -> dict:
    """Convert internal patient schema to a FHIR R4 Bundle.

    Creates a Bundle containing:
    - Patient resource (demographics)
    - MedicationRequest resources (current medications)
    - Observation resources (labs and vitals)
    - Condition resources (medical history)

    Args:
        patient: Internal patient data dictionary.

    Returns:
        FHIR R4 Bundle dictionary.
    """
    entries: list[dict] = []
    patient_id = patient.get("patient_id", "unknown")
    patient_ref = f"Patient/{patient_id}"

    # ── Patient Resource ──────────────────────────────────────────────
    name_parts = patient.get("name", "Unknown").split(" ", 1)
    given = name_parts[0] if name_parts else "Unknown"
    family = name_parts[1] if len(name_parts) > 1 else ""

    sex_map = {"M": "male", "F": "female", "U": "unknown"}

    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [
            {
                "use": "official",
                "family": family,
                "given": [given],
            }
        ],
        "gender": sex_map.get(patient.get("sex", "U"), "unknown"),
        "birthDate": _estimate_birth_year(patient.get("age", 0)),
    }

    if patient.get("height_cm"):
        patient_resource["extension"] = [
            {
                "url": "http://hl7.org/fhir/StructureDefinition/patient-height",
                "valueQuantity": {
                    "value": patient["height_cm"],
                    "unit": "cm",
                    "system": "http://unitsofmeasure.org",
                    "code": "cm",
                },
            }
        ]

    entries.append({
        "fullUrl": f"urn:uuid:{patient_id}",
        "resource": patient_resource,
        "request": {"method": "PUT", "url": patient_ref},
    })

    # ── Condition Resources (medical history) ─────────────────────────
    for condition_text in patient.get("medical_history", []):
        cond_id = _make_id()
        entries.append({
            "fullUrl": f"urn:uuid:{cond_id}",
            "resource": {
                "resourceType": "Condition",
                "id": cond_id,
                "subject": {"reference": patient_ref},
                "code": {
                    "text": condition_text,
                },
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ],
                },
            },
            "request": {"method": "PUT", "url": f"Condition/{cond_id}"},
        })

    # ── MedicationRequest Resources ───────────────────────────────────
    for med in patient.get("medications", []):
        med_id = _make_id()
        entries.append({
            "fullUrl": f"urn:uuid:{med_id}",
            "resource": {
                "resourceType": "MedicationRequest",
                "id": med_id,
                "status": "active",
                "intent": "order",
                "subject": {"reference": patient_ref},
                "medicationCodeableConcept": {
                    "text": med.get("drug", "Unknown"),
                },
                "dosageInstruction": [
                    {
                        "text": f"{med.get('dose_mg', 0)}mg {med.get('route', 'oral')} "
                                f"{med.get('frequency_per_day', 1)}x daily",
                        "doseAndRate": [
                            {
                                "doseQuantity": {
                                    "value": med.get("dose_mg", 0),
                                    "unit": "mg",
                                    "system": "http://unitsofmeasure.org",
                                    "code": "mg",
                                }
                            }
                        ],
                        "timing": {
                            "repeat": {
                                "frequency": med.get("frequency_per_day", 1),
                                "period": 1,
                                "periodUnit": "d",
                            }
                        },
                        "route": {
                            "text": med.get("route", "oral"),
                        },
                    }
                ],
                "authoredOn": med.get("start_date"),
            },
            "request": {"method": "PUT", "url": f"MedicationRequest/{med_id}"},
        })

    # ── Observation Resources (labs) ──────────────────────────────────
    lab_codes = {
        "potassium": {"code": "6298-4", "display": "Potassium", "unit": "mmol/L"},
        "creatinine": {"code": "2160-0", "display": "Creatinine", "unit": "mg/dL"},
        "egfr": {"code": "33914-3", "display": "eGFR", "unit": "mL/min/1.73m2"},
        "bnp": {"code": "30934-4", "display": "BNP", "unit": "pg/mL"},
        "sodium": {"code": "2951-2", "display": "Sodium", "unit": "mmol/L"},
    }

    for lab_name, readings in patient.get("labs", {}).items():
        loinc = lab_codes.get(lab_name, {"code": "unknown", "display": lab_name, "unit": ""})
        for reading in readings:
            obs_id = _make_id()
            entries.append({
                "fullUrl": f"urn:uuid:{obs_id}",
                "resource": {
                    "resourceType": "Observation",
                    "id": obs_id,
                    "status": "final",
                    "category": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "laboratory",
                                }
                            ],
                        }
                    ],
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": loinc["code"],
                                "display": loinc["display"],
                            }
                        ],
                        "text": loinc["display"],
                    },
                    "subject": {"reference": patient_ref},
                    "effectiveDateTime": reading.get("date"),
                    "valueQuantity": {
                        "value": reading.get("value"),
                        "unit": loinc["unit"],
                        "system": "http://unitsofmeasure.org",
                    },
                },
                "request": {"method": "PUT", "url": f"Observation/{obs_id}"},
            })

    # ── Observation Resources (vitals) ────────────────────────────────
    vital_codes = {
        "weight_kg": {"code": "29463-7", "display": "Body Weight", "unit": "kg"},
        "systolic_bp": {"code": "8480-6", "display": "Systolic Blood Pressure", "unit": "mmHg"},
        "diastolic_bp": {"code": "8462-4", "display": "Diastolic Blood Pressure", "unit": "mmHg"},
        "heart_rate": {"code": "8867-4", "display": "Heart Rate", "unit": "/min"},
    }

    for vital_name, readings in patient.get("vitals", {}).items():
        loinc = vital_codes.get(vital_name, {"code": "unknown", "display": vital_name, "unit": ""})
        for reading in readings:
            obs_id = _make_id()
            entries.append({
                "fullUrl": f"urn:uuid:{obs_id}",
                "resource": {
                    "resourceType": "Observation",
                    "id": obs_id,
                    "status": "final",
                    "category": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "vital-signs",
                                }
                            ],
                        }
                    ],
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": loinc["code"],
                                "display": loinc["display"],
                            }
                        ],
                        "text": loinc["display"],
                    },
                    "subject": {"reference": patient_ref},
                    "effectiveDateTime": reading.get("date"),
                    "valueQuantity": {
                        "value": reading.get("value"),
                        "unit": loinc["unit"],
                        "system": "http://unitsofmeasure.org",
                    },
                },
                "request": {"method": "PUT", "url": f"Observation/{obs_id}"},
            })

    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": entries,
    }


def fhir_bundle_to_patient(bundle: dict) -> dict:
    """Convert a FHIR R4 Bundle back to internal patient schema.

    Reverse mapping for import from EHR systems.

    Args:
        bundle: FHIR R4 Bundle dictionary.

    Returns:
        Internal patient data dictionary.
    """
    patient_data: dict[str, Any] = {
        "patient_id": "imported",
        "name": "Unknown",
        "age": 0,
        "sex": "U",
        "height_cm": 170.0,
        "weight_kg": 70.0,
        "ejection_fraction": 0.0,
        "nyha_class": 2,
        "medical_history": [],
        "allergies": [],
        "medications": [],
        "labs": {"potassium": [], "creatinine": [], "egfr": [], "bnp": [], "sodium": []},
        "vitals": {"weight_kg": [], "systolic_bp": [], "diastolic_bp": [], "heart_rate": []},
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
            "last_refill_date": datetime.now().date().isoformat(),
            "days_since_refill": 0,
            "refill_on_time": True,
            "reported_barriers": [],
        },
        "conversation_history": [],
    }

    sex_rmap = {"male": "M", "female": "F", "unknown": "U", "other": "U"}

    # Reverse LOINC code maps
    lab_code_map = {
        "6298-4": "potassium",
        "2160-0": "creatinine",
        "33914-3": "egfr",
        "30934-4": "bnp",
        "2951-2": "sodium",
    }
    vital_code_map = {
        "29463-7": "weight_kg",
        "8480-6": "systolic_bp",
        "8462-4": "diastolic_bp",
        "8867-4": "heart_rate",
    }

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            patient_data["patient_id"] = resource.get("id", "imported")
            names = resource.get("name", [])
            if names:
                given = " ".join(names[0].get("given", []))
                family = names[0].get("family", "")
                patient_data["name"] = f"{given} {family}".strip()
            patient_data["sex"] = sex_rmap.get(resource.get("gender", "unknown"), "U")
            birth = resource.get("birthDate")
            if birth:
                try:
                    birth_year = int(birth[:4])
                    patient_data["age"] = datetime.now().year - birth_year
                except (ValueError, IndexError):
                    pass

        elif rtype == "Condition":
            code = resource.get("code", {})
            text = code.get("text", "")
            if text:
                patient_data["medical_history"].append(text)

        elif rtype == "MedicationRequest":
            med_code = resource.get("medicationCodeableConcept", {})
            dosage = resource.get("dosageInstruction", [{}])[0]
            dose_rate = dosage.get("doseAndRate", [{}])[0]
            dose_qty = dose_rate.get("doseQuantity", {})
            timing = dosage.get("timing", {}).get("repeat", {})

            patient_data["medications"].append({
                "drug": med_code.get("text", "Unknown"),
                "dose_mg": dose_qty.get("value", 0),
                "frequency_per_day": timing.get("frequency", 1),
                "route": dosage.get("route", {}).get("text", "oral"),
                "start_date": resource.get("authoredOn", ""),
                "last_changed_date": resource.get("authoredOn", ""),
            })

        elif rtype == "Observation":
            codings = resource.get("code", {}).get("coding", [])
            loinc_code = codings[0].get("code", "") if codings else ""
            value_qty = resource.get("valueQuantity", {})
            obs_value = value_qty.get("value")
            obs_date = resource.get("effectiveDateTime", "")

            if obs_value is not None and obs_date:
                reading = {"value": obs_value, "date": obs_date}

                # Check labs
                lab_key = lab_code_map.get(loinc_code)
                if lab_key and lab_key in patient_data["labs"]:
                    patient_data["labs"][lab_key].append(reading)
                    continue

                # Check vitals
                vital_key = vital_code_map.get(loinc_code)
                if vital_key and vital_key in patient_data["vitals"]:
                    patient_data["vitals"][vital_key].append(reading)
                    if vital_key == "weight_kg":
                        patient_data["weight_kg"] = obs_value

    return patient_data


def _estimate_birth_year(age: int) -> str:
    """Estimate birth date from age (just the year)."""
    if age <= 0:
        return ""
    year = datetime.now().year - age
    return f"{year}-01-01"
