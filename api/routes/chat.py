"""Chat API route — core endpoint for the clinical pipeline."""

import base64
import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.main import app_state
from api.schemas import (
    ChatRequest,
    ChatResponse,
    ActionPacketResponse,
    ValidationResult,
    SignalsResponse,
    TTSRequest,
    TTSResponse,
)
from api.services.pipeline_service import process_message, process_audio, process_image_message, process_message_stream
from api.services.onboarding import get_or_create_session, remove_session

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a patient message (text or audio) through the clinical pipeline.

    Flow:
    1. If audio_data: transcribe + extract signals via Gemini audio
    2. If message: extract signals from text via Gemini
    3. Run deterministic pipeline
    4. Generate + validate response
    5. Optionally generate TTS audio
    """
    drug_db = app_state.get("drug_db", [])
    alternatives = app_state.get("alternatives", [])

    if not drug_db:
        raise HTTPException(status_code=503, detail="Drug database not loaded")

    if not request.message and not request.audio_data and not request.image_data:
        raise HTTPException(
            status_code=400,
            detail="Either message, audio_data, or image_data is required",
        )

    # Patient files are named patient_001.json but IDs come as P001
    pid = request.patient_id
    lookup_id = pid.lstrip("P") if pid.startswith("P") else pid

    try:
        if request.image_data:
            # Image mode (optionally with text)
            image_bytes = base64.b64decode(request.image_data)
            mime_type = request.image_mime_type or "image/jpeg"
            result = process_image_message(
                patient_id=lookup_id,
                image_bytes=image_bytes,
                mime_type=mime_type,
                text_message=request.message,
                drug_db=drug_db,
                alternatives=alternatives,
                conversation_history=request.conversation_history,
            )
        elif request.audio_data:
            # Audio mode
            audio_bytes = base64.b64decode(request.audio_data)
            mime_type = request.audio_mime_type or "audio/webm"
            result = process_audio(
                patient_id=lookup_id,
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                drug_db=drug_db,
                alternatives=alternatives,
                conversation_history=request.conversation_history,
            )
        else:
            # Text mode
            result = process_message(
                patient_id=lookup_id,
                message=request.message,
                drug_db=drug_db,
                alternatives=alternatives,
                conversation_history=request.conversation_history,
            )

        return ChatResponse(
            response_text=result["response_text"],
            audio_response=result.get("audio_response"),
            action_packets=[
                ActionPacketResponse(**p) for p in result["action_packets"]
            ],
            validation=ValidationResult(**result["validation"]),
            signals=SignalsResponse(**result["signals"]),
            transcript=result.get("transcript"),
            conversation_history=result.get("conversation_history"),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Patient {request.patient_id} not found"
        )
    except Exception as e:
        logger.exception("Error processing chat request")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream a patient message response via Server-Sent Events.

    Only supports text messages (not audio/image).
    Events: signals, packets, chunk (multiple), validation, replace (if needed), done.
    """
    drug_db = app_state.get("drug_db", [])
    alternatives = app_state.get("alternatives", [])

    if not drug_db:
        raise HTTPException(status_code=503, detail="Drug database not loaded")

    if not request.message:
        raise HTTPException(status_code=400, detail="message is required for streaming")

    pid = request.patient_id
    lookup_id = pid.lstrip("P") if pid.startswith("P") else pid

    def event_generator():
        try:
            yield from process_message_stream(
                patient_id=lookup_id,
                message=request.message,
                drug_db=drug_db,
                alternatives=alternatives,
                conversation_history=request.conversation_history,
            )
        except FileNotFoundError:
            import json
            yield f"event: error\ndata: {json.dumps({'detail': f'Patient {request.patient_id} not found'})}\n\n"
        except Exception as e:
            import json
            logger.exception("Error in streaming chat")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/onboarding")
async def chat_onboarding(request: ChatRequest):
    """Process a message during conversational onboarding.

    Routes to the onboarding state machine instead of the clinical pipeline.
    Returns the next prompt and extraction results.
    """
    pid = request.patient_id
    session = get_or_create_session(pid)

    # Extract data from the message for the current step
    extracted = None
    if request.message:
        try:
            from google import genai as genai_new
            import os
            client = genai_new.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
            extracted = session.extract_data_v2(request.message, client)
        except Exception:
            extracted = session.extract_data(request.message)

    # Advance to next step
    complete = session.advance()

    # Generate response using Gemini with full Iris persona
    response_text = ""
    try:
        from google import genai as genai_new
        import os
        from src.orchestrator.iris_prompt import ONBOARDING_SYSTEM_PROMPT
        client = genai_new.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        step_instruction = session.get_system_instruction()

        history = request.conversation_history or []
        history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])

        # Collected data context so Iris knows what she already has
        collected = session.collected_data
        collected_context = ""
        if collected:
            collected_context = "\nInformation collected so far: " + json.dumps(collected)

        prompt = f"""{ONBOARDING_SYSTEM_PROMPT}

{step_instruction}
{collected_context}

Conversation so far:
{history_text}

Patient just said: "{request.message or '(first interaction, no message yet)'}"

Respond as Iris. One to three sentences. Be natural and warm."""

        result = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt])
        response_text = result.text.strip()
    except Exception as e:
        logger.warning(f"Gemini onboarding generation failed: {e}")
        response_text = "Thank you for sharing that. Let me continue setting up your profile."

    # If complete, build patient data and persist to disk
    patient_data = None
    if complete:
        patient_data = session.build_patient_data()
        remove_session(pid)

        # Merge collected data into existing patient file
        try:
            from src.utils.data_loader import load_patient, save_patient
            lookup_id = pid.lstrip("P") if pid.startswith("P") else pid
            existing = load_patient(lookup_id)
            if patient_data.get("name"):
                existing["name"] = patient_data["name"]
            if patient_data.get("age"):
                existing["age"] = patient_data["age"]
            if patient_data.get("sex") and patient_data["sex"] != "U":
                existing["sex"] = patient_data["sex"]
            if patient_data.get("medical_history"):
                existing["medical_history"] = patient_data["medical_history"]
            if patient_data.get("allergies"):
                existing["allergies"] = patient_data["allergies"]
            if patient_data.get("insurance_tier"):
                existing.setdefault("social_factors", {})["insurance_tier"] = patient_data["insurance_tier"]
            save_patient(existing)
        except Exception as e:
            logger.warning(f"Failed to persist onboarding data: {e}")

    return {
        "response_text": response_text,
        "progress": session.progress if not complete else {"current_step": 8, "total_steps": 8, "step_name": "complete", "complete": True},
        "extracted": extracted,
        "patient_data": patient_data,
        "complete": complete,
    }


@router.get("/education")
async def get_education():
    """Return education content for patient-facing tooltips."""
    from src.orchestrator.responder import EDUCATION_CONTENT
    return EDUCATION_CONTENT


@router.post("/chat/tts", response_model=TTSResponse)
async def tts(request: TTSRequest):
    """Generate TTS audio for a given text (off the critical path).

    The frontend calls this asynchronously after displaying the text response,
    so TTS latency never blocks the user from seeing the reply.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    try:
        from api.services.audio import generate_tts

        audio_b64 = generate_tts(request.text)
        return TTSResponse(audio=audio_b64)
    except Exception as e:
        logger.exception("TTS generation failed")
        raise HTTPException(status_code=500, detail=str(e))
