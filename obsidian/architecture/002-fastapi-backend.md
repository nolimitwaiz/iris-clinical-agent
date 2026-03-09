# FastAPI Backend Layer

Date: 2026-03-01
Status: Decided

## Context

The existing clinical pipeline (6 tools, orchestrator, validator) was tightly coupled to Streamlit via `src/frontend/chat_interface.py`. Building a voice first React frontend required exposing the pipeline as an HTTP API. The Streamlit app also could not handle audio input/output or real time voice interactions.

## Decision

Add a FastAPI backend in `api/` that wraps the existing pipeline without modifying any clinical tool code. The API layer is a thin translation between HTTP requests and the existing Python orchestrator.

### Architecture

```
api/
  main.py              FastAPI app, CORS, lifespan (loads drug_db + alternatives)
  schemas.py           Pydantic models for request/response validation
  routes/
    patients.py        GET /api/patients, GET /api/patients/{id}
    chat.py            POST /api/chat (text + audio)
  services/
    pipeline_service.py    Wraps orchestrator: extract > pipeline > respond > validate
    audio.py               Gemini audio extraction + TTS generation
```

### Endpoint Design

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check, reports Gemini key status and data loading |
| `/api/patients` | GET | List all 5 patients (summary) |
| `/api/patients/{id}` | GET | Full patient detail |
| `/api/chat` | POST | Core pipeline endpoint, accepts text or audio |

### Chat Endpoint Flow

```
Request: { patient_id, message?, audio_data?, audio_mime_type? }
    1. If audio_data: Gemini transcribes + extracts signals in one call
    2. If message: existing extract_signals() for text
    3. run_pipeline(patient, signals, drug_db, alternatives)
    4. generate_response(packets, message, patient)
    5. validate_response(draft, packets) with up to 2 retries
    6. If audio mode: generate TTS via Gemini TTS
Response: { response_text, audio_response?, action_packets, validation, signals, transcript? }
```

### Key Principles

- **No clinical code modified.** All `src/tools/`, `pipeline.py`, `validator.py` untouched.
- **Shared state via lifespan.** Drug database and alternatives loaded once at startup into `app_state` dict, shared across requests.
- **CORS restricted.** Only `localhost:5173` and `localhost:5174` allowed (Vite dev server).
- **Streamlit preserved.** `app.py` still works as a fallback text interface.

## Alternatives Considered

1. **WebSocket API:** Considered for streaming voice, but Gemini processes complete audio chunks, not streams. WebSocket complexity not justified for request/response pattern.
2. **Modify Streamlit to serve API:** Rejected. Streamlit is not designed as an API server and cannot handle audio or CORS properly.
3. **Merge into existing src/:** Rejected. Keeping `api/` separate maintains clear boundary between HTTP layer and clinical logic.

## Consequences

- Two frontends can run simultaneously (Streamlit on 8501, React on 5173)
- Future mobile apps or integrations can use the same API
- Pipeline execution is stateless per request (no server side session)
- Audio processing adds latency (Gemini API calls for transcription + TTS)
- Testing the API layer requires running FastAPI server (existing pytest suite tests clinical logic independently)
