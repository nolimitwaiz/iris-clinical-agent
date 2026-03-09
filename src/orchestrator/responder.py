"""LLM Responder — uses Gemini 2.0 Flash to generate patient-facing messages."""

import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

_client = None


def _has_api_key() -> bool:
    """Check if a Gemini API key is available."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(key)


def _get_client():
    """Get or create the Gemini client (new google-genai SDK)."""
    global _client
    if _client is None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        _client = genai.Client(api_key=api_key)
    return _client


def _build_fallback_response(packets: list[dict], patient: dict) -> str:
    """Build a deterministic summary from Action Packets when no API key is set."""
    patient_name = patient.get("name", "there").split()[0]
    lines = [f"Hi {patient_name}, here is your care summary:\n"]

    for p in packets:
        decision = p.get("decision", "no_change")
        if decision == "no_change":
            continue
        tool = (p.get("tool_name") or "").replace("_", " ").title()
        drug = p.get("drug") or ""
        reason = p.get("reason", "")
        monitoring = p.get("monitoring")

        if drug:
            lines.append(f"**{tool}** {decision} {drug}: {reason}")
        else:
            lines.append(f"**{tool}** {decision}: {reason}")
        if monitoring:
            lines.append(f"  Monitoring: {monitoring}")
        lines.append("")

    if len(lines) == 1:
        lines.append("Everything looks stable right now. Keep up the great work!\n")

    lines.append(
        "Please reach out to your care team if you have any questions or concerns."
    )
    # Remove hyphens per style requirement
    return "\n".join(lines).replace("-", " ")

EDUCATION_CONTENT = {
    "potassium": {
        "full_name": "Potassium",
        "what_it_measures": "The level of potassium in your blood, a mineral that helps your heart beat regularly.",
        "normal_range": "3.5 to 5.0 mEq/L",
        "why_it_matters": "Too low can cause irregular heartbeats. Too high can be dangerous for your heart. Many heart failure medicines affect potassium levels.",
        "simple_analogy": "Think of potassium like the oil in your car engine. Too little or too much can cause the engine to misfire.",
    },
    "creatinine": {
        "full_name": "Creatinine",
        "what_it_measures": "A waste product filtered by your kidneys. Higher levels may mean your kidneys are working harder.",
        "normal_range": "0.7 to 1.3 mg/dL",
        "why_it_matters": "Heart failure medicines can affect kidney function. Your care team watches this closely when adjusting medications.",
        "simple_analogy": "Creatinine is like the exhaust from a car. If the exhaust builds up, it might mean the engine (your kidneys) needs a checkup.",
    },
    "egfr": {
        "full_name": "Estimated Glomerular Filtration Rate",
        "what_it_measures": "How well your kidneys are filtering waste from your blood. Higher numbers are better.",
        "normal_range": "Above 60 is generally normal. Below 30 may need special attention.",
        "why_it_matters": "Your kidneys and heart work together. When kidney function drops, your care team may need to adjust heart medicines.",
        "simple_analogy": "Think of eGFR like a speedometer for your kidneys. The higher the number, the faster and better they're working.",
    },
    "bnp": {
        "full_name": "B type Natriuretic Peptide",
        "what_it_measures": "A hormone released by your heart when it is under stress or working too hard.",
        "normal_range": "Below 100 pg/mL is generally normal. Heart failure patients often have higher levels.",
        "why_it_matters": "Rising BNP can be an early warning that your heart failure may be getting worse, even before you feel symptoms.",
        "simple_analogy": "BNP is like a stress alarm from your heart. The higher it goes, the harder your heart is working.",
    },
    "sodium": {
        "full_name": "Sodium",
        "what_it_measures": "The level of sodium (salt) in your blood, which helps control fluid balance.",
        "normal_range": "135 to 145 mEq/L",
        "why_it_matters": "Low sodium can happen with heart failure and some diuretics (water pills). It can cause confusion and fatigue.",
        "simple_analogy": "Sodium helps keep the right amount of water in your body, like a sponge that holds just the right amount of moisture.",
    },
    "ejection_fraction": {
        "full_name": "Ejection Fraction",
        "what_it_measures": "The percentage of blood your heart pumps out with each beat. A healthy heart pumps about 55 to 70%.",
        "normal_range": "55% to 70% is normal. Below 40% is considered reduced.",
        "why_it_matters": "A lower EF means your heart is not pumping as strongly. The goal of treatment is to help improve or maintain your EF.",
        "simple_analogy": "Imagine squeezing a water balloon. EF is how much water comes out with each squeeze. A healthy heart squeezes out more than half.",
    },
    "nyha_class": {
        "full_name": "New York Heart Association Functional Class",
        "what_it_measures": "How much your heart failure symptoms limit your daily activities, rated from I (least) to IV (most).",
        "normal_range": "Class I: No limits. Class II: Mild limits. Class III: Notable limits. Class IV: Symptoms at rest.",
        "why_it_matters": "This helps your care team understand how heart failure affects your daily life and guides treatment decisions.",
    },
}

# Keyword to education topic mapping
_KEYWORD_MAP = {
    "potassium": "potassium", "k+": "potassium", "k level": "potassium",
    "creatinine": "creatinine", "cr level": "creatinine",
    "egfr": "egfr", "gfr": "egfr", "kidney": "egfr", "kidneys": "egfr", "renal": "egfr", "filtration": "egfr",
    "bnp": "bnp", "natriuretic": "bnp", "heart stress": "bnp",
    "sodium": "sodium", "na+": "sodium", "salt": "sodium", "na level": "sodium",
    "ejection fraction": "ejection_fraction", "ef": "ejection_fraction", "pumping": "ejection_fraction",
    "nyha": "nyha_class", "functional class": "nyha_class", "class i": "nyha_class",
    "class ii": "nyha_class", "class iii": "nyha_class", "class iv": "nyha_class",
}


def _find_education_topics(message: str, questions: list[str] | None = None) -> list[dict]:
    """Scan message and extracted questions for education keywords. Return matching education dicts."""
    text = (message or "").lower()
    if questions:
        text += " " + " ".join(q.lower() for q in questions)

    matched_keys: set[str] = set()
    for keyword, topic_key in _KEYWORD_MAP.items():
        if keyword in text:
            matched_keys.add(topic_key)

    return [{"topic": k, **EDUCATION_CONTENT[k]} for k in matched_keys if k in EDUCATION_CONTENT]


def _build_conversation_context(conversation_history: list[dict], max_turns: int = 4) -> str:
    """Build a conversation context string from recent history for the responder."""
    if not conversation_history:
        return ""
    recent = conversation_history[-max_turns:]
    lines = ["Recent conversation:"]
    for turn in recent:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        lines.append(f"  {role}: {content}")
    return "\n".join(lines)


def _build_education_context(topics: list[dict]) -> str:
    """Format matched education topics for the prompt."""
    if not topics:
        return ""
    lines = ["Approved Education Content (use ONLY this information to explain metrics, do not invent facts beyond what is provided):"]
    for t in topics:
        lines.append(f"  {t['full_name']}:")
        lines.append(f"    What it measures: {t['what_it_measures']}")
        lines.append(f"    Normal range: {t['normal_range']}")
        lines.append(f"    Why it matters: {t['why_it_matters']}")
        if t.get("simple_analogy"):
            lines.append(f"    Simple analogy: {t['simple_analogy']}")
    return "\n".join(lines)


_NO_ACTION_DECISIONS = {
    "no_change", "maintain", "adherent", "no_escalation",
    "safe", "feasible", "low",
}


def _filter_actionable_packets(packets: list[dict]) -> list[dict]:
    """Filter packets to only actionable ones for the response prompt.

    Strips no-op decisions (no_change, maintain, safe, etc.) to reduce
    token count sent to Gemini.  Also removes tool_name and risk_of_inaction
    which aren't needed for response generation.

    GDMT packets with ``communicate_now=False`` are marked as deferred
    so the responder knows to mention them briefly or skip them.

    If all packets are no-op, returns a single stable summary packet.
    """
    actionable = []
    deferred = []
    for p in packets:
        if p.get("decision") in _NO_ACTION_DECISIONS:
            continue
        # Strip fields not needed for response generation
        filtered = {
            "decision": p.get("decision"),
            "drug": p.get("drug"),
            "current_dose_mg": p.get("current_dose_mg"),
            "new_dose_mg": p.get("new_dose_mg"),
            "reason": p.get("reason"),
            "monitoring": p.get("monitoring"),
        }
        # Respect priority-based staging from pipeline
        if p.get("communicate_now") is False and p.get("tool_name") == "gdmt_engine":
            filtered["deferred"] = True
            deferred.append(filtered)
        else:
            actionable.append(filtered)
    if not actionable and not deferred:
        return [{"decision": "stable", "reason": "All indicators stable, no changes recommended"}]
    # Include deferred items so responder can briefly acknowledge them
    if deferred:
        actionable.append({
            "decision": "deferred",
            "reason": f"{len(deferred)} additional medication change(s) to discuss at your next check in",
            "deferred_drugs": [d.get("drug") for d in deferred if d.get("drug")],
        })
    return actionable


ONBOARDING_PREFIX = """This is a brand new patient speaking with Iris for the first time.
Warmly introduce yourself as Iris, their heart failure care companion,
and ask for their first name so you can address them personally.
Keep it brief and natural. Then address their message if they said anything clinical.
"""

RESPONSE_PROMPT = """{iris_persona}

{conversation_context}
{education_context}
Action Packets: {packets_json}
Message: {message}
Name: {patient_name}
Literacy: {literacy}"""


def generate_response(
    packets: list[dict],
    message: str,
    patient: dict,
    conversation_history: list[dict] | None = None,
    signals: dict | None = None,
) -> str:
    """Generate a patient-facing response using Gemini based on Action Packets.

    Args:
        packets: List of Action Packet dicts from the pipeline.
        message: The patient's original message.
        patient: Patient data dict (used for name, health_literacy).
        conversation_history: Optional prior conversation turns for context.
        signals: Optional extracted signals (used for education topic matching).

    Returns:
        A string response for the patient.
    """
    # Demo mode: no API key — build a deterministic summary
    if not _has_api_key():
        return _build_fallback_response(packets, patient)

    client = _get_client()

    patient_name = patient.get("name", "there").split()[0]
    literacy = patient.get("social_factors", {}).get("health_literacy", "moderate")

    # Build conversation context
    conversation_context = _build_conversation_context(conversation_history or [])

    # Build education context from message + extracted questions
    questions = (signals or {}).get("questions", [])
    education_topics = _find_education_topics(message, questions)
    education_context = _build_education_context(education_topics)

    # Filter packets to only actionable ones (reduces token count)
    filtered_packets = _filter_actionable_packets(packets)

    # Build allowed drugs list from the FULL unfiltered packets for validation
    allowed_drugs = []
    for p in packets:
        drug = p.get("drug")
        if drug:
            dose_parts = []
            if p.get("current_dose_mg") is not None:
                dose_parts.append(f"current {p['current_dose_mg']}mg")
            if p.get("new_dose_mg") is not None:
                dose_parts.append(f"new {p['new_dose_mg']}mg")
            allowed_drugs.append(f"  - {drug} ({', '.join(dose_parts)})" if dose_parts else f"  - {drug}")

    # Prepend onboarding greeting for new anonymous patients
    onboarding_context = ""
    if patient.get("name", "").strip() == "New Patient":
        onboarding_context = ONBOARDING_PREFIX

    # Build allowed drugs constraint to prevent hallucinated medications
    drug_constraint = ""
    if allowed_drugs:
        drug_constraint = "\n\nALLOWED medications — ONLY mention these exact drugs and doses:\n" + "\n".join(allowed_drugs) + "\nDo NOT mention any other medication names or doses.\n"

    from src.orchestrator.iris_prompt import CLINICAL_SYSTEM_PROMPT

    prompt = (onboarding_context + RESPONSE_PROMPT).format(
        iris_persona=CLINICAL_SYSTEM_PROMPT,
        packets_json=json.dumps(filtered_packets, indent=2),
        message=message,
        patient_name=patient_name,
        literacy=literacy,
        conversation_context=conversation_context,
        education_context=education_context,
    ) + drug_constraint

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt]
        )
        return response.text.strip()
    except Exception as e:
        return (
            f"I received your message and our clinical tools have analyzed your "
            f"situation. However, I am having trouble generating a detailed response "
            f"right now. Please contact your care team if you have urgent concerns."
        )


def generate_response_stream(
    packets: list[dict],
    message: str,
    patient: dict,
    conversation_history: list[dict] | None = None,
    signals: dict | None = None,
):
    """Stream a patient-facing response using Gemini, yielding text chunks.

    Same logic as generate_response but uses generate_content_stream.
    Yields string chunks as they arrive from Gemini.
    """
    if not _has_api_key():
        yield _build_fallback_response(packets, patient)
        return

    client = _get_client()

    patient_name = patient.get("name", "there").split()[0]
    literacy = patient.get("social_factors", {}).get("health_literacy", "moderate")

    conversation_context = _build_conversation_context(conversation_history or [])

    questions = (signals or {}).get("questions", [])
    education_topics = _find_education_topics(message, questions)
    education_context = _build_education_context(education_topics)

    filtered_packets = _filter_actionable_packets(packets)

    allowed_drugs = []
    for p in packets:
        drug = p.get("drug")
        if drug:
            dose_parts = []
            if p.get("current_dose_mg") is not None:
                dose_parts.append(f"current {p['current_dose_mg']}mg")
            if p.get("new_dose_mg") is not None:
                dose_parts.append(f"new {p['new_dose_mg']}mg")
            allowed_drugs.append(f"  - {drug} ({', '.join(dose_parts)})" if dose_parts else f"  - {drug}")

    onboarding_context = ""
    if patient.get("name", "").strip() == "New Patient":
        onboarding_context = ONBOARDING_PREFIX

    drug_constraint = ""
    if allowed_drugs:
        drug_constraint = "\n\nALLOWED medications — ONLY mention these exact drugs and doses:\n" + "\n".join(allowed_drugs) + "\nDo NOT mention any other medication names or doses.\n"

    from src.orchestrator.iris_prompt import CLINICAL_SYSTEM_PROMPT

    prompt = (onboarding_context + RESPONSE_PROMPT).format(
        iris_persona=CLINICAL_SYSTEM_PROMPT,
        packets_json=json.dumps(filtered_packets, indent=2),
        message=message,
        patient_name=patient_name,
        literacy=literacy,
        conversation_context=conversation_context,
        education_context=education_context,
    ) + drug_constraint

    try:
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash", contents=[prompt]
        ):
            if chunk.text:
                yield chunk.text
    except Exception:
        yield (
            "I received your message and our clinical tools have analyzed your "
            "situation. However, I am having trouble generating a detailed response "
            "right now. Please contact your care team if you have urgent concerns."
        )
