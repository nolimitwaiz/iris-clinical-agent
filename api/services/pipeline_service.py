"""Pipeline service — wraps the existing orchestrator for API use."""

import os
import logging
from concurrent.futures import ThreadPoolExecutor

from src.utils.data_loader import load_patient, load_drug_database, save_patient
from src.utils.mos import calculate_mos
from src.orchestrator.extractor import extract_signals
from src.orchestrator.responder import generate_response, generate_response_stream
from src.orchestrator.validator import validate_response, get_strict_regeneration_prompt
from src.orchestrator.pipeline import run_pipeline

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

MAX_VALIDATION_RETRIES = 2
MAX_CONVERSATION_TURNS = 50


def _has_api_key() -> bool:
    """Check if a Gemini API key is available."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _retry_with_strict_prompt(
    packets: list[dict],
    message: str,
    patient: dict,
    validation: dict,
) -> tuple[str, dict]:
    """Retry response generation with stricter prompt after validation failure."""
    if not _has_api_key():
        return validation.get("response", ""), validation

    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    patient_name = patient.get("name", "there").split()[0]
    literacy = patient.get("social_factors", {}).get("health_literacy", "moderate")

    draft = validation.get("response", "")
    result = validation

    for _ in range(MAX_VALIDATION_RETRIES):
        strict_prompt = get_strict_regeneration_prompt(
            packets, message, patient_name, literacy, result["violations"]
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=[strict_prompt]
            )
            draft = response.text.strip()
        except Exception:
            break

        result = validate_response(draft, packets)
        if result["approved"]:
            return draft, result

    return draft, result


def _persist_history(patient: dict, message: str, response: str, history: list[dict] | None) -> list[dict]:
    """Append turns to history, trim, persist to patient JSON, return updated history."""
    updated = list(history or patient.get("conversation_history", []))
    updated.append({"role": "patient", "content": message})
    updated.append({"role": "iris", "content": response})
    updated = updated[-MAX_CONVERSATION_TURNS:]
    patient["conversation_history"] = updated
    try:
        save_patient(patient)
    except Exception:
        logger.warning("Could not persist conversation history", exc_info=True)
    return updated


def process_message(
    patient_id: str,
    message: str,
    drug_db: list[dict],
    alternatives: list[dict],
    conversation_history: list[dict] | None = None,
) -> dict:
    """Process a text message through the full clinical pipeline.

    Returns dict with: response_text, action_packets, validation, signals,
    conversation_history.
    """
    # Step 1: Load patient and extract signals in parallel
    patient_future = _executor.submit(load_patient, patient_id)
    signals_future = _executor.submit(extract_signals, message, conversation_history=conversation_history)
    patient = patient_future.result()
    signals = signals_future.result()

    # Step 2: Run deterministic pipeline
    packets = run_pipeline(patient, signals, drug_db, alternatives)

    # Step 3: Generate response (with conversation context + education)
    draft = generate_response(
        packets, message, patient,
        conversation_history=conversation_history,
        signals=signals,
    )

    # Step 4: Validate
    validation = validate_response(draft, packets)

    if not validation["approved"]:
        draft, validation = _retry_with_strict_prompt(
            packets, message, patient, validation
        )

    # Step 5: Persist conversation history (TTS removed from critical path)
    updated_history = _persist_history(patient, message, draft, conversation_history)

    # Step 6: Compute Medication Optimization Score
    mos = calculate_mos(patient, drug_db)

    return {
        "response_text": draft,
        "audio_response": None,
        "action_packets": packets,
        "validation": {
            "approved": validation["approved"],
            "violations": validation.get("violations", []),
        },
        "signals": signals,
        "conversation_history": updated_history,
        "mos": mos,
    }


def process_image_message(
    patient_id: str,
    image_bytes: bytes,
    mime_type: str,
    text_message: str | None,
    drug_db: list[dict],
    alternatives: list[dict],
    conversation_history: list[dict] | None = None,
) -> dict:
    """Process an image (optionally with text) through the clinical pipeline.

    Returns dict with: response_text, action_packets, validation, signals, image_description, conversation_history
    """
    patient = load_patient(patient_id)

    # Step 1: Extract signals from image
    from api.services.image import extract_signals_from_image

    image_result = extract_signals_from_image(image_bytes, mime_type, text_message)
    signals = image_result["signals"]
    image_description = image_result["image_description"]

    # If text was also provided, merge text signals into image signals
    if text_message:
        text_signals = extract_signals(text_message, conversation_history=conversation_history)
        for key in signals:
            if isinstance(signals[key], list) and isinstance(text_signals.get(key), list):
                merged = list(signals[key])
                for item in text_signals[key]:
                    if item not in merged:
                        merged.append(item)
                signals[key] = merged
            elif not signals[key] and text_signals.get(key):
                signals[key] = text_signals[key]

    # Step 2: Run deterministic pipeline
    packets = run_pipeline(patient, signals, drug_db, alternatives)

    # Step 3: Generate response
    message = text_message or "Image sent by patient"
    draft = generate_response(
        packets, message, patient,
        conversation_history=conversation_history,
        signals=signals,
    )

    # Step 4: Validate
    validation = validate_response(draft, packets)

    if not validation["approved"]:
        draft, validation = _retry_with_strict_prompt(
            packets, message, patient, validation
        )

    # Step 5: Persist conversation history
    updated_history = _persist_history(patient, message, draft, conversation_history)

    # Step 6: Compute MOS
    mos = calculate_mos(patient, drug_db)

    return {
        "response_text": draft,
        "action_packets": packets,
        "validation": {
            "approved": validation["approved"],
            "violations": validation.get("violations", []),
        },
        "signals": signals,
        "image_description": image_description,
        "conversation_history": updated_history,
        "mos": mos,
    }


def process_audio(
    patient_id: str,
    audio_bytes: bytes,
    mime_type: str,
    drug_db: list[dict],
    alternatives: list[dict],
    conversation_history: list[dict] | None = None,
) -> dict:
    """Process audio input through the full clinical pipeline.

    Returns dict with: response_text, audio_response, action_packets, validation, signals, transcript, conversation_history
    """
    # Step 1: Load patient and extract signals from audio in parallel
    from api.services.audio import extract_signals_from_audio

    patient_future = _executor.submit(load_patient, patient_id)
    audio_future = _executor.submit(extract_signals_from_audio, audio_bytes, mime_type)
    patient = patient_future.result()
    audio_result = audio_future.result()
    signals = audio_result["signals"]
    transcript = audio_result["transcript"]

    # Step 2: Run deterministic pipeline
    packets = run_pipeline(patient, signals, drug_db, alternatives)

    # Step 3: Generate response
    message = transcript or "Audio message received"
    draft = generate_response(
        packets, message, patient,
        conversation_history=conversation_history,
        signals=signals,
    )

    # Step 4: Validate
    validation = validate_response(draft, packets)

    if not validation["approved"]:
        draft, validation = _retry_with_strict_prompt(
            packets, message, patient, validation
        )

    # Step 5: Persist conversation history (TTS removed from critical path)
    updated_history = _persist_history(patient, message, draft, conversation_history)

    # Step 6: Compute MOS
    mos = calculate_mos(patient, drug_db)

    return {
        "response_text": draft,
        "audio_response": None,
        "action_packets": packets,
        "validation": {
            "approved": validation["approved"],
            "violations": validation.get("violations", []),
        },
        "signals": signals,
        "transcript": transcript,
        "conversation_history": updated_history,
        "mos": mos,
    }


def process_message_stream(
    patient_id: str,
    message: str,
    drug_db: list[dict],
    alternatives: list[dict],
    conversation_history: list[dict] | None = None,
):
    """Process a text message and stream SSE events.

    Yields SSE-formatted strings:
      event: signals\ndata: {...}\n\n
      event: packets\ndata: {...}\n\n
      event: chunk\ndata: {...}\n\n   (multiple)
      event: validation\ndata: {...}\n\n
      event: replace\ndata: {...}\n\n  (only if validation fails)
      event: done\ndata: {...}\n\n
    """
    import json as _json

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {_json.dumps(data)}\n\n"

    # Step 1: Load patient and extract signals in parallel
    patient_future = _executor.submit(load_patient, patient_id)
    signals_future = _executor.submit(extract_signals, message, conversation_history=conversation_history)
    patient = patient_future.result()
    signals = signals_future.result()

    yield _sse("signals", signals)

    # Step 2: Run deterministic pipeline
    packets = run_pipeline(patient, signals, drug_db, alternatives)

    yield _sse("packets", {"action_packets": packets})

    # Step 3: Stream response chunks
    full_text_parts = []
    for chunk in generate_response_stream(
        packets, message, patient,
        conversation_history=conversation_history,
        signals=signals,
    ):
        full_text_parts.append(chunk)
        yield _sse("chunk", {"text": chunk})

    full_text = "".join(full_text_parts).strip()

    # Step 4: Validate the full response
    validation = validate_response(full_text, packets)

    if not validation["approved"]:
        # Retry with strict prompt
        corrected, validation = _retry_with_strict_prompt(
            packets, message, patient, validation
        )
        if corrected != full_text:
            full_text = corrected
            yield _sse("replace", {"text": full_text})

    yield _sse("validation", {
        "approved": validation["approved"],
        "violations": validation.get("violations", []),
    })

    # Step 5: Persist conversation history
    updated_history = _persist_history(patient, message, full_text, conversation_history)

    # Step 6: Compute MOS
    mos = calculate_mos(patient, drug_db)

    yield _sse("done", {
        "response_text": full_text,
        "conversation_history": updated_history,
        "mos": mos,
    })
