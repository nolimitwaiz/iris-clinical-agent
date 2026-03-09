# SDK Migration from google-generativeai to google-genai

Date: 2026-03-01
Made By: Technical requirement for audio support
Reason: The `google-generativeai` SDK (old) was deprecated (EOL August 2025) and does not support native audio input via `types.Part.from_bytes()` or Gemini TTS via `response_modalities=["AUDIO"]`. The new `google-genai` SDK is required for multimodal features. Migration was also needed to stay on a supported SDK.
Impact: Three source files modified (`extractor.py`, `responder.py`, `chat_interface.py`). Pattern changed from global `genai.configure()` to explicit `genai.Client()`. All 81 tests pass unchanged because clinical tools have no SDK dependency.
