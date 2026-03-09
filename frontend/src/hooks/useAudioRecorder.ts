/**
 * Hook for capturing microphone audio via MediaRecorder API.
 *
 * Includes real-time audio level monitoring (via AnalyserNode) and
 * Voice Activity Detection (VAD) that auto-fires onSilence when the
 * user stops speaking.
 */

import { useRef, useState, useCallback, useEffect } from "react";

/** Normalized 0-1 audio level, updated ~60fps while recording. */
export type AudioLevelCallback = (level: number) => void;

interface AudioRecorderOptions {
  /** Called ~60fps with normalized 0-1 audio level while recording. */
  onAudioLevel?: AudioLevelCallback;
  /** Called once when silence is detected after speech. */
  onSilence?: () => void;
  /** RMS threshold below which audio counts as silence (0-1). Default 0.015. */
  silenceThreshold?: number;
  /** Milliseconds of continuous silence before triggering onSilence. Default 1500. */
  silenceDuration?: number;
  /** Minimum recording time in ms before silence detection activates. Default 600. */
  minRecordingMs?: number;
}

interface AudioRecorderResult {
  isRecording: boolean;
  audioLevel: number;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<{ base64: string; mimeType: string } | null>;
}

export function useAudioRecorder(
  options: AudioRecorderOptions = {}
): AudioRecorderResult {
  const {
    onAudioLevel,
    onSilence,
    silenceThreshold = 0.015,
    silenceDuration = 1500,
    minRecordingMs = 600,
  } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Audio analysis refs
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number>(0);

  // VAD refs
  const speechDetectedRef = useRef(false);
  const silenceStartRef = useRef(0);
  const recordingStartRef = useRef(0);
  const silenceFiredRef = useRef(false);

  // Keep callbacks in refs so the animation loop always sees the latest
  const onAudioLevelRef = useRef(onAudioLevel);
  const onSilenceRef = useRef(onSilence);
  useEffect(() => { onAudioLevelRef.current = onAudioLevel; }, [onAudioLevel]);
  useEffect(() => { onSilenceRef.current = onSilence; }, [onSilence]);

  const cleanup = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  }, []);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // ── Audio analysis setup ──────────────────────────────────
      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.4;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Reset VAD state
      speechDetectedRef.current = false;
      silenceStartRef.current = 0;
      silenceFiredRef.current = false;
      recordingStartRef.current = Date.now();

      // ── Level monitoring + VAD loop ───────────────────────────
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const tick = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteTimeDomainData(dataArray);

        // Compute RMS (root mean square) for a normalized 0-1 level
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          const v = (dataArray[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        const level = Math.min(rms * 3, 1); // amplify for visual range

        setAudioLevel(level);
        onAudioLevelRef.current?.(level);

        // ── VAD logic ─────────────────────────────────────────
        const now = Date.now();
        const elapsed = now - recordingStartRef.current;

        if (rms > silenceThreshold) {
          speechDetectedRef.current = true;
          silenceStartRef.current = 0;
        } else if (speechDetectedRef.current && elapsed > minRecordingMs) {
          // Speech was detected and now it's quiet
          if (silenceStartRef.current === 0) {
            silenceStartRef.current = now;
          } else if (
            now - silenceStartRef.current > silenceDuration &&
            !silenceFiredRef.current
          ) {
            silenceFiredRef.current = true;
            onSilenceRef.current?.();
            return; // stop the loop
          }
        }

        rafRef.current = requestAnimationFrame(tick);
      };

      rafRef.current = requestAnimationFrame(tick);

      // ── MediaRecorder setup ───────────────────────────────────
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/mp4";

      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250); // collect chunks every 250ms for snappier stop
      setIsRecording(true);
    } catch (err) {
      console.error("Failed to start recording:", err);
      cleanup();
      throw err;
    }
  }, [silenceThreshold, silenceDuration, minRecordingMs, cleanup]);

  const stopRecording = useCallback(async (): Promise<{
    base64: string;
    mimeType: string;
  } | null> => {
    cleanup();

    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      // Release mic even if recorder is gone
      streamRef.current?.getTracks().forEach((t) => t.stop());
      setIsRecording(false);
      return null;
    }

    return new Promise((resolve) => {
      recorder.onstop = async () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });

        // Stop all tracks to release the microphone
        streamRef.current?.getTracks().forEach((t) => t.stop());

        // Convert to base64 via arrayBuffer (faster than FileReader)
        const buffer = await blob.arrayBuffer();
        const bytes = new Uint8Array(buffer);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
        resolve({
          base64: btoa(binary),
          mimeType: mimeType.split(";")[0],
        });
        setIsRecording(false);
      };

      recorder.stop();
    });
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [cleanup]);

  return { isRecording, audioLevel, startRecording, stopRecording };
}
