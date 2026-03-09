"""Tests for the Escalation Manager tool.

Validates that evaluate_escalation correctly identifies escalation triggers,
determines urgency levels, and generates clinician summaries when
escalation is warranted.
"""

from datetime import date

import pytest

from src.utils.data_loader import load_patient, load_drug_database, load_alternatives
from src.utils.action_packet import validate_action_packet
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.gdmt_engine import evaluate_gdmt
from src.tools.safety_checker import check_safety
from src.tools.barrier_planner import plan_barriers
from src.tools.escalation_manager import evaluate_escalation
from src.tools.adherence_monitor import check_adherence

TEST_REFERENCE_DATE = date(2026, 2, 28)


# ---------------------------------------------------------------------------
# Helper: run the full pipeline and collect all packets for escalation
# ---------------------------------------------------------------------------

def _run_escalation_pipeline(patient_id: str) -> dict:
    """Run the full pipeline (adherence + trajectory -> GDMT -> safety ->
    barriers -> escalation) for a given patient and return the escalation
    Action Packet.

    Collects all packets from every tool to pass to evaluate_escalation,
    matching the production pipeline behavior.
    """
    patient = load_patient(patient_id)
    drug_db = load_drug_database()
    alternatives = load_alternatives()

    all_packets: list[dict] = []

    # 1. Adherence
    adherence_packet = check_adherence(patient)
    all_packets.append(adherence_packet)

    # 2. Trajectory
    trajectory_packet = analyze_trajectory(patient)
    all_packets.append(trajectory_packet)

    # 3. GDMT
    gdmt_packets = evaluate_gdmt(patient, trajectory_packet, drug_db, reference_date=TEST_REFERENCE_DATE)
    all_packets.extend(gdmt_packets)

    # 4. Safety
    safety_results = check_safety(gdmt_packets, patient, drug_db)
    all_packets.extend(safety_results)

    # 5. Barriers (only for safe changes)
    safe_changes = [p for p in safety_results if p["decision"] == "safe"]
    barrier_results = plan_barriers(safe_changes, patient, drug_db, alternatives)
    all_packets.extend(barrier_results)

    # 6. Escalation
    escalation_packet = evaluate_escalation(all_packets, patient)
    return escalation_packet


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_action_packet_valid():
    """Escalation packet for every test patient must pass validate_action_packet."""
    for patient_id in ["001", "003", "005"]:
        packet = _run_escalation_pipeline(patient_id)
        is_valid, errors = validate_action_packet(packet)
        assert is_valid, (
            f"Patient {patient_id}: escalation packet failed validation: {errors}"
        )


def test_patient_001_no_escalation():
    """Patient 001 (stable, all safe, no critical labs) should not trigger escalation."""
    packet = _run_escalation_pipeline("001")
    assert packet["decision"] == "no_escalation", (
        f"Expected 'no_escalation' for stable patient 001, "
        f"got '{packet['decision']}'. Reason: {packet.get('reason')}"
    )


def test_patient_003_escalation():
    """Patient 003 should trigger escalation because safety blocked lisinopril
    (creatinine rise > 30%) and spironolactone (K+ > 5.0) with no alternatives
    resolving the block.

    The escalation manager fires when safety blocks medications and no
    barrier planner alternative is available for those blocked drugs.
    """
    packet = _run_escalation_pipeline("003")
    assert packet["decision"] == "escalate", (
        f"Expected 'escalate' for patient 003 (safety blocked lisinopril + "
        f"spironolactone), got '{packet['decision']}'. "
        f"Reason: {packet.get('reason')}"
    )


def test_patient_005_escalation():
    """Patient 005 (critical trajectory, BNP 1800, weight gain > 5 lbs in 7 days,
    K+ 5.3, eGFR 28) should trigger escalation.

    Multiple escalation triggers should fire:
    - Critical trajectory
    - BNP > 1000 (1800)
    - Weight gain > 5 lbs over 7 days
    - Safety blocked medications
    """
    packet = _run_escalation_pipeline("005")
    assert packet["decision"] == "escalate", (
        f"Expected 'escalate' for critical patient 005, "
        f"got '{packet['decision']}'. Reason: {packet.get('reason')}"
    )


def test_patient_005_urgent():
    """Patient 005 escalation should have urgency_level 'urgent' in inputs_used.

    Patient 005 has a critical trajectory (weight gain > 3 lbs in 3 days)
    which sets is_urgent to True, resulting in urgency_level 'urgent'.
    """
    packet = _run_escalation_pipeline("005")
    assert packet["decision"] == "escalate", (
        "Patient 005 must escalate for this test to be meaningful"
    )
    inputs = packet.get("inputs_used", {})
    assert inputs.get("urgency_level") == "urgent", (
        f"Expected urgency_level 'urgent' for patient 005, "
        f"got '{inputs.get('urgency_level')}'"
    )


def test_escalation_has_clinician_summary():
    """When escalation triggers, inputs_used should contain a clinician_summary
    string with structured clinical information for the reviewing clinician.
    """
    for patient_id in ["003", "005"]:
        packet = _run_escalation_pipeline(patient_id)
        if packet["decision"] != "escalate":
            pytest.skip(
                f"Patient {patient_id} did not escalate; skipping summary check"
            )
        inputs = packet.get("inputs_used", {})
        summary = inputs.get("clinician_summary")
        assert summary is not None, (
            f"Patient {patient_id}: escalated packet should have clinician_summary"
        )
        assert isinstance(summary, str), (
            f"Patient {patient_id}: clinician_summary should be a string"
        )
        assert len(summary) > 0, (
            f"Patient {patient_id}: clinician_summary should not be empty"
        )
        # The summary should contain key sections
        assert "ESCALATION SUMMARY" in summary, (
            f"Patient {patient_id}: clinician_summary should contain header"
        )


def test_escalation_guideline():
    """Escalation packets should cite AHA/ACC 2022 HF Guideline Section 7.3.9."""
    expected_guideline = "AHA/ACC 2022 HF Guideline Section 7.3.9"
    for patient_id in ["001", "003", "005"]:
        packet = _run_escalation_pipeline(patient_id)
        assert packet["guideline"] == expected_guideline, (
            f"Patient {patient_id}: expected guideline "
            f"'{expected_guideline}', got '{packet['guideline']}'"
        )


def test_escalation_monitoring():
    """Escalated packets should have the monitoring field set with a review timeline."""
    for patient_id in ["003", "005"]:
        packet = _run_escalation_pipeline(patient_id)
        if packet["decision"] != "escalate":
            pytest.skip(
                f"Patient {patient_id} did not escalate; skipping monitoring check"
            )
        assert packet["monitoring"] is not None, (
            f"Patient {patient_id}: escalated packet monitoring should not be None"
        )
        assert packet["monitoring"] != "", (
            f"Patient {patient_id}: escalated packet monitoring should not be empty"
        )
        # Monitoring should mention clinician review
        assert "clinician" in packet["monitoring"].lower() or "review" in packet["monitoring"].lower(), (
            f"Patient {patient_id}: escalated packet monitoring should mention "
            f"clinician review. Got: {packet['monitoring']}"
        )
