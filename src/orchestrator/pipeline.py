"""Pipeline Orchestrator — runs the fixed clinical tool pipeline.

The pipeline runs in a fixed order every time, no skipping:
  1. Adherence Monitor
  2. Trajectory Analyzer
  3. GDMT Engine
  4. Safety Checker (for each proposed change)
  5. Barrier Planner (for each safe change)
  6. Escalation Manager
"""

from src.tools.adherence_monitor import check_adherence
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.gdmt_engine import evaluate_gdmt
from src.tools.safety_checker import check_safety
from src.tools.barrier_planner import plan_barriers
from src.tools.escalation_manager import evaluate_escalation
from src.utils.constants import BARRIER_KEYWORDS, ADHERENCE_KEYWORDS


# Priority levels for GDMT recommendations (lower = more urgent)
_DECISION_PRIORITY = {
    "stop": 1,       # Safety critical — must communicate
    "hold": 1,       # Safety critical — must communicate
    "escalate": 1,   # Escalation — must communicate
    "increase": 2,   # Active change — communicate this session
    "start": 3,      # New medication — stage across sessions
    "maintain": 4,   # Status quo — mention briefly or skip
    "no_change": 5,  # No action — skip in response
}

# Maximum number of active medication changes to surface in one response
MAX_CHANGES_PER_RESPONSE = 2


def _prioritize_packets(packets: list[dict]) -> list[dict]:
    """Add priority and staging info to GDMT packets.

    Annotates each GDMT packet with:
      - ``priority``: int (1=urgent, 5=no action)
      - ``communicate_now``: bool (whether to include in this response)

    Only the top MAX_CHANGES_PER_RESPONSE active changes (start/increase)
    are marked for communication. Hold/stop/escalate are always communicated.
    Maintain/no_change are never highlighted.

    Preserves the overall packet order (non-GDMT packets stay in place).
    """
    # Collect GDMT packets for prioritization
    gdmt_packets = [p for p in packets if p.get("tool_name") == "gdmt_engine"]

    for p in gdmt_packets:
        decision = p.get("decision", "no_change")
        p["priority"] = _DECISION_PRIORITY.get(decision, 5)

    # Sort by priority (lower = more urgent) to determine communication order
    gdmt_sorted = sorted(gdmt_packets, key=lambda p: p["priority"])

    # Mark what to communicate now
    active_change_count = 0
    for p in gdmt_sorted:
        priority = p["priority"]
        if priority <= 1:
            # Safety critical — always communicate
            p["communicate_now"] = True
        elif priority <= 3:
            # Active change (increase/start) — limit to MAX_CHANGES_PER_RESPONSE
            active_change_count += 1
            p["communicate_now"] = active_change_count <= MAX_CHANGES_PER_RESPONSE
        else:
            # Maintain/no_change — don't highlight
            p["communicate_now"] = False

    # Return original list (packets are mutated in place), order preserved
    return packets


def _extract_persistent_context(conversation_history: list[dict]) -> dict:
    """Mine conversation history for barriers and adherence issues that
    should persist across sessions.

    Scans patient turns in conversation history for keywords that indicate
    persistent barriers or adherence problems. These get merged into the
    current signals so tools don't ignore information from previous conversations.

    Returns a dict with barriers_mentioned and adherence_signals lists.
    """
    persistent_barriers: list[str] = []
    persistent_adherence: list[str] = []

    if not conversation_history:
        return {"barriers_mentioned": [], "adherence_signals": []}

    for turn in conversation_history:
        if turn.get("role") != "patient":
            continue
        content = (turn.get("content") or "").lower()

        for keyword, barrier_type in BARRIER_KEYWORDS.items():
            if keyword in content and barrier_type not in persistent_barriers:
                persistent_barriers.append(barrier_type)

        for keyword in ADHERENCE_KEYWORDS:
            if keyword in content:
                # Extract a brief context
                signal = f"previously reported: {keyword}"
                if signal not in persistent_adherence:
                    persistent_adherence.append(signal)

    return {
        "barriers_mentioned": persistent_barriers,
        "adherence_signals": persistent_adherence,
    }


def run_pipeline(
    patient: dict,
    signals: dict,
    drug_db: list[dict],
    alternatives: list[dict],
    reference_date=None,
) -> list[dict]:
    """Run the full clinical tool pipeline in fixed order.

    Args:
        patient: Patient data dictionary following the Patient Data Schema.
        signals: Extracted signals from the LLM extractor.
        drug_db: List of drug database entries.
        alternatives: List of alternative drug mapping entries.
        reference_date: Optional fixed date for day calculations (tests).

    Returns:
        A list of all Action Packets produced by the pipeline, in order.
    """
    # Merge persistent context from conversation history into current signals
    history = patient.get("conversation_history", [])
    if history:
        persistent = _extract_persistent_context(history)
        signals = dict(signals)  # don't mutate the original
        for key in ("barriers_mentioned", "adherence_signals"):
            existing = signals.get(key, [])
            for item in persistent.get(key, []):
                if item not in existing:
                    existing = list(existing) + [item]
            signals[key] = existing

    all_packets: list[dict] = []

    # 1. Adherence Monitor (now uses extracted signals for adherence/side effects)
    adherence_packet = check_adherence(patient, signals=signals)
    all_packets.append(adherence_packet)

    # 2. Trajectory Analyzer (uses extracted symptoms to boost risk assessment)
    trajectory_packet = analyze_trajectory(patient, signals=signals)
    all_packets.append(trajectory_packet)

    # 3. GDMT Engine
    gdmt_packets = evaluate_gdmt(patient, trajectory_packet, drug_db, reference_date=reference_date)
    all_packets.extend(gdmt_packets)

    # 4. Safety Checker (evaluates all GDMT proposals + proactive lab checks)
    safety_packets = check_safety(gdmt_packets, patient, drug_db)
    all_packets.extend(safety_packets)

    # 5. Barrier Planner (now uses extracted barriers from patient message)
    safe_changes = [p for p in safety_packets if p["decision"] == "safe"]
    barrier_packets = plan_barriers(safe_changes, patient, drug_db, alternatives, signals=signals)
    all_packets.extend(barrier_packets)

    # 6. Escalation Manager
    escalation_packet = evaluate_escalation(all_packets, patient)
    all_packets.append(escalation_packet)

    # 7. Prioritize GDMT recommendations for staged communication
    all_packets = _prioritize_packets(all_packets)

    return all_packets
