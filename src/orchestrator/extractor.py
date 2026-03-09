"""LLM Extractor — uses Gemini 2.0 Flash to extract structured signals."""

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


EXTRACTION_PROMPT = """You are a clinical information extractor. Given a patient message, extract ONLY the following as JSON. Do not interpret, diagnose, or recommend anything.
{{
    "symptoms": [],
    "side_effects": [],
    "adherence_signals": [],
    "questions": [],
    "barriers_mentioned": [],
    "mood": ""
}}
Patient message: {message}"""

EMPTY_SIGNALS = {
    "symptoms": [],
    "side_effects": [],
    "adherence_signals": [],
    "questions": [],
    "barriers_mentioned": [],
    "mood": "",
}


def _build_context_prefix(conversation_history: list[dict], max_turns: int = 4) -> str:
    """Build a conversation context string from recent history."""
    if not conversation_history:
        return ""
    recent = conversation_history[-max_turns:]
    lines = ["Previous conversation for context (extract ONLY from the NEW message below, not from history):"]
    for turn in recent:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        lines.append(f"  {role}: {content}")
    lines.append("")
    return "\n".join(lines)


def extract_signals(message: str, conversation_history: list[dict] | None = None) -> dict:
    """Extract structured clinical signals from a patient message using Gemini.

    Args:
        message: The patient's message text.
        conversation_history: Optional list of prior turns for context.

    Returns:
        A dict with keys: symptoms, side_effects, adherence_signals, questions,
        barriers_mentioned, mood.
    """
    if not message or not message.strip():
        return dict(EMPTY_SIGNALS)

    # Demo mode: no API key — return empty signals so pipeline still runs
    if not _has_api_key():
        return dict(EMPTY_SIGNALS)

    client = _get_client()
    context_prefix = _build_context_prefix(conversation_history or [])
    prompt = context_prefix + EXTRACTION_PROMPT.format(message=message)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents=[prompt]
        )
        text = response.text.strip()

        # Try to extract JSON from the response (may have markdown fences)
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(text)

        # Validate and fill in missing keys
        result = dict(EMPTY_SIGNALS)
        for key in EMPTY_SIGNALS:
            if key in parsed:
                result[key] = parsed[key]
        return result
    except Exception:
        # On any error, return empty signals rather than crashing
        return dict(EMPTY_SIGNALS)
