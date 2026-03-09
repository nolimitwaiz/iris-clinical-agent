"""WebSocket endpoint for Gemini Live real-time voice sessions.

Proxies bidirectional audio between the browser and a Gemini Live session.
Gemini handles VAD, transcription, tool calling, and spoken response generation.
The backend executes the clinical pipeline when Gemini calls run_clinical_pipeline.
"""

import asyncio
import json
import logging
import os
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_system_instruction(patient_name: str) -> str:
    """Build the Gemini Live system instruction."""
    return (
        f"You are Iris, a compassionate heart failure care assistant speaking with {patient_name}. "
        "Rules you MUST follow:\n"
        "1. ALWAYS call the run_clinical_pipeline tool with the patient's message before responding "
        "with any clinical information. NEVER invent medications, doses, lab values, or clinical "
        "recommendations on your own.\n"
        "2. After the tool returns, relay the response_text naturally in a warm, conversational tone. "
        "You may rephrase slightly for spoken delivery but do NOT add any clinical facts not in the "
        "tool output.\n"
        "3. Do not use hyphens. Use spaces instead.\n"
        "4. For greetings and non clinical chat, respond briefly and warmly in one to two sentences. "
        "Never mention medications, doses, or lab values in casual responses.\n"
        "5. Keep responses concise and clear. Explain medical terms in simple language.\n"
        "6. Be empathetic and supportive."
    )


def _build_tool_declaration() -> dict:
    """Build the run_clinical_pipeline function declaration for Gemini."""
    return {
        "name": "run_clinical_pipeline",
        "description": (
            "Process a patient message through the clinical pipeline. "
            "Returns validated clinical response text and action packets. "
            "MUST be called before providing any clinical information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The patient's message to process through the clinical pipeline",
                }
            },
            "required": ["message"],
        },
    }


@router.websocket("/ws/voice/{patient_id}")
async def voice_websocket(websocket: WebSocket, patient_id: str):
    """Real-time voice session using Gemini Live API.

    Protocol:
    - Client sends binary frames: raw PCM audio (16kHz, 16-bit, mono)
    - Server sends binary frames: raw PCM audio (24kHz, 16-bit, mono)
    - Server sends JSON text frames: status and transcript events
    """
    await websocket.accept()

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        await websocket.send_json({
            "type": "error",
            "message": "google-genai package not installed. Install with: pip install google-genai",
        })
        await websocket.close()
        return

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        await websocket.send_json({
            "type": "error",
            "message": "GEMINI_API_KEY not configured",
        })
        await websocket.close()
        return

    # Load patient and pipeline dependencies
    from api.main import app_state
    from src.utils.data_loader import load_patient
    from api.services.pipeline_service import process_message
    from src.orchestrator.validator import validate_live_transcript
    from api.services.onboarding import get_or_create_session

    try:
        lookup_id = patient_id.lstrip("P") if patient_id.startswith("P") else patient_id
        patient = load_patient(lookup_id)
    except FileNotFoundError:
        await websocket.send_json({
            "type": "error",
            "message": f"Patient {patient_id} not found",
        })
        await websocket.close()
        return

    drug_db = app_state.get("drug_db", [])
    alternatives = app_state.get("alternatives", [])
    patient_name = patient.get("name", "the patient")
    conversation_history: list[dict] = list(patient.get("conversation_history", []))
    allowed_drugs_from_pipeline: set[str] = set()

    # Configure Gemini client
    client = genai.Client(api_key=api_key)

    tool_declaration = _build_tool_declaration()
    system_instruction = _build_system_instruction(patient_name)

    live_config = genai_types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=genai_types.SpeechConfig(
            voice_config=genai_types.VoiceConfig(
                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                    voice_name="Aoede",
                )
            )
        ),
        system_instruction=genai_types.Content(
            parts=[genai_types.Part(text=system_instruction)]
        ),
        tools=[genai_types.Tool(function_declarations=[
            genai_types.FunctionDeclaration(**tool_declaration)
        ])],
    )

    async def _send_status(status: str):
        try:
            await websocket.send_json({"type": "status", "status": status})
        except Exception:
            pass

    try:
        async with client.aio.live.connect(
            model="gemini-2.0-flash-exp",
            config=live_config,
        ) as session:
            await _send_status("listening")

            # Task: forward audio from frontend to Gemini
            async def forward_audio_to_gemini():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data and data["bytes"]:
                            await session.send(
                                input=genai_types.LiveClientRealtimeInput(
                                    media_chunks=[
                                        genai_types.Blob(
                                            data=data["bytes"],
                                            mime_type="audio/pcm;rate=16000",
                                        )
                                    ]
                                )
                            )
                        elif "text" in data:
                            msg = json.loads(data["text"])
                            if msg.get("type") == "close":
                                break
                except WebSocketDisconnect:
                    pass
                except Exception:
                    logger.warning("Forward audio task ended", exc_info=True)

            # Task: forward responses from Gemini to frontend
            async def forward_gemini_to_frontend():
                try:
                    async for response in session.receive():
                        # Handle tool calls
                        if response.tool_call:
                            await _send_status("thinking")
                            for fc in response.tool_call.function_calls:
                                if fc.name == "run_clinical_pipeline":
                                    message_text = fc.args.get("message", "")
                                    try:
                                        result = process_message(
                                            patient_id=lookup_id,
                                            message=message_text,
                                            drug_db=drug_db,
                                            alternatives=alternatives,
                                            conversation_history=conversation_history,
                                        )
                                        response_text = result["response_text"]
                                        # Update local history
                                        conversation_history.clear()
                                        conversation_history.extend(
                                            result.get("conversation_history", [])
                                        )
                                        # Track allowed drugs for transcript validation
                                        for pkt in result["action_packets"]:
                                            drug = pkt.get("drug")
                                            if drug:
                                                allowed_drugs_from_pipeline.add(drug.lower())
                                        # Send action packets to frontend
                                        await websocket.send_json({
                                            "type": "packets",
                                            "action_packets": result["action_packets"],
                                            "validation": result["validation"],
                                            "signals": result["signals"],
                                        })
                                        # Send tool response back to Gemini
                                        await session.send(
                                            input=genai_types.LiveClientToolResponse(
                                                function_responses=[
                                                    genai_types.FunctionResponse(
                                                        name="run_clinical_pipeline",
                                                        id=fc.id,
                                                        response={"response_text": response_text},
                                                    )
                                                ]
                                            )
                                        )
                                    except Exception:
                                        logger.error("Pipeline error", exc_info=True)
                                        await session.send(
                                            input=genai_types.LiveClientToolResponse(
                                                function_responses=[
                                                    genai_types.FunctionResponse(
                                                        name="run_clinical_pipeline",
                                                        id=fc.id,
                                                        response={
                                                            "response_text": (
                                                                "I'm having trouble processing that right now. "
                                                                "Could you try again?"
                                                            )
                                                        },
                                                    )
                                                ]
                                            )
                                        )

                        # Handle audio data
                        if response.data:
                            await _send_status("speaking")
                            try:
                                await websocket.send_bytes(response.data)
                            except Exception:
                                break

                        # Handle text (transcript) — validate for hallucinated clinical content
                        if response.text:
                            try:
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": response.text,
                                })
                                # Validate transcript for hallucinated drugs/doses
                                vresult = validate_live_transcript(
                                    response.text, allowed_drugs_from_pipeline or None
                                )
                                if not vresult["clean"]:
                                    await websocket.send_json({
                                        "type": "correction",
                                        "message": vresult["correction_message"],
                                    })
                            except Exception:
                                break

                        # Handle turn completion
                        if response.server_content and response.server_content.turn_complete:
                            await _send_status("listening")

                except Exception:
                    logger.warning("Gemini receive task ended", exc_info=True)

            # Run both tasks concurrently
            audio_task = asyncio.create_task(forward_audio_to_gemini())
            gemini_task = asyncio.create_task(forward_gemini_to_frontend())

            done, pending = await asyncio.wait(
                [audio_task, gemini_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    except WebSocketDisconnect:
        logger.info(f"Voice session disconnected: patient {patient_id}")
    except Exception:
        logger.error(f"Voice session error: {traceback.format_exc()}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Voice session encountered an error",
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
