"""Tests for patient onboarding — minimal patient through full pipeline."""

import json
import os
import tempfile
from datetime import date

import pytest

from src.utils.data_loader import (
    create_minimal_patient,
    save_patient,
    load_patient,
    list_patient_ids,
    DATA_DIR,
)
from src.utils.action_packet import validate_action_packet
from src.orchestrator.pipeline import run_pipeline


@pytest.fixture
def drug_db():
    from src.utils.data_loader import load_drug_database
    return load_drug_database()


@pytest.fixture
def alternatives():
    from src.utils.data_loader import load_alternatives
    return load_alternatives()


@pytest.fixture
def empty_signals():
    return {
        "symptoms": [],
        "side_effects": [],
        "adherence_signals": [],
        "questions": [],
        "barriers_mentioned": [],
        "mood": "",
    }


class TestCreateMinimalPatient:
    def test_returns_valid_structure(self):
        patient = create_minimal_patient(name="Test User", age=55, sex="M")
        assert patient["name"] == "Test User"
        assert patient["age"] == 55
        assert patient["sex"] == "M"
        assert isinstance(patient["labs"], dict)
        assert isinstance(patient["vitals"], dict)
        assert isinstance(patient["medications"], list)
        assert isinstance(patient["medical_history"], list)
        assert isinstance(patient["social_factors"], dict)
        assert isinstance(patient["adherence"], dict)

    def test_empty_labs_without_initial(self):
        patient = create_minimal_patient(name="Test", age=60, sex="F")
        for lab in ["potassium", "creatinine", "egfr", "bnp", "sodium"]:
            assert patient["labs"][lab] == []

    def test_default_ef_is_zero(self):
        patient = create_minimal_patient(name="Test", age=60, sex="F")
        assert patient["ejection_fraction"] == 0.0

    def test_custom_ef(self):
        patient = create_minimal_patient(
            name="Test", age=60, sex="F", ejection_fraction=0.35
        )
        assert patient["ejection_fraction"] == 0.35

    def test_custom_medical_history(self):
        patient = create_minimal_patient(
            name="Test", age=60, sex="F",
            medical_history=["hypertension", "diabetes"],
        )
        assert "hypertension" in patient["medical_history"]

    def test_initial_vitals(self):
        patient = create_minimal_patient(
            name="Vitals Test", age=65, sex="M",
            initial_vitals={"systolic_bp": 130, "diastolic_bp": 80, "heart_rate": 72},
        )
        today = date.today().isoformat()
        assert len(patient["vitals"]["systolic_bp"]) == 1
        assert patient["vitals"]["systolic_bp"][0]["value"] == 130
        assert patient["vitals"]["systolic_bp"][0]["date"] == today
        assert patient["vitals"]["diastolic_bp"][0]["value"] == 80
        assert patient["vitals"]["heart_rate"][0]["value"] == 72

    def test_initial_vitals_partial(self):
        patient = create_minimal_patient(
            name="Partial Vitals", age=65, sex="M",
            initial_vitals={"systolic_bp": 120},
        )
        assert len(patient["vitals"]["systolic_bp"]) == 1
        assert patient["vitals"]["diastolic_bp"] == []
        assert patient["vitals"]["heart_rate"] == []

    def test_initial_labs(self):
        patient = create_minimal_patient(
            name="Labs Test", age=65, sex="M",
            initial_labs={"potassium": 4.2, "creatinine": 1.1, "egfr": 65},
        )
        today = date.today().isoformat()
        assert len(patient["labs"]["potassium"]) == 1
        assert patient["labs"]["potassium"][0]["value"] == 4.2
        assert patient["labs"]["potassium"][0]["date"] == today
        assert patient["labs"]["creatinine"][0]["value"] == 1.1
        assert patient["labs"]["egfr"][0]["value"] == 65
        # bnp and sodium still empty
        assert patient["labs"]["bnp"] == []
        assert patient["labs"]["sodium"] == []

    def test_initial_labs_partial(self):
        patient = create_minimal_patient(
            name="Partial Labs", age=65, sex="M",
            initial_labs={"potassium": 4.0},
        )
        assert len(patient["labs"]["potassium"]) == 1
        assert patient["labs"]["creatinine"] == []
        assert patient["labs"]["egfr"] == []


class TestSavePatient:
    def test_save_and_load(self):
        patient = create_minimal_patient(name="Save Test", age=50, sex="M")
        pid = patient["patient_id"]
        path = os.path.join(DATA_DIR, "patients", f"patient_{pid}.json")
        try:
            save_patient(patient)
            loaded = load_patient(pid)
            assert loaded["name"] == "Save Test"
            assert loaded["age"] == 50
        finally:
            # Clean up
            if os.path.exists(path):
                os.remove(path)


class TestListPatientIds:
    def test_returns_sorted_list(self):
        ids = list_patient_ids()
        assert isinstance(ids, list)
        assert ids == sorted(ids)

    def test_empty_directory_returns_empty(self):
        # The directory can be empty (no demo patients)
        ids = list_patient_ids()
        assert isinstance(ids, list)


class TestMinimalPatientPipeline:
    """Run the full pipeline with a minimal patient (empty labs, vitals, meds, EF=0)."""

    def test_pipeline_with_empty_patient(self, drug_db, alternatives, empty_signals):
        patient = create_minimal_patient(name="Empty Patient", age=65, sex="F")
        # EF=0.0, empty labs, empty vitals, empty meds
        packets = run_pipeline(patient, empty_signals, drug_db, alternatives)
        assert isinstance(packets, list)
        assert len(packets) > 0

        for packet in packets:
            is_valid, errors = validate_action_packet(packet)
            assert is_valid, f"Invalid packet from {packet.get('tool_name')}: {errors}"

    def test_pipeline_with_ef_zero_no_bb_start(self, drug_db, alternatives, empty_signals):
        """EF=0.0 should be treated as unknown, NOT trigger beta blocker start."""
        patient = create_minimal_patient(name="EF Zero", age=65, sex="F")
        packets = run_pipeline(patient, empty_signals, drug_db, alternatives)

        bb_packets = [p for p in packets if p.get("tool_name") == "gdmt_engine"
                      and p.get("drug") == "carvedilol"]
        for p in bb_packets:
            assert p["decision"] != "start", \
                "EF=0.0 should not trigger beta blocker initiation"

    def test_pipeline_with_minimal_data(self, drug_db, alternatives, empty_signals):
        """Patient with some data but not all fields populated."""
        patient = create_minimal_patient(
            name="Partial Data",
            age=70,
            sex="M",
            ejection_fraction=0.30,
            nyha_class=3,
            medical_history=["heart_failure"],
        )
        packets = run_pipeline(patient, empty_signals, drug_db, alternatives)
        assert isinstance(packets, list)
        assert len(packets) > 0

        for packet in packets:
            is_valid, errors = validate_action_packet(packet)
            assert is_valid, f"Invalid packet from {packet.get('tool_name')}: {errors}"
            # Every packet must have a guideline citation
            assert packet.get("guideline"), \
                f"Missing guideline in {packet.get('tool_name')}"

    def test_pipeline_with_initial_vitals_and_labs(self, drug_db, alternatives, empty_signals):
        """Patient created with initial vitals and labs should produce meaningful packets."""
        patient = create_minimal_patient(
            name="Full Onboard",
            age=68,
            sex="F",
            ejection_fraction=0.30,
            nyha_class=2,
            weight_kg=75.0,
            medical_history=["heart_failure", "hypertension"],
            initial_vitals={"systolic_bp": 128, "diastolic_bp": 78, "heart_rate": 72},
            initial_labs={"potassium": 4.2, "creatinine": 1.0, "egfr": 68},
        )
        packets = run_pipeline(patient, empty_signals, drug_db, alternatives)
        assert isinstance(packets, list)
        assert len(packets) > 0

        for packet in packets:
            is_valid, errors = validate_action_packet(packet)
            assert is_valid, f"Invalid packet from {packet.get('tool_name')}: {errors}"
