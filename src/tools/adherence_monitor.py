"""Adherence Monitor tool.

Checks medication refill adherence and identifies reported barriers.
Returns a single Action Packet.
"""

from src.utils.action_packet import create_action_packet


def check_adherence(patient: dict, signals: dict | None = None) -> dict:
    """Check medication adherence status for a heart failure patient.

    Uses refill timing, reported barriers, and extracted signals from the
    patient's message to determine adherence status.

    Args:
        patient: Patient data dictionary following the Patient Data Schema.
        signals: Optional extracted signals from the LLM extractor containing
            adherence_signals, side_effects, and barriers_mentioned.

    Returns:
        An Action Packet dictionary with the adherence assessment.
    """
    adherence = patient.get("adherence", {})
    signals = signals or {}

    days_since_refill = adherence.get("days_since_refill", 0)
    refill_on_time = adherence.get("refill_on_time", True)
    reported_barriers = list(adherence.get("reported_barriers", []))

    # Merge barriers from extracted signals into reported barriers
    signal_barriers = signals.get("barriers_mentioned", [])
    for barrier in signal_barriers:
        if barrier and barrier not in reported_barriers:
            reported_barriers.append(barrier)

    # Extract adherence signals from patient message
    adherence_signals = signals.get("adherence_signals", [])
    side_effects = signals.get("side_effects", [])

    # ── Check for non-adherence signals from patient message ─────────────
    # Signals like "I stopped taking", "skipping my pills", "ran out"
    # indicate non-adherence even if refill timing looks OK
    signal_non_adherent = False
    non_adherence_keywords = [
        "skipping", "stopped", "not taking", "ran out", "forgot",
        "missed", "can't afford", "don't take", "haven't been taking",
        "skip", "stop",
    ]
    for signal in adherence_signals:
        signal_lower = signal.lower()
        for keyword in non_adherence_keywords:
            if keyword in signal_lower:
                signal_non_adherent = True
                break

    # ── Determine adherence status ───────────────────────────────────────
    # A standard supply is 30 days. More than 7 days overdue (37+) is
    # clearly non adherent. Between 30 and 37, we rely on the refill flag.
    # Extracted signals from the patient's own words also trigger non-adherent.
    if days_since_refill > 37:
        decision = "non_adherent"
    elif days_since_refill > 30 and not refill_on_time:
        decision = "non_adherent"
    elif signal_non_adherent:
        decision = "non_adherent"
    else:
        decision = "adherent"

    # ── Build reason string ──────────────────────────────────────────────
    reason_parts = []
    if decision == "non_adherent":
        if days_since_refill > 30:
            overdue_days = days_since_refill - 30
            reason_parts.append(f"Medication refill is {overdue_days} days overdue")
        if signal_non_adherent and adherence_signals:
            reason_parts.append(
                f"Patient reports: {', '.join(adherence_signals)}"
            )
        if reported_barriers:
            barrier_text = ", ".join(reported_barriers)
            reason_parts.append(f"Barriers: {barrier_text}")
        if side_effects:
            reason_parts.append(
                f"Side effects reported: {', '.join(side_effects)}"
            )
        reason = ". ".join(reason_parts) if reason_parts else "Non adherent based on patient report"
    else:
        reason = "Medication refills are on schedule"
        if reported_barriers:
            barrier_text = ", ".join(reported_barriers)
            reason += f". Patient reports barriers: {barrier_text}"
        if side_effects:
            reason += f". Side effects reported: {', '.join(side_effects)}"

    # ── Monitoring and risk of inaction ──────────────────────────────────
    if decision == "non_adherent":
        monitoring = "Follow up on refill status in 7 days"
        risk_of_inaction = (
            "Medication non adherence increases risk of heart failure "
            "decompensation and hospitalization"
        )
    elif side_effects:
        monitoring = "Follow up on reported side effects in 7 days"
        risk_of_inaction = (
            "Unaddressed side effects may lead to medication non adherence"
        )
    else:
        monitoring = None
        risk_of_inaction = (
            "No immediate risk; patient is adherent to current regimen"
        )

    return create_action_packet(
        tool_name="adherence_monitor",
        decision=decision,
        reason=reason,
        guideline="AHA/ACC 2022 HF Guideline Section 7.3.8",
        confidence="high",
        risk_of_inaction=risk_of_inaction,
        inputs_used={
            "days_since_refill": days_since_refill,
            "refill_on_time": refill_on_time,
            "reported_barriers": reported_barriers,
            "adherence_signals": adherence_signals,
            "side_effects": side_effects,
        },
        drug=None,
        monitoring=monitoring,
        data_quality=None,
    )
