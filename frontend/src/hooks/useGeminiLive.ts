/**
 * useGeminiLive — WebSocket hook for Gemini Live real-time voice sessions.
 *
 * Manages mic capture via AudioWorklet (16kHz PCM), WebSocket transport,
 * and audio playback (24kHz PCM) for bidirectional streaming with the backend.
 */

import { useState, useRef, useCallback, useEffect } from "react";

export type LiveStatus =
  | "disconnected"
  | "connecting"
  | "idle"
  | "listening"
  | "thinking"
  | "speaking";

interface LiveEvents {
  onTranscript?: (text: string) => void;
  onPackets?: (data: {
    action_packets: unknown[];
    validation: unknown;
    signals: unknown;
  }) => void;
  onError?: (message: string) => void;
  onAudioLevel?: (level: number) => void;
}

// AudioWorklet processor source (inlined as a blob URL)
const WORKLET_SOURCE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const float32 = input[0];
    // Convert float32 to 16-bit PCM
    const pcm16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    // Calculate RMS for audio level
    let sum = 0;
    for (let i = 0; i < float32.length; i++) {
      sum += float32[i] * float32[i];
    }
    const rms = Math.sqrt(sum / float32.length);
    this.port.postMessage({ pcm: pcm16.buffer, rms }, [pcm16.buffer]);
    return true;
  }
}
registerProcessor('pcm-capture-processor', PcmCaptureProcessor);
`;

// Resample from source rate to 16kHz
function resamplePcm16(
  pcm16: Int16Array,
  sourceRate: number,
  targetRate: number
): Int16Array {
  if (sourceRate === targetRate) return pcm16;
  const ratio = sourceRate / targetRate;
  const newLength = Math.round(pcm16.length / ratio);
  const result = new Int16Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const srcIndex = Math.min(Math.round(i * ratio), pcm16.length - 1);
    result[i] = pcm16[srcIndex];
  }
  return result;
}

export function useGeminiLive(events?: LiveEvents) {
  const [status, setStatus] = useState<LiveStatus>("disconnected");
  const [transcript, setTranscript] = useState("");

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);

  // Audio playback queue
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);

  const statusRef = useRef<LiveStatus>("disconnected");
  const eventsRef = useRef(events);
  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  const updateStatus = useCallback((s: LiveStatus) => {
    statusRef.current = s;
    setStatus(s);
  }, []);

  const playPcmChunk = useCallback((pcmBytes: ArrayBuffer) => {
    if (!playbackCtxRef.current) {
      playbackCtxRef.current = new AudioContext({ sampleRate: 24000 });
    }
    const ctx = playbackCtxRef.current;
    const int16 = new Int16Array(pcmBytes);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    const now = ctx.currentTime;
    const startTime = Math.max(now, nextPlayTimeRef.current);
    source.start(startTime);
    nextPlayTimeRef.current = startTime + buffer.duration;
  }, []);

  const connect = useCallback(
    async (patientId: string) => {
      if (wsRef.current) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_API_BASE
        ? new URL(import.meta.env.VITE_API_BASE).host
        : "localhost:8000";
      const url = `${protocol}//${host}/ws/voice/${patientId}`;

      updateStatus("connecting");

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.binaryType = "arraybuffer";

      ws.onopen = async () => {
        try {
          // Start mic capture
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              sampleRate: 16000,
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true,
            },
          });
          micStreamRef.current = stream;

          const audioCtx = new AudioContext({ sampleRate: 16000 });
          audioCtxRef.current = audioCtx;

          // Create worklet from inline source
          const blob = new Blob([WORKLET_SOURCE], {
            type: "application/javascript",
          });
          const workletUrl = URL.createObjectURL(blob);
          await audioCtx.audioWorklet.addModule(workletUrl);
          URL.revokeObjectURL(workletUrl);

          const source = audioCtx.createMediaStreamSource(stream);
          const workletNode = new AudioWorkletNode(
            audioCtx,
            "pcm-capture-processor"
          );
          workletNodeRef.current = workletNode;

          workletNode.port.onmessage = (e) => {
            const { pcm, rms } = e.data;
            if (rms !== undefined) {
              eventsRef.current?.onAudioLevel?.(rms);
            }
            if (
              pcm &&
              wsRef.current &&
              wsRef.current.readyState === WebSocket.OPEN
            ) {
              // Resample if needed (browser may give us a different rate)
              const int16 = new Int16Array(pcm);
              const resampled = resamplePcm16(
                int16,
                audioCtx.sampleRate,
                16000
              );
              wsRef.current.send(resampled.buffer);
            }
          };

          source.connect(workletNode);
          workletNode.connect(audioCtx.destination);

          updateStatus("listening");
        } catch {
          eventsRef.current?.onError?.("Microphone access needed");
          updateStatus("disconnected");
        }
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Binary: PCM audio from Gemini
          playPcmChunk(event.data);
        } else {
          // JSON: status, transcript, packets, error
          try {
            const msg = JSON.parse(event.data);
            switch (msg.type) {
              case "status":
                updateStatus(msg.status as LiveStatus);
                break;
              case "transcript":
                setTranscript(msg.text);
                eventsRef.current?.onTranscript?.(msg.text);
                break;
              case "packets":
                eventsRef.current?.onPackets?.(msg);
                break;
              case "error":
                eventsRef.current?.onError?.(msg.message);
                break;
            }
          } catch {
            // Ignore unparseable messages
          }
        }
      };

      ws.onclose = () => {
        cleanup();
        updateStatus("disconnected");
      };

      ws.onerror = () => {
        eventsRef.current?.onError?.("Voice connection failed");
        cleanup();
        updateStatus("disconnected");
      };
    },
    [updateStatus, playPcmChunk]
  );

  const cleanup = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (playbackCtxRef.current) {
      playbackCtxRef.current.close().catch(() => {});
      playbackCtxRef.current = null;
      nextPlayTimeRef.current = 0;
    }
    wsRef.current = null;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: "close" }));
      } catch {
        // ignore
      }
      wsRef.current.close();
    }
    cleanup();
    updateStatus("disconnected");
  }, [cleanup, updateStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      cleanup();
    };
  }, [cleanup]);

  return {
    status,
    transcript,
    connect,
    disconnect,
  };
}
