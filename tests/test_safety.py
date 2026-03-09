"""Tests for the Safety Checker tool.

Validates that check_safety correctly blocks unsafe medication changes,
approves safe ones, and follows AHA/ACC guideline citation requirements.
"""

from datetime import date

import pytest

from src.utils.data_loader import load_patient, load_drug_database
from src.utils.action_packet import validate_action_packet
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.gdmt_engine import evaluate_gdmt
from src.tools.safety_checker import check_safety

TEST_REFERENCE_DATE = date(2026, 2, 28)


# ---------------------------------------------------------------------------
# Helper: run trajectory + GDMT to get proposed changes, then run safety
# ---------------------------------------------------------------------------

def _run_safety_pipeline(patient_id: str) -> list[dict]:
    """Run trajectory -> GDMT -> safety for a given patient and return
    the list of safety Action Packets."""
    patient = load_patient(patient_id)
    drug_db = load_drug_database()
    trajectory_packet = analyze_trajectory(patient)
    proposed_changes = evaluate_gdmt(patient, trajectory_packet, drug_db, reference_date=TEST_REFERENCE_DATE)
    safety_results = check_safety(proposed_changes, patient, drug_db)
    return safety_results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_packets_valid_format():
    """All safety packets for every test patient must pass validate_action_packet."""
    for patient_id in ["001", "002", "003", "004", "005"]:
        safety_results = _run_safety_pipeline(patient_id)
        assert len(safety_results) > 0, (
            f"Patient {patient_id}: safety checker returned no packets"
        )
        for i, packet in enumerate(safety_results):
            is_valid, errors = validate_action_packet(packet)
            assert is_valid, (
                f"Patient {patient_id}, packet {i} failed validation: {errors}"
            )


def test_patient_001_all_safe():
    """Patient 001 (stable, normal labs) should have all safety results as 'safe'."""
    safety_results = _run_safety_pipeline("001")
    for packet in safety_results:
        assert packet["decision"] == "safe", (
            f"Expected 'safe' for stable patient 001, got '{packet['decision']}' "
            f"for drug '{packet.get('drug')}'. Reason: {packet.get('reason')}"
        )


def test_patient_003_spironolactone_blocked():
    """Patient 003 (K+ 5.1) should have spironolactone blocked.

    Patient 003 has potassium at 5.1 which is above the 5.0 threshold for
    MRA drugs. The safety checker should proactively block spironolactone
    even if GDMT does not propose a change to it.
    """
    safety_results = _run_safety_pipeline("003")
    spiro_packets = [
        p for p in safety_results
        if p.get("drug") and p["drug"].lower() == "spironolactone"
    ]
    assert len(spiro_packets) > 0, (
        "Expected at least one safety packet for spironolactone in patient 003"
    )
    blocked = any(p["decision"] == "blocked" for p in spiro_packets)
    assert blocked, (
        f"Spironolactone should be blocked for patient 003 (K+ 5.1), "
        f"got decisions: {[p['decision'] for p in spiro_packets]}"
    )


def test_patient_003_lisinopril_blocked():
    """Patient 003 (Cr rise ~50% from 1.2 to 1.8 within 27 days of last change)
    should have lisinopril blocked due to creatinine rise > 30%.

    Lisinopril last_changed_date is 2026-02-01, Cr was 1.2 on that date and
    rose to 1.8 by 2026-02-27, a 50% increase within 27 days.
    """
    safety_results = _run_safety_pipeline("003")
    lisinopril_packets = [
        p for p in safety_results
        if p.get("drug") and p["drug"].lower() == "lisinopril"
    ]
    assert len(lisinopril_packets) > 0, (
        "Expected at least one safety packet for lisinopril in patient 003"
    )
    blocked = any(p["decision"] == "blocked" for p in lisinopril_packets)
    assert blocked, (
        f"Lisinopril should be blocked for patient 003 (Cr rise > 30%), "
        f"got decisions: {[p['decision'] for p in lisinopril_packets]}"
    )


def test_patient_005_spironolactone_blocked():
    """Patient 005 (K+ 5.3, eGFR 28) should have spironolactone blocked.

    K+ > 5.0 blocks MRA, and eGFR < 30 also blocks spironolactone/eplerenone.
    """
    safety_results = _run_safety_pipeline("005")
    spiro_packets = [
        p for p in safety_results
        if p.get("drug") and p["drug"].lower() == "spironolactone"
    ]
    assert len(spiro_packets) > 0, (
        "Expected at least one safety packet for spironolactone in patient 005"
    )
    blocked = any(p["decision"] == "blocked" for p in spiro_packets)
    assert blocked, (
        f"Spironolactone should be blocked for patient 005 (K+ 5.3, eGFR 28), "
        f"got decisions: {[p['decision'] for p in spiro_packets]}"
    )


def test_safety_guideline_citation():
    """All safety packets should cite AHA/ACC 2022 HF Guideline Section 7.3.4."""
    expected_guideline = "AHA/ACC 2022 HF Guideline Section 7.3.4"
    for patient_id in ["001", "003", "005"]:
        safety_results = _run_safety_pipeline(patient_id)
        for i, packet in enumerate(safety_results):
            assert packet["guideline"] == expected_guideline, (
                f"Patient {patient_id}, packet {i}: expected guideline "
                f"'{expected_guideline}', got '{packet['guideline']}'"
            )


def test_blocked_packets_have_monitoring():
    """Every blocked packet must have the monitoring field set (not None, not empty)."""
    for patient_id in ["003", "005"]:
        safety_results = _run_safety_pipeline(patient_id)
        blocked_packets = [p for p in safety_results if p["decision"] == "blocked"]
        assert len(blocked_packets) > 0, (
            f"Patient {patient_id}: expected at least one blocked packet"
        )
        for i, packet in enumerate(blocked_packets):
            assert packet["monitoring"] is not None, (
                f"Patient {patient_id}, blocked packet {i} "
                f"(drug={packet.get('drug')}): monitoring should not be None"
            )
            assert packet["monitoring"] != "", (
                f"Patient {patient_id}, blocked packet {i} "
                f"(drug={packet.get('drug')}): monitoring should not be empty"
            )


def test_safe_packets_have_monitoring():
    """Safe packets for actionable changes (increase/start) should have monitoring set.

    When the safety checker approves an increase or start decision, there
    should be a monitoring recommendation (e.g. 'BMP in 7 days').
    """
    for patient_id in ["001", "002", "004"]:
        safety_results = _run_safety_pipeline(patient_id)
        actionable_safe_packets = [
            p for p in safety_results
            if p["decision"] == "safe"
            and p.get("inputs_used", {}).get("proposed_decision") in ("increase", "start")
        ]
        for packet in actionable_safe_packets:
            assert packet["monitoring"] is not None, (
                f"Patient {patient_id}: safe packet for "
                f"{packet.get('inputs_used', {}).get('proposed_decision')} "
                f"{packet.get('drug')} should have monitoring set"
            )
            assert packet["monitoring"] != "", (
                f"Patient {patient_id}: safe packet monitoring should not be empty "
                f"for drug {packet.get('drug')}"
            )
