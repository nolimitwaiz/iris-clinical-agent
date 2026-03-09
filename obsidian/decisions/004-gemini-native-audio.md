# Gemini Native Audio Instead of Separate STT/TTS Services

Date: 2026-03-01
Made By: Architecture decision during Session 3
Reason: Gemini 2.0 Flash processes audio natively. Sending raw audio bytes with the extraction prompt does transcription and clinical signal extraction in a single API call. This eliminates an entire service dependency (Whisper, Deepgram, etc.) and reduces latency from two sequential API calls to one. Gemini 2.5 Flash Preview TTS provides voice output. Browser `speechSynthesis` is the fallback.
Impact: No additional API keys or services needed. Audio extraction uses the same prompt as text extraction. The `api/services/audio.py` module handles both directions. If TTS fails, the React frontend falls back to browser speech synthesis automatically.
