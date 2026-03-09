/**
 * useMicMonitor — lightweight mic monitor for barge-in detection.
 *
 * Opens the microphone with echoCancellation enabled, runs an AnalyserNode
 * RMS loop to detect voice activity. Does NOT record audio. Fires
 * onVoiceDetected when RMS exceeds threshold for confirmationMs.
 */

import { useRef, useEffect, useCallback } from "react";

interface MicMonitorOptions {
  /** Enable monitoring (true only during SPEAKING state). */
  enabled: boolean;
  /** RMS threshold to consider as voice (0-1). Default 0.025. */
  threshold?: number;
  /** Ms of sustained voice before triggering callback. Default 250. */
  confirmationMs?: number;
  /** Called once when voice is confirmed. */
  onVoiceDetected: () => void;
}

export function useMicMonitor({
  enabled,
  threshold = 0.025,
  confirmationMs = 250,
  onVoiceDetected,
}: MicMonitorOptions) {
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number>(0);
  const voiceStartRef = useRef<number>(0);
  const firedRef = useRef(false);

  // Keep callback in ref to avoid re-triggering effect
  const callbackRef = useRef(onVoiceDetected);
  useEffect(() => {
    callbackRef.current = onVoiceDetected;
  }, [onVoiceDetected]);

  const teardown = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    analyserRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    voiceStartRef.current = 0;
    firedRef.current = false;
  }, []);

  useEffect(() => {
    if (!enabled) {
      teardown();
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        streamRef.current = stream;

        const audioCtx = new AudioContext();
        audioCtxRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.3;
        source.connect(analyser);
        analyserRef.current = analyser;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        firedRef.current = false;
        voiceStartRef.current = 0;

        const tick = () => {
          if (!analyserRef.current || cancelled || firedRef.current) return;
          analyserRef.current.getByteTimeDomainData(dataArray);

          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            const v = (dataArray[i] - 128) / 128;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / dataArray.length);

          const now = Date.now();
          if (rms > threshold) {
            if (voiceStartRef.current === 0) {
              voiceStartRef.current = now;
            } else if (now - voiceStartRef.current >= confirmationMs) {
              firedRef.current = true;
              callbackRef.current();
              return;
            }
          } else {
            voiceStartRef.current = 0;
          }

          rafRef.current = requestAnimationFrame(tick);
        };

        rafRef.current = requestAnimationFrame(tick);
      } catch {
        // Mic access denied or unavailable — silently degrade
      }
    })();

    return () => {
      cancelled = true;
      teardown();
    };
  }, [enabled, threshold, confirmationMs, teardown]);
}
