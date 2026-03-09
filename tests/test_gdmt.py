"""Tests for the GDMT (Guideline-Directed Medical Therapy) Engine.

Verifies that the engine returns correctly structured Action Packets and
follows AHA/ACC 2022 HF Guideline rules for diuretic, beta blocker,
ARNI/ACEi/ARB, MRA, and SGLT2i management across multiple patient profiles.
"""

from datetime import date

import pytest

from src.utils.data_loader import load_patient, load_drug_database
from src.utils.action_packet import validate_action_packet
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.gdmt_engine import evaluate_gdmt

# Tests use a fixed reference date matching the sample patient data
TEST_REFERENCE_DATE = date(2026, 2, 28)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def drug_db():
    return load_drug_database()


@pytest.fixture
def patient_001():
    return load_patient("001")


@pytest.fixture
def patient_002():
    return load_patient("002")


@pytest.fixture
def patient_003():
    return load_patient("003")


@pytest.fixture
def patient_005():
    return load_patient("005")


@pytest.fixture
def packets_001(patient_001, drug_db):
    trajectory = analyze_trajectory(patient_001)
    return evaluate_gdmt(patient_001, trajectory, drug_db, reference_date=TEST_REFERENCE_DATE)


@pytest.fixture
def packets_002(patient_002, drug_db):
    trajectory = analyze_trajectory(patient_002)
    return evaluate_gdmt(patient_002, trajectory, drug_db, reference_date=TEST_REFERENCE_DATE)


@pytest.fixture
def packets_003(patient_003, drug_db):
    trajectory = analyze_trajectory(patient_003)
    return evaluate_gdmt(patient_003, trajectory, drug_db, reference_date=TEST_REFERENCE_DATE)


@pytest.fixture
def packets_005(patient_005, drug_db):
    trajectory = analyze_trajectory(patient_005)
    return evaluate_gdmt(patient_005, trajectory, drug_db, reference_date=TEST_REFERENCE_DATE)


# ---------------------------------------------------------------------------
# Helpers: index 0=diuretic, 1=BB, 2=ARNI, 3=MRA, 4=SGLT2i
# ---------------------------------------------------------------------------

def _diuretic_packet(packets):
    return packets[0]


def _bb_packet(packets):
    return packets[1]


def _arni_packet(packets):
    return packets[2]


def _mra_packet(packets):
    return packets[3]


def _sglt2i_packet(packets):
    return packets[4]


# ===========================================================================
# Action Packet Format Tests
# ===========================================================================

class TestActionPacketFormat:
    """Every call to evaluate_gdmt must return well-formed Action Packets."""

    def test_returns_list(self, packets_001):
        """evaluate_gdmt always returns a list."""
        assert isinstance(packets_001, list)

    def test_all_packets_valid(self, packets_001, packets_002, packets_005):
        """Every returned packet passes validate_action_packet."""
        for packets in [packets_001, packets_002, packets_005]:
            for packet in packets:
                is_valid, errors = validate_action_packet(packet)
                assert is_valid, f"Invalid packet: {errors}"

    def test_all_packets_have_guideline(self, packets_001, packets_002, packets_005):
        """Every packet has a non-empty guideline citation."""
        for packets in [packets_001, packets_002, packets_005]:
            for packet in packets:
                assert packet.get("guideline"), (
                    f"Packet from {packet.get('tool_name')} missing guideline citation"
                )
                assert len(packet["guideline"]) > 0


# ===========================================================================
# Diuretic Tests
# ===========================================================================

class TestDiuretics:
    """Tests for diuretic management decisions."""

    def test_patient_001_diuretic_maintain(self, packets_001):
        """Patient 001 (stable weight, furosemide 40mg): diuretic decision
        should be 'maintain' because there is no significant weight gain."""
        diuretic = _diuretic_packet(packets_001)
        assert diuretic["decision"] == "maintain"

    def test_patient_002_diuretic_increase(self, packets_002):
        """Patient 002 (weight gain >2 lbs in 5 days, furosemide 40mg):
        diuretic decision should be 'increase', drug 'furosemide', new dose 80mg."""
        diuretic = _diuretic_packet(packets_002)
        assert diuretic["decision"] == "increase"
        assert diuretic["drug"] == "furosemide"
        assert diuretic["new_dose_mg"] == 80.0

    def test_patient_005_diuretic_metolazone(self, packets_005):
        """Patient 005 (already on furosemide 80mg BID, critical weight gain):
        should recommend metolazone addition since furosemide is already >= 80mg."""
        diuretic = _diuretic_packet(packets_005)
        assert diuretic["drug"] == "metolazone"
        assert diuretic["new_dose_mg"] == 2.5

    def test_diuretic_monitoring_on_change(self, packets_002, packets_005):
        """When diuretic decision is 'increase' or 'start', monitoring should
        contain 'BMP' (basic metabolic panel in 7 days per guideline)."""
        for packets in [packets_002, packets_005]:
            diuretic = _diuretic_packet(packets)
            assert diuretic["decision"] in ("increase", "start")
            assert diuretic["monitoring"] is not None
            assert "BMP" in diuretic["monitoring"]


# ===========================================================================
# Beta Blocker Tests
# ===========================================================================

class TestBetaBlockers:
    """Tests for beta blocker management decisions."""

    def test_patient_001_bb_uptitration(self, packets_001):
        """Patient 001 (metoprolol succinate 25mg, SBP >90, HR >60,
        >=14 days since last change): decision should be 'increase' with
        next dose of 50.0mg."""
        bb = _bb_packet(packets_001)
        assert bb["decision"] == "increase"
        assert bb["new_dose_mg"] == 50.0

    def test_patient_005_bb_maintain(self, packets_005):
        """Patient 005 (SBP dropping to 85, carvedilol 25mg at target):
        decision should be 'maintain' or 'hold' since the patient is at
        target dose and SBP is borderline."""
        bb = _bb_packet(packets_005)
        assert bb["decision"] in ("maintain", "hold")

    def test_bb_at_target_dose_maintain(self, packets_005):
        """Patient 005's carvedilol 25mg BID is at target dose (25mg).
        The decision should be 'maintain'."""
        bb = _bb_packet(packets_005)
        # Carvedilol target_dose_mg is 25.0 and patient is on 25.0
        assert bb["decision"] == "maintain"

    def test_bb_monitoring_on_change(self, packets_001):
        """When BB decision is 'increase' or 'start', monitoring should
        mention heart rate or blood pressure."""
        bb = _bb_packet(packets_001)
        assert bb["decision"] in ("increase", "start")
        assert bb["monitoring"] is not None
        monitoring_lower = bb["monitoring"].lower()
        assert "heart rate" in monitoring_lower or "blood pressure" in monitoring_lower


# ===========================================================================
# ARNI / ACEi / ARB Tests
# ===========================================================================

class TestARNI:
    """Tests for ARNI/ACEi/ARB management decisions."""

    def test_patient_001_start_arni(self, packets_001):
        """Patient 001 (EF 35%, on metoprolol+furosemide, no ACEi/ARB/ARNI,
        SBP ~115): should recommend starting ARNI."""
        arni = _arni_packet(packets_001)
        assert arni["decision"] == "start"
        assert arni["drug"] == "sacubitril/valsartan"
        assert arni["new_dose_mg"] == 24.0

    def test_patient_003_switch_to_arni(self, packets_003):
        """Patient 003 (on lisinopril, EF 30%, SBP 110): should recommend
        switch to ARNI with washout note."""
        arni = _arni_packet(packets_003)
        assert arni["decision"] == "start"
        assert arni["drug"] == "sacubitril/valsartan"
        assert "washout" in arni["reason"].lower() or "acei" in arni["reason"].lower()

    def test_patient_005_hold_arni(self, packets_005):
        """Patient 005 (SBP 85): should hold/not initiate ARNI."""
        arni = _arni_packet(packets_005)
        assert arni["decision"] in ("hold", "no_change")

    def test_arni_packet_has_guideline(self, packets_001):
        """ARNI packet should cite Section 7.3.1."""
        arni = _arni_packet(packets_001)
        assert "7.3.1" in arni["guideline"]

    def test_returns_five_packets(self, packets_001):
        """evaluate_gdmt should return 5 packets now."""
        assert len(packets_001) == 5


# ===========================================================================
# MRA Tests
# ===========================================================================

class TestMRA:
    """Tests for MRA management decisions."""

    def test_patient_001_start_mra(self, packets_001):
        """Patient 001 (EF 35%, NYHA 2, K+ 4.1, eGFR 65, no MRA):
        should recommend starting spironolactone."""
        mra = _mra_packet(packets_001)
        assert mra["decision"] == "start"
        assert mra["drug"] == "spironolactone"
        assert mra["new_dose_mg"] == 12.5

    def test_patient_003_hold_mra(self, packets_003):
        """Patient 003 (K+ 5.1, on spironolactone): should hold MRA."""
        mra = _mra_packet(packets_003)
        assert mra["decision"] == "hold"

    def test_patient_005_hold_mra(self, packets_005):
        """Patient 005 (K+ 5.3, eGFR 28): should hold MRA."""
        mra = _mra_packet(packets_005)
        assert mra["decision"] in ("hold", "stop")

    def test_mra_guideline(self, packets_001):
        """MRA packet should cite Section 7.3.4."""
        mra = _mra_packet(packets_001)
        assert "7.3.4" in mra["guideline"]


# ===========================================================================
# SGLT2i Tests
# ===========================================================================

class TestSGLT2i:
    """Tests for SGLT2i management decisions."""

    def test_patient_001_start_sglt2i(self, packets_001):
        """Patient 001 (EF 35%, eGFR 65, no SGLT2i): should recommend
        starting dapagliflozin 10mg."""
        sglt2 = _sglt2i_packet(packets_001)
        assert sglt2["decision"] == "start"
        assert sglt2["drug"] == "dapagliflozin"
        assert sglt2["new_dose_mg"] == 10.0

    def test_patient_005_start_sglt2i(self, packets_005):
        """Patient 005 (EF 20%, eGFR 28 >= 20): should recommend starting."""
        sglt2 = _sglt2i_packet(packets_005)
        assert sglt2["decision"] == "start"
        assert sglt2["drug"] == "dapagliflozin"

    def test_egfr_below_20_no_initiate(self, drug_db):
        """Edge case: eGFR 19 should NOT initiate SGLT2i."""
        patient = load_patient("005")
        # Override eGFR to 19
        patient["labs"]["egfr"] = [{"value": 19.0, "date": "2026-02-27"}]
        trajectory = analyze_trajectory(patient)
        packets = evaluate_gdmt(patient, trajectory, drug_db, reference_date=TEST_REFERENCE_DATE)
        sglt2 = _sglt2i_packet(packets)
        assert sglt2["decision"] == "no_change"

    def test_sglt2i_guideline(self, packets_001):
        """SGLT2i packet should cite Section 7.3.5."""
        sglt2 = _sglt2i_packet(packets_001)
        assert "7.3.5" in sglt2["guideline"]
