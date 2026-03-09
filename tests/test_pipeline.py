"""Tests for the pipeline orchestrator."""

from datetime import date

import pytest

from src.utils.data_loader import load_patient, load_drug_database, load_alternatives
from src.utils.action_packet import validate_action_packet
from src.orchestrator.pipeline import run_pipeline

# Tests use a fixed reference date matching the sample patient data
TEST_REFERENCE_DATE = date(2026, 2, 28)


@pytest.fixture
def drug_db():
    return load_drug_database()


@pytest.fixture
def alternatives():
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


def _run(patient_id, drug_db, alternatives, empty_signals):
    patient = load_patient(patient_id)
    return run_pipeline(patient, empty_signals, drug_db, alternatives, reference_date=TEST_REFERENCE_DATE)


class TestPipelineStructure:
    def test_returns_list(self, drug_db, alternatives, empty_signals):
        packets = _run("001", drug_db, alternatives, empty_signals)
        assert isinstance(packets, list)

    def test_all_packets_valid(self, drug_db, alternatives, empty_signals):
        for pid in ["001", "002", "003", "004", "005"]:
            packets = _run(pid, drug_db, alternatives, empty_signals)
            for packet in packets:
                valid, errors = validate_action_packet(packet)
                assert valid, f"Patient {pid} invalid packet: {errors}"

    def test_minimum_packet_count(self, drug_db, alternatives, empty_signals):
        """Pipeline should produce at least 7 packets:
        adherence(1) + trajectory(1) + gdmt(2) + safety(2+) + barrier(1+) + escalation(1)
        """
        packets = _run("001", drug_db, alternatives, empty_signals)
        assert len(packets) >= 7

    def test_pipeline_order(self, drug_db, alternatives, empty_signals):
        """Verify packets appear in the expected tool order."""
        packets = _run("001", drug_db, alternatives, empty_signals)
        tool_names = [p["tool_name"] for p in packets]

        # First packet should be adherence
        assert tool_names[0] == "adherence_monitor"
        # Second should be trajectory
        assert tool_names[1] == "trajectory_analyzer"
        # Last should be escalation
        assert tool_names[-1] == "escalation_manager"
        # GDMT should appear before safety
        gdmt_indices = [i for i, t in enumerate(tool_names) if t == "gdmt_engine"]
        safety_indices = [i for i, t in enumerate(tool_names) if t == "safety_checker"]
        assert min(gdmt_indices) < min(safety_indices)


class TestPatient001Pipeline:
    def test_no_escalation(self, drug_db, alternatives, empty_signals):
        packets = _run("001", drug_db, alternatives, empty_signals)
        escalation = [p for p in packets if p["tool_name"] == "escalation_manager"]
        assert len(escalation) == 1
        assert escalation[0]["decision"] == "no_escalation"

    def test_bb_uptitration(self, drug_db, alternatives, empty_signals):
        packets = _run("001", drug_db, alternatives, empty_signals)
        gdmt = [p for p in packets if p["tool_name"] == "gdmt_engine"]
        bb_packet = [p for p in gdmt if p.get("drug") == "metoprolol succinate"]
        assert len(bb_packet) == 1
        assert bb_packet[0]["decision"] == "increase"

    def test_adherent(self, drug_db, alternatives, empty_signals):
        packets = _run("001", drug_db, alternatives, empty_signals)
        adh = [p for p in packets if p["tool_name"] == "adherence_monitor"]
        assert adh[0]["decision"] == "adherent"


class TestPatient002Pipeline:
    def test_diuretic_increase(self, drug_db, alternatives, empty_signals):
        packets = _run("002", drug_db, alternatives, empty_signals)
        gdmt = [p for p in packets if p["tool_name"] == "gdmt_engine"]
        diuretic = [p for p in gdmt if p.get("drug") == "furosemide"]
        assert len(diuretic) == 1
        assert diuretic[0]["decision"] == "increase"

    def test_trajectory_high(self, drug_db, alternatives, empty_signals):
        packets = _run("002", drug_db, alternatives, empty_signals)
        traj = [p for p in packets if p["tool_name"] == "trajectory_analyzer"]
        assert traj[0]["decision"] == "high"


class TestPatient003Pipeline:
    def test_safety_blocks_lisinopril(self, drug_db, alternatives, empty_signals):
        packets = _run("003", drug_db, alternatives, empty_signals)
        safety = [p for p in packets if p["tool_name"] == "safety_checker"]
        lisinopril = [p for p in safety if p.get("drug") == "lisinopril"]
        assert len(lisinopril) == 1
        assert lisinopril[0]["decision"] == "blocked"

    def test_safety_blocks_spironolactone(self, drug_db, alternatives, empty_signals):
        packets = _run("003", drug_db, alternatives, empty_signals)
        safety = [p for p in packets if p["tool_name"] == "safety_checker"]
        spiro = [p for p in safety if p.get("drug") == "spironolactone"]
        assert len(spiro) == 1
        assert spiro[0]["decision"] == "blocked"

    def test_escalation_triggered(self, drug_db, alternatives, empty_signals):
        packets = _run("003", drug_db, alternatives, empty_signals)
        esc = [p for p in packets if p["tool_name"] == "escalation_manager"]
        assert esc[0]["decision"] == "escalate"


class TestPatient004Pipeline:
    def test_non_adherent(self, drug_db, alternatives, empty_signals):
        packets = _run("004", drug_db, alternatives, empty_signals)
        adh = [p for p in packets if p["tool_name"] == "adherence_monitor"]
        assert adh[0]["decision"] == "non_adherent"

    def test_barriers_identified(self, drug_db, alternatives, empty_signals):
        packets = _run("004", drug_db, alternatives, empty_signals)
        barriers = [p for p in packets if p["tool_name"] == "barrier_planner"]
        has_barrier = any(p["decision"] == "barrier_identified" for p in barriers)
        assert has_barrier


class TestPatient005Pipeline:
    def test_critical_trajectory(self, drug_db, alternatives, empty_signals):
        packets = _run("005", drug_db, alternatives, empty_signals)
        traj = [p for p in packets if p["tool_name"] == "trajectory_analyzer"]
        assert traj[0]["decision"] == "critical"

    def test_escalation_triggered(self, drug_db, alternatives, empty_signals):
        packets = _run("005", drug_db, alternatives, empty_signals)
        esc = [p for p in packets if p["tool_name"] == "escalation_manager"]
        assert esc[0]["decision"] == "escalate"

    def test_escalation_urgent(self, drug_db, alternatives, empty_signals):
        packets = _run("005", drug_db, alternatives, empty_signals)
        esc = [p for p in packets if p["tool_name"] == "escalation_manager"]
        assert esc[0]["inputs_used"]["urgency_level"] == "urgent"

    def test_spironolactone_blocked(self, drug_db, alternatives, empty_signals):
        packets = _run("005", drug_db, alternatives, empty_signals)
        safety = [p for p in packets if p["tool_name"] == "safety_checker"]
        spiro = [p for p in safety if p.get("drug") == "spironolactone"]
        assert len(spiro) == 1
        assert spiro[0]["decision"] == "blocked"
