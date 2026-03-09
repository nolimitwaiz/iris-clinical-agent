"""Tests for the Barrier Planner tool.

Validates that plan_barriers correctly identifies cost and social barriers,
suggests alternatives when appropriate, and follows AHA/ACC guideline
citation requirements.
"""

from datetime import date

import pytest

from src.utils.data_loader import load_patient, load_drug_database, load_alternatives
from src.utils.action_packet import validate_action_packet
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.gdmt_engine import evaluate_gdmt
from src.tools.safety_checker import check_safety
from src.tools.barrier_planner import plan_barriers

TEST_REFERENCE_DATE = date(2026, 2, 28)


# ---------------------------------------------------------------------------
# Helper: run the full pipeline up through barrier planning
# ---------------------------------------------------------------------------

def _run_barrier_pipeline(patient_id: str) -> list[dict]:
    """Run trajectory -> GDMT -> safety -> barrier planner for a given patient.

    Only passes safe (non-blocked) changes to the barrier planner, matching
    the production pipeline behavior.
    """
    patient = load_patient(patient_id)
    drug_db = load_drug_database()
    alternatives = load_alternatives()

    trajectory_packet = analyze_trajectory(patient)
    proposed_changes = evaluate_gdmt(patient, trajectory_packet, drug_db, reference_date=TEST_REFERENCE_DATE)
    safety_results = check_safety(proposed_changes, patient, drug_db)

    # Filter to only safe changes for barrier planning
    safe_changes = [p for p in safety_results if p["decision"] == "safe"]

    barrier_results = plan_barriers(safe_changes, patient, drug_db, alternatives)
    return barrier_results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_packets_valid_format():
    """All barrier packets for every test patient must pass validate_action_packet."""
    for patient_id in ["001", "002", "003", "004", "005"]:
        barrier_results = _run_barrier_pipeline(patient_id)
        # Some patients may have all changes blocked (no safe changes),
        # which means no barrier packets. That is acceptable.
        for i, packet in enumerate(barrier_results):
            is_valid, errors = validate_action_packet(packet)
            assert is_valid, (
                f"Patient {patient_id}, packet {i} failed validation: {errors}"
            )


def test_patient_001_no_barriers():
    """Patient 001 (tier1_generic, medium income, close pharmacy, moderate literacy)
    should have all barrier results as 'feasible'.

    This patient has affordable insurance, lives with family, and has no
    significant social barriers.
    """
    barrier_results = _run_barrier_pipeline("001")
    assert len(barrier_results) > 0, (
        "Patient 001 should have at least one barrier packet (safe changes exist)"
    )
    for packet in barrier_results:
        assert packet["decision"] == "feasible", (
            f"Expected 'feasible' for patient 001, got '{packet['decision']}' "
            f"for drug '{packet.get('drug')}'. Reason: {packet.get('reason')}"
        )


def test_patient_004_barrier_identified():
    """Patient 004 (tier3_nonpreferred, low income) should have barriers detected.

    Patient 004 has tier3_nonpreferred insurance and low income, which means
    the cost threshold is $50/month and many tier3 drugs will exceed it.
    Social factors (lives alone, low literacy, pharmacy 8 miles away) also
    contribute to barriers.
    """
    barrier_results = _run_barrier_pipeline("004")
    assert len(barrier_results) > 0, (
        "Patient 004 should have at least one barrier packet"
    )
    has_barrier = any(
        p["decision"] == "barrier_identified" for p in barrier_results
    )
    assert has_barrier, (
        f"Expected at least one 'barrier_identified' for patient 004, "
        f"got decisions: {[p['decision'] for p in barrier_results]}"
    )


def test_patient_004_social_barriers():
    """Patient 004 (lives alone, low literacy, pharmacy 8 miles away) should
    have social barriers mentioned in the inputs_used of barrier packets.

    The barrier planner should detect:
    - lives_alone -> recommend more frequent check ins
    - health_literacy == 'low' -> simplified instructions
    - pharmacy_distance > 5 -> mail order pharmacy suggestion
    """
    barrier_results = _run_barrier_pipeline("004")
    assert len(barrier_results) > 0, (
        "Patient 004 should have at least one barrier packet"
    )

    # Collect all social barrier notes across all packets
    all_social_barriers = []
    for packet in barrier_results:
        social = packet.get("inputs_used", {}).get("social_barriers", [])
        all_social_barriers.extend(social)

    # Check that at least the social barriers are detected
    social_text = " ".join(all_social_barriers).lower()
    assert "lives alone" in social_text, (
        f"Should mention 'lives alone' barrier. Got social barriers: {all_social_barriers}"
    )
    assert "literacy" in social_text, (
        f"Should mention low health literacy. Got social barriers: {all_social_barriers}"
    )
    assert "pharmacy" in social_text or "mail order" in social_text, (
        f"Should mention pharmacy distance barrier. Got social barriers: {all_social_barriers}"
    )


def test_barrier_guideline_citation():
    """All barrier packets should cite AHA/ACC 2022 HF Guideline Section 7.3.8."""
    expected_guideline = "AHA/ACC 2022 HF Guideline Section 7.3.8"
    for patient_id in ["001", "004"]:
        barrier_results = _run_barrier_pipeline(patient_id)
        for i, packet in enumerate(barrier_results):
            assert packet["guideline"] == expected_guideline, (
                f"Patient {patient_id}, packet {i}: expected guideline "
                f"'{expected_guideline}', got '{packet['guideline']}'"
            )


def test_barrier_monitoring():
    """All barrier packets should have the monitoring field set (not None, not empty).

    Both feasible and barrier_identified packets include monitoring
    recommendations: either standard follow up or barrier resolution follow up.
    """
    for patient_id in ["001", "004"]:
        barrier_results = _run_barrier_pipeline(patient_id)
        for i, packet in enumerate(barrier_results):
            assert packet["monitoring"] is not None, (
                f"Patient {patient_id}, packet {i} "
                f"(drug={packet.get('drug')}): monitoring should not be None"
            )
            assert packet["monitoring"] != "", (
                f"Patient {patient_id}, packet {i} "
                f"(drug={packet.get('drug')}): monitoring should not be empty"
            )
