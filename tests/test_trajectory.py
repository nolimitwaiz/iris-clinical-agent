"""Tests for trajectory_analyzer and adherence_monitor tools."""

import pytest

from src.utils.data_loader import load_patient, load_drug_database
from src.utils.action_packet import validate_action_packet
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.adherence_monitor import check_adherence


# ── Trajectory Analyzer Tests ─────────────────────────────────────────────────


def test_action_packet_format():
    """Run trajectory analyzer for patient 001 and verify the Action Packet is valid."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    is_valid, errors = validate_action_packet(packet)
    assert is_valid, f"Action Packet validation failed: {errors}"


def test_all_fields_present():
    """Check that tool_name, timestamp, decision, reason, guideline, confidence,
    and risk_of_inaction are all present and non empty."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)

    required_fields = [
        "tool_name",
        "timestamp",
        "decision",
        "reason",
        "guideline",
        "confidence",
        "risk_of_inaction",
    ]
    for field in required_fields:
        assert field in packet, f"Missing field: {field}"
        assert packet[field] is not None, f"Field is None: {field}"
        assert packet[field] != "", f"Field is empty string: {field}"


def test_patient_001_stable():
    """Patient 001 (Maria, stable weight) should have a 'low' trajectory decision."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    assert packet["decision"] == "low", (
        f"Expected 'low' for stable patient, got '{packet['decision']}'"
    )


def test_patient_002_weight_gain():
    """Patient 002 (James, weight gain) should have a 'high' trajectory decision."""
    patient = load_patient("002")
    packet = analyze_trajectory(patient)
    assert packet["decision"] == "high", (
        f"Expected 'high' for weight gain patient, got '{packet['decision']}'"
    )


def test_patient_005_critical():
    """Patient 005 (David, rapid deterioration) should have a 'critical' trajectory decision."""
    patient = load_patient("005")
    packet = analyze_trajectory(patient)
    assert packet["decision"] == "critical", (
        f"Expected 'critical' for rapidly deteriorating patient, got '{packet['decision']}'"
    )


def test_guideline_citation():
    """Every trajectory packet must cite AHA/ACC 2022 HF Guideline Section 7.3.1."""
    expected_guideline = "AHA/ACC 2022 HF Guideline Section 7.3.1"
    for patient_id in ["001", "002", "005"]:
        patient = load_patient(patient_id)
        packet = analyze_trajectory(patient)
        assert packet["guideline"] == expected_guideline, (
            f"Patient {patient_id}: expected guideline '{expected_guideline}', "
            f"got '{packet['guideline']}'"
        )


def test_monitoring_when_not_low():
    """When decision is not 'low', monitoring field should not be None."""
    for patient_id in ["002", "005"]:
        patient = load_patient(patient_id)
        packet = analyze_trajectory(patient)
        assert packet["decision"] != "low", (
            f"Patient {patient_id} was expected to have non low decision"
        )
        assert packet["monitoring"] is not None, (
            f"Patient {patient_id}: monitoring should not be None "
            f"when decision is '{packet['decision']}'"
        )


def test_inputs_used_contains_weight_deltas():
    """inputs_used should contain weight_delta_3d_lbs and weight_delta_5d_lbs keys."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    inputs = packet["inputs_used"]
    assert "weight_delta_3d_lbs" in inputs, "Missing weight_delta_3d_lbs in inputs_used"
    assert "weight_delta_5d_lbs" in inputs, "Missing weight_delta_5d_lbs in inputs_used"


def test_confidence_based_on_readings():
    """Patient 001 with 30 days of vitals should have 'high' confidence."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    assert packet["confidence"] == "high", (
        f"Expected 'high' confidence for patient with 30 days of vitals, "
        f"got '{packet['confidence']}'"
    )


# ── Adherence Monitor Tests ──────────────────────────────────────────────────


def test_adherence_action_packet_format():
    """Verify that check_adherence returns a valid Action Packet."""
    patient = load_patient("001")
    packet = check_adherence(patient)
    is_valid, errors = validate_action_packet(packet)
    assert is_valid, f"Action Packet validation failed: {errors}"


def test_patient_001_adherent():
    """Patient 001 (8 days since refill, on time) should be 'adherent'."""
    patient = load_patient("001")
    packet = check_adherence(patient)
    assert packet["decision"] == "adherent", (
        f"Expected 'adherent' for on time patient, got '{packet['decision']}'"
    )


def test_patient_004_non_adherent():
    """Patient 004 (35 days since refill, not on time) should be 'non_adherent'."""
    patient = load_patient("004")
    packet = check_adherence(patient)
    assert packet["decision"] == "non_adherent", (
        f"Expected 'non_adherent' for overdue patient, got '{packet['decision']}'"
    )


def test_adherence_guideline_citation():
    """Adherence packets should cite AHA/ACC 2022 HF Guideline Section 7.3.8."""
    expected_guideline = "AHA/ACC 2022 HF Guideline Section 7.3.8"
    for patient_id in ["001", "004"]:
        patient = load_patient(patient_id)
        packet = check_adherence(patient)
        assert packet["guideline"] == expected_guideline, (
            f"Patient {patient_id}: expected guideline '{expected_guideline}', "
            f"got '{packet['guideline']}'"
        )


def test_non_adherent_has_monitoring():
    """Non adherent patients should have the monitoring field set."""
    patient = load_patient("004")
    packet = check_adherence(patient)
    assert packet["decision"] == "non_adherent"
    assert packet["monitoring"] is not None, (
        "Non adherent patient should have monitoring set"
    )
    assert packet["monitoring"] != "", (
        "Non adherent patient monitoring should not be empty"
    )


def test_barriers_in_reason():
    """Patient 004 has reported barriers; the reason field should mention them."""
    patient = load_patient("004")
    packet = check_adherence(patient)
    reason = packet["reason"].lower()
    # Patient 004 barriers: "medication too expensive", "pharmacy too far"
    assert "expensive" in reason or "medication too expensive" in reason, (
        f"Reason should mention cost barrier, got: {packet['reason']}"
    )
    assert "pharmacy" in reason or "pharmacy too far" in reason, (
        f"Reason should mention pharmacy distance barrier, got: {packet['reason']}"
    )


# ── Composite Risk Score Tests ───────────────────────────────────────────────


def test_risk_score_present():
    """Trajectory packet should include a risk_score dict."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    assert "risk_score" in packet
    rs = packet["risk_score"]
    assert "composite" in rs
    assert "tier" in rs
    assert "components" in rs


def test_patient_001_risk_low():
    """Patient 001 (stable) should have low risk score."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    rs = packet["risk_score"]
    assert rs["composite"] <= 25
    assert rs["tier"] == "low"


def test_patient_002_risk_moderate_or_high():
    """Patient 002 (weight gain) should have moderate or high risk."""
    patient = load_patient("002")
    packet = analyze_trajectory(patient)
    rs = packet["risk_score"]
    assert rs["composite"] >= 15
    assert rs["tier"] in ("moderate", "high")


def test_patient_005_risk_critical():
    """Patient 005 (critical weight + low SBP + BNP 1800) should be critical or high."""
    patient = load_patient("005")
    packet = analyze_trajectory(patient)
    rs = packet["risk_score"]
    assert rs["composite"] > 50
    assert rs["tier"] in ("high", "critical")


def test_risk_components_sum():
    """Component contributions should sum to the composite score."""
    patient = load_patient("005")
    packet = analyze_trajectory(patient)
    rs = packet["risk_score"]
    total = sum(c["contribution"] for c in rs["components"].values())
    assert abs(total - rs["composite"]) <= 1  # rounding tolerance


def test_risk_components_present():
    """All 5 risk components should be present."""
    patient = load_patient("001")
    packet = analyze_trajectory(patient)
    rs = packet["risk_score"]
    expected = {"weight_trend", "blood_pressure", "heart_rate", "adherence", "bnp"}
    assert set(rs["components"].keys()) == expected
