"""Image service — Gemini multimodal extraction from images."""

import json
import logging
import os
import re

from src.orchestrator.extractor import EMPTY_SIGNALS

logger = logging.getLogger(__name__)

_client = None

IMAGE_EXTRACTION_PROMPT = """You are a clinical information extractor. Analyze this image sent by a heart failure patient and extract relevant clinical signals.

The image may be:
- A medication bottle label (extract drug name, dosage, frequency)
- A lab report (extract lab values like potassium, creatinine, eGFR, BNP)
- A blood pressure or weight reading
- A general photo with relevant clinical context

Return your response as JSON with this exact format:
{
    "image_description": "brief description of what the image shows",
    "symptoms": [],
    "side_effects": [],
    "adherence_signals": [],
    "questions": [],
    "barriers_mentioned": [],
    "mood": "",
    "extracted_values": {}
}

The extracted_values field should contain any numeric values found (e.g. {"systolic_bp": 130, "weight_kg": 75}).

Do not interpret, diagnose, or recommend anything. Only extract what is visible in the image."""


def _has_api_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _get_client():
    global _client
    if _client is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        _client = genai.Client(api_key=api_key)
    return _client


def extract_signals_from_image(
    image_bytes: bytes,
    mime_type: str,
    text_message: str | None = None,
) -> dict:
    """Extract clinical signals from an image using Gemini multimodal.

    Args:
        image_bytes: Raw image data.
        mime_type: MIME type (e.g. "image/jpeg", "image/png").
        text_message: Optional accompanying text message for context.

    Returns:
        Dict with 'signals' (same schema as extract_signals) and 'image_description'.
    """
    if not _has_api_key():
        return {"signals": dict(EMPTY_SIGNALS), "image_description": None}

    try:
        from google.genai import types

        client = _get_client()

        contents = [IMAGE_EXTRACTION_PROMPT]
        if text_message:
            contents.append(f"The patient also said: {text_message}")
        contents.append(
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        text = response.text.strip()

        # Parse JSON from response
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(text)

        image_description = parsed.pop("image_description", None)
        parsed.pop("extracted_values", None)

        # Build signals dict
        signals = dict(EMPTY_SIGNALS)
        for key in EMPTY_SIGNALS:
            if key in parsed:
                signals[key] = parsed[key]

        return {"signals": signals, "image_description": image_description}
    except Exception:
        logger.exception("Failed to extract signals from image")
        return {"signals": dict(EMPTY_SIGNALS), "image_description": None}
