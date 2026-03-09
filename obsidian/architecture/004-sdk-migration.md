# Gemini SDK Migration

Date: 2026-03-01
Status: Decided

## Context

The codebase used `google-generativeai` (the old Gemini Python SDK). This SDK was deprecated with EOL August 2025. More importantly, the new `google-genai` SDK is required for:

1. Native audio input (sending audio bytes directly to Gemini 2.0 Flash)
2. Gemini TTS (text to speech via `gemini-2.5-flash-preview-tts`)
3. Multimodal content with `types.Part.from_bytes()`

## Decision

Migrate from `google-generativeai` to `google-genai` across all files that interact with the Gemini API.

### Old Pattern (google-generativeai)

```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content(prompt)
text = response.text
```

### New Pattern (google-genai)

```python
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(
    model="gemini-2.0-flash", contents=[prompt]
)
text = response.text
```

### Files Modified

| File | Change |
|------|--------|
| `src/orchestrator/extractor.py` | Replaced `_CONFIGURED` global + `genai.configure()` with `_client` global + `genai.Client()` |
| `src/orchestrator/responder.py` | Same pattern migration |
| `src/frontend/chat_interface.py` | Updated retry logic to use new Client |
| `requirements.txt` | `google-generativeai>=0.3.0` replaced with `google-genai>=1.0.0` |

### Audio Capabilities Enabled

```python
from google.genai import types

# Audio input (transcription + extraction in one call)
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type="audio/webm")]
)

# TTS output
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=text,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
            )
        )
    )
)
```

## Alternatives Considered

1. **Keep old SDK + add REST calls for audio:** Rejected. Two different methods of calling the same API adds complexity and maintenance burden.
2. **Use a separate STT service (Whisper/Deepgram) + old SDK:** Rejected. Gemini 2.0 Flash handles audio natively, removing an entire service dependency.

## Consequences

- All 81 existing tests pass without modification (clinical tools don't touch the SDK)
- Demo mode (no API key) behavior unchanged
- New SDK uses Client object pattern (more explicit than global configure)
- Lazy client initialization preserved (client created on first API call)
- Audio features available without additional dependencies
