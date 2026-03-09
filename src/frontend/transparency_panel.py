"""Transparency Panel component for the Streamlit frontend.

Displays all Action Packets from the pipeline with color coding
and expandable details, showing the clinical reasoning trail.
"""

import streamlit as st


def _decision_color(decision: str) -> str:
    """Return a color indicator for the decision type."""
    green = ["safe", "feasible", "adherent", "no_escalation", "low", "maintain", "no_change"]
    yellow = ["moderate", "barrier_identified", "non_adherent", "hold"]
    red = ["blocked", "escalate", "critical", "high", "stop"]
    blue = ["increase", "start"]

    if decision in green:
        return "🟢"
    elif decision in yellow:
        return "🟡"
    elif decision in red:
        return "🔴"
    elif decision in blue:
        return "🔵"
    return "⚪"


def _format_tool_name(tool_name: str) -> str:
    """Format tool name for display."""
    return tool_name.replace("_", " ").title()


def render_transparency_panel(packets: list[dict] | None = None):
    """Render the transparency panel in the right column.

    Shows all Action Packets from the latest pipeline run with
    color-coded decisions and expandable details.

    Args:
        packets: List of Action Packets from the pipeline run.
    """
    st.markdown("### Clinical Reasoning")

    if not packets:
        st.info("Send a message to see the clinical reasoning trail")
        return

    for packet in packets:
        tool_name = packet.get("tool_name", "unknown")
        decision = packet.get("decision", "unknown")
        drug = packet.get("drug")
        color = _decision_color(decision)

        # Build the expander label
        label_parts = [f"{color} {_format_tool_name(tool_name)}: {decision.upper()}"]
        if drug:
            label_parts.append(f"({drug})")
        label = " ".join(label_parts)

        with st.expander(label, expanded=False):
            # Decision and drug info
            if drug:
                st.markdown(f"**Drug:** {drug}")
                current = packet.get("current_dose_mg")
                new = packet.get("new_dose_mg")
                if current is not None:
                    dose_text = f"**Current Dose:** {current}mg"
                    if new is not None:
                        dose_text += f" → **New Dose:** {new}mg"
                    st.markdown(dose_text)

            # Reason
            reason = packet.get("reason", "")
            if reason:
                st.markdown(f"**Reason:** {reason}")

            # Guideline
            guideline = packet.get("guideline", "")
            if guideline:
                st.markdown(f"**Guideline:** {guideline}")

            # Monitoring
            monitoring = packet.get("monitoring")
            if monitoring:
                st.markdown(f"**Monitoring:** {monitoring}")

            # Confidence
            confidence = packet.get("confidence", "")
            if confidence:
                conf_colors = {"high": "🟢", "moderate": "🟡", "low": "🔴"}
                conf_icon = conf_colors.get(confidence, "⚪")
                st.markdown(f"**Confidence:** {conf_icon} {confidence}")

            # Risk of inaction
            risk = packet.get("risk_of_inaction", "")
            if risk:
                st.markdown(f"**Risk of Inaction:** {risk}")

            # Data quality
            dq = packet.get("data_quality")
            if dq:
                st.warning(f"Data Quality: {dq}")

    # Special section for escalation
    escalation = [p for p in packets if p.get("decision") == "escalate"]
    if escalation:
        st.divider()
        st.error("**ESCALATION TRIGGERED**")
        for esc in escalation:
            summary = esc.get("inputs_used", {}).get("clinician_summary", "")
            if summary:
                st.code(summary, language=None)
            monitoring = esc.get("monitoring", "")
            if monitoring:
                st.markdown(f"**Required:** {monitoring}")
