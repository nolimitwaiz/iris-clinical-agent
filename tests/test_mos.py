"""Tests for the Medication Optimization Score (MOS) calculator."""

import pytest

from src.utils.data_loader import load_patient, load_drug_database
from src.utils.mos import calculate_mos


@pytest.fixture
def drug_db():
    return load_drug_database()


class TestMOS:
    """MOS calculation tests across patient profiles."""

    def test_patient_001_low_mos(self, drug_db):
        """Patient 001 (metoprolol 25/200, no RAAS, no MRA, no SGLT2i):
        MOS should be low (~3)."""
        patient = load_patient("001")
        mos = calculate_mos(patient, drug_db)
        assert mos["mos_score"] < 10
        assert len(mos["pillars"]) == 4

        # BB pillar: 25/200 = 12.5% of 25 = ~3
        bb = mos["pillars"][0]
        assert bb["name"] == "Beta Blocker"
        assert bb["status"] == "below_target"
        assert bb["score"] == 3  # round(25/200 * 25) = 3

        # RAAS, MRA, SGLT2i all not_started
        for p in mos["pillars"][1:]:
            assert p["status"] == "not_started"
            assert p["score"] == 0

    def test_patient_003_moderate_mos(self, drug_db):
        """Patient 003 (lisinopril 20/20, spironolactone 25/25,
        carvedilol 12.5/25, no SGLT2i): MOS should be moderate."""
        patient = load_patient("003")
        mos = calculate_mos(patient, drug_db)

        # BB: carvedilol 12.5/25 = 50% of 25 = 12 or 13
        bb = mos["pillars"][0]
        assert bb["drug"] == "carvedilol"
        assert bb["score"] == 12  # round(12.5/25 * 25) = 12

        # RAAS: lisinopril 20/20 = 100% = 25
        raas = mos["pillars"][1]
        assert raas["drug"] == "lisinopril"
        assert raas["score"] == 25
        assert raas["status"] == "at_target"

        # MRA: spironolactone 25/25 = 100% = 25
        mra = mos["pillars"][2]
        assert mra["drug"] == "spironolactone"
        assert mra["score"] == 25
        assert mra["status"] == "at_target"

        # SGLT2i: not started = 0
        sglt2 = mos["pillars"][3]
        assert sglt2["score"] == 0

        # Total: 12 + 25 + 25 + 0 = 62
        assert mos["mos_score"] == 62

    def test_all_at_target(self, drug_db):
        """A patient with all 4 pillars at target should have MOS = 100."""
        patient = load_patient("001")
        # Override meds to all at target
        patient["medications"] = [
            {"drug": "metoprolol succinate", "dose_mg": 200.0, "frequency_per_day": 1,
             "route": "oral", "start_date": "2025-01-01", "last_changed_date": "2025-01-01"},
            {"drug": "sacubitril/valsartan", "dose_mg": 97.0, "frequency_per_day": 2,
             "route": "oral", "start_date": "2025-01-01", "last_changed_date": "2025-01-01"},
            {"drug": "spironolactone", "dose_mg": 25.0, "frequency_per_day": 1,
             "route": "oral", "start_date": "2025-01-01", "last_changed_date": "2025-01-01"},
            {"drug": "dapagliflozin", "dose_mg": 10.0, "frequency_per_day": 1,
             "route": "oral", "start_date": "2025-01-01", "last_changed_date": "2025-01-01"},
        ]
        mos = calculate_mos(patient, drug_db)
        assert mos["mos_score"] == 100
        for p in mos["pillars"]:
            assert p["score"] == 25
            assert p["status"] == "at_target"

    def test_structure(self, drug_db):
        """MOS response should have correct structure."""
        patient = load_patient("001")
        mos = calculate_mos(patient, drug_db)
        assert "mos_score" in mos
        assert "pillars" in mos
        assert isinstance(mos["mos_score"], int)
        assert 0 <= mos["mos_score"] <= 100
        assert len(mos["pillars"]) == 4
        for p in mos["pillars"]:
            assert "name" in p
            assert "score" in p
            assert "max_score" in p
            assert "status" in p
            assert p["max_score"] == 25
