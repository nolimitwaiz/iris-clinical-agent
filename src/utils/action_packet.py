"""Action Packet creation and validation utilities."""

from datetime import datetime, timezone

REQUIRED_FIELDS = [
    "tool_name",
    "decision",
    "reason",
    "guideline",
    "confidence",
    "risk_of_inaction",
]

ALL_FIELDS = [
    "tool_name",
    "timestamp",
    "inputs_used",
    "decision",
    "drug",
    "current_dose_mg",
    "new_dose_mg",
    "reason",
    "guideline",
    "monitoring",
    "confidence",
    "risk_of_inaction",
    "data_quality",
]


def create_action_packet(
    tool_name: str,
    decision: str,
    reason: str,
    guideline: str,
    confidence: str,
    risk_of_inaction: str,
    inputs_used: dict | None = None,
    drug: str | None = None,
    current_dose_mg: float | None = None,
    new_dose_mg: float | None = None,
    monitoring: str | None = None,
    data_quality: str | None = None,
) -> dict:
    """Create a validated Action Packet with all required fields.

    Every clinical tool must return an Action Packet. This helper ensures
    consistent structure and adds an ISO timestamp automatically.
    """
    packet = {
        "tool_name": tool_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs_used": inputs_used or {},
        "decision": decision,
        "drug": drug,
        "current_dose_mg": current_dose_mg,
        "new_dose_mg": new_dose_mg,
        "reason": reason,
        "guideline": guideline,
        "monitoring": monitoring,
        "confidence": confidence,
        "risk_of_inaction": risk_of_inaction,
        "data_quality": data_quality,
    }
    return packet


def validate_action_packet(packet: dict) -> tuple[bool, list[str]]:
    """Validate that a dict has all required Action Packet fields.

    Returns (is_valid, list_of_errors).
    """
    errors = []

    if not isinstance(packet, dict):
        return False, ["Action Packet must be a dictionary"]

    for field in REQUIRED_FIELDS:
        if field not in packet:
            errors.append(f"Missing required field: {field}")
        elif packet[field] is None or packet[field] == "":
            errors.append(f"Required field is empty: {field}")

    if "timestamp" not in packet:
        errors.append("Missing timestamp")

    if "decision" in packet:
        valid_decisions = [
            "increase", "maintain", "hold", "start", "stop",
            "escalate", "no_change", "safe", "blocked",
            "adherent", "non_adherent", "no_escalation",
            "low", "moderate", "high", "critical",
            "feasible", "barrier_identified",
        ]
        if packet["decision"] not in valid_decisions:
            errors.append(f"Invalid decision value: {packet['decision']}")

    if "confidence" in packet and packet["confidence"]:
        valid_confidence = ["high", "moderate", "low"]
        if packet["confidence"] not in valid_confidence:
            errors.append(f"Invalid confidence value: {packet['confidence']}")

    return len(errors) == 0, errors
