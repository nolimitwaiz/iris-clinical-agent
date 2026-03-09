"""Tests for the response validator."""

import pytest

from src.orchestrator.validator import (
    validate_response,
    _extract_drug_names_from_text,
    _extract_doses_from_text,
    _build_allowed_set,
)
from src.utils.action_packet import create_action_packet


def _make_test_packets():
    """Create sample Action Packets for testing."""
    return [
        create_action_packet(
            tool_name="gdmt_engine",
            decision="increase",
            drug="furosemide",
            current_dose_mg=40.0,
            new_dose_mg=80.0,
            reason="Weight gain detected",
            guideline="AHA/ACC 2022 HF Guideline Section 7.3.2",
            confidence="high",
            risk_of_inaction="Fluid retention may worsen",
            monitoring="BMP in 7 days",
        ),
        create_action_packet(
            tool_name="gdmt_engine",
            decision="maintain",
            drug="metoprolol succinate",
            current_dose_mg=25.0,
            new_dose_mg=None,
            reason="At stable dose",
            guideline="AHA/ACC 2022 HF Guideline Section 7.3.3",
            confidence="high",
            risk_of_inaction="No risk",
        ),
    ]


class TestDrugNameExtraction:
    def test_finds_generic_names(self):
        text = "You are taking furosemide for fluid management."
        found = _extract_drug_names_from_text(text)
        assert "furosemide" in found

    def test_finds_brand_names(self):
        text = "Your Lasix dose will be adjusted."
        found = _extract_drug_names_from_text(text)
        assert "lasix" in found

    def test_case_insensitive(self):
        text = "FUROSEMIDE is working well."
        found = _extract_drug_names_from_text(text)
        assert "furosemide" in found

    def test_no_false_positives(self):
        text = "You are doing great today."
        found = _extract_drug_names_from_text(text)
        assert len(found) == 0


class TestDoseExtraction:
    def test_finds_dose_no_space(self):
        doses = _extract_doses_from_text("Take 40mg daily")
        assert any(d["value"] == 40.0 for d in doses)

    def test_finds_dose_with_space(self):
        doses = _extract_doses_from_text("Take 40 mg daily")
        assert any(d["value"] == 40.0 for d in doses)

    def test_finds_decimal_dose(self):
        doses = _extract_doses_from_text("Start at 3.125mg")
        assert any(d["value"] == 3.125 for d in doses)


class TestValidateResponse:
    def test_approved_when_all_drugs_in_packets(self):
        packets = _make_test_packets()
        draft = "We are adjusting your furosemide from 40 mg to 80 mg."
        result = validate_response(draft, packets)
        assert result["approved"] is True
        assert len(result["violations"]) == 0

    def test_rejected_when_unknown_drug_mentioned(self):
        packets = _make_test_packets()
        draft = "We will start you on lisinopril 10mg for blood pressure."
        result = validate_response(draft, packets)
        assert result["approved"] is False
        assert any("lisinopril" in v for v in result["violations"])

    def test_rejected_when_unknown_dose_mentioned(self):
        packets = _make_test_packets()
        draft = "Your furosemide will be increased to 120mg."
        result = validate_response(draft, packets)
        assert result["approved"] is False
        assert any("120" in v for v in result["violations"])

    def test_rejected_for_hyphens(self):
        packets = _make_test_packets()
        draft = "Please follow-up with your doctor about your long-term care."
        result = validate_response(draft, packets)
        assert result["approved"] is False
        assert any("Hyphen" in v or "hyphen" in v.lower() for v in result["violations"])

    def test_approved_clean_response(self):
        packets = _make_test_packets()
        draft = (
            "Your furosemide dose is being increased from 40 mg to 80 mg to help "
            "manage fluid. Please get a blood test in 7 days."
        )
        result = validate_response(draft, packets)
        assert result["approved"] is True

    def test_returns_dict_with_required_keys(self):
        packets = _make_test_packets()
        result = validate_response("Hello", packets)
        assert "approved" in result
        assert "response" in result
        assert "violations" in result


class TestBuildAllowedSet:
    def test_extracts_drug_names(self):
        packets = _make_test_packets()
        allowed = _build_allowed_set(packets)
        assert "furosemide" in allowed["drug_names"]
        assert "metoprolol succinate" in allowed["drug_names"]

    def test_extracts_doses(self):
        packets = _make_test_packets()
        allowed = _build_allowed_set(packets)
        assert 40.0 in allowed["doses"]
        assert 80.0 in allowed["doses"]
        assert 25.0 in allowed["doses"]
