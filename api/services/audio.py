"""Audio service — Gemini audio extraction and TTS generation."""

import base64
import json
import logging
import os
import re
import struct

from src.orchestrator.extractor import EXTRACTION_PROMPT, EMPTY_SIGNALS

logger = logging.getLogger(__name__)

# TTS voice configuration — extract to constants for easy experimentation.
# Available warm voices (all free): Aoede (Breezy), Achird (Friendly),
# Vindemiatrix (Gentle), Despina (Warm/Smooth)
TTS_VOICE_NAME = "Aoede"
TTS_STYLE_PREFIX = (
    "Read this as a warm, empathetic care companion speaking one on one with a patient. "
    "Use natural pauses between sentences. Vary your intonation like a real conversation, "
    "not a formal announcement. Slightly softer tone for reassuring statements. "
    "Sound genuinely caring, not clinical. "
)

_client = None


def _has_api_key() -> bool:
    """Check if a Gemini API key is available."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _get_client():
    """Get or create the Gemini client."""
    global _client
    if _client is None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        _client = genai.Client(api_key=api_key)
    return _client


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, bits: int = 16, channels: int = 1) -> bytes:
    """Wrap raw PCM data with a WAV header so browsers can play it."""
    data_size = len(pcm_data)
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, channels, sample_rate,
        sample_rate * channels * bits // 8,
        channels * bits // 8, bits,
        b'data', data_size,
    )
    return header + pcm_data


# Prompt for combined transcription + extraction from audio
AUDIO_EXTRACTION_PROMPT = """You are a clinical information extractor. Listen to the patient's audio message and do two things:

1. Transcribe what the patient said into plain text
2. Extract clinical signals from what they said

Return your response as JSON with this exact format:
{
    "transcript": "the exact words the patient said",
    "symptoms": [],
    "side_effects": [],
    "adherence_signals": [],
    "questions": [],
    "barriers_mentioned": [],
    "mood": ""
}

Do not interpret, diagnose, or recommend anything. Only extract what the patient actually said."""


def extract_signals_from_audio(audio_bytes: bytes, mime_type: str) -> dict:
    """Extract clinical signals from audio using Gemini's native audio understanding.

    Args:
        audio_bytes: Raw audio data.
        mime_type: MIME type of the audio (e.g. "audio/webm", "audio/wav").

    Returns:
        Dict with 'signals' (same schema as extract_signals) and 'transcript'.
    """
    if not _has_api_key():
        return {"signals": dict(EMPTY_SIGNALS), "transcript": None}

    try:
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                AUDIO_EXTRACTION_PROMPT,
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        text = response.text.strip()

        # Parse JSON from response
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(text)

        transcript = parsed.pop("transcript", None)

        # Build signals dict
        signals = dict(EMPTY_SIGNALS)
        for key in EMPTY_SIGNALS:
            if key in parsed:
                signals[key] = parsed[key]

        return {"signals": signals, "transcript": transcript}
    except Exception as e:
        logger.error(f"Failed to extract signals from audio: {e}")
        return {"signals": dict(EMPTY_SIGNALS), "transcript": None}


def generate_tts(text: str) -> str | None:
    """Generate TTS audio from text using Gemini TTS.

    Args:
        text: The validated response text to speak.

    Returns:
        Base64 encoded audio string, or None if TTS fails.
    """
    if not _has_api_key():
        return None

    try:
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=TTS_STYLE_PREFIX + text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=TTS_VOICE_NAME
                        )
                    )
                ),
            ),
        )

        audio_data = response.candidates[0].content.parts[0].inline_data.data
        wav_data = _pcm_to_wav(audio_data)
        return base64.b64encode(wav_data).decode("utf-8")
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return None
