/**
 * RadialNodes — 80-node 2D radial waveform orb.
 *
 * The user's original design: flat circle with spokes from center,
 * outer connecting ring, multi-harmonic displacement.
 * Manages its own state machine: idle -> listening -> thinking -> speaking.
 * Theme-aware: dark = white on black, beige = dark brown on beige.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useAudioRecorder } from "../../hooks/useAudioRecorder";
import { useGeminiLive } from "../../hooks/useGeminiLive";
import { sendChat, sendChatStream, fetchTTS, sendOnboardingChat } from "../../api/client";
import type { StreamEvent } from "../../api/client";
import { useTheme, glassStyle } from "../../context/ThemeContext";
import { useIris } from "../../context/IrisContext";
import { useIsMobile, useIsTablet } from "../../hooks/useMediaQuery";
import { useMicMonitor } from "../../hooks/useMicMonitor";
import type { ChatResponse } from "../../api/types";
import ClinicalGraph from "./ClinicalGraph";

const STATES = {
  IDLE: "idle",
  LISTENING: "listening",
  THINKING: "thinking",
  SPEAKING: "speaking",
} as const;

type OrbStateValue = (typeof STATES)[keyof typeof STATES];

const STATE_LABELS: Record<OrbStateValue, string> = {
  [STATES.IDLE]: "Tap to speak",
  [STATES.LISTENING]: "Listening\u2026 tap to send",
  [STATES.THINKING]: "Thinking\u2026",
  [STATES.SPEAKING]: "Speaking\u2026",
};

const LIVE_STATE_LABELS: Record<OrbStateValue, string> = {
  [STATES.IDLE]: "Tap to start",
  [STATES.LISTENING]: "Listening\u2026",
  [STATES.THINKING]: "Thinking\u2026",
  [STATES.SPEAKING]: "Speaking\u2026",
};

const isLiveEnabled = Boolean(
  typeof import.meta !== "undefined" &&
  import.meta.env?.VITE_GEMINI_LIVE === "true"
);

/** Play base64-encoded WAV audio from Gemini TTS. Returns when playback ends. */
async function playTTSAudio(
  base64Wav: string,
  audioRef?: React.MutableRefObject<HTMLAudioElement | null>,
): Promise<void> {
  const audio = new Audio(`data:audio/wav;base64,${base64Wav}`);
  if (audioRef) audioRef.current = audio;
  return new Promise((resolve, reject) => {
    audio.onended = () => {
      if (audioRef) audioRef.current = null;
      resolve();
    };
    audio.onerror = () => {
      if (audioRef) audioRef.current = null;
      reject(new Error("TTS playback failed"));
    };
    audio.play().catch((err) => {
      if (audioRef) audioRef.current = null;
      reject(err);
    });
  });
}

export interface ConversationTurn {
  role: "patient" | "iris";
  content: string;
}

interface Props {
  patientId: string;
  conversations: ConversationTurn[];
  onResponse?: (response: ChatResponse) => void;
}

export default function RadialNodes({
  patientId,
  conversations,
  onResponse,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const stateRef = useRef<OrbStateValue>(STATES.IDLE);
  const [currentState, setCurrentState] = useState<OrbStateValue>(STATES.IDLE);
  const timeRef = useRef<number>(0);
  const deformRef = useRef<number>(0);
  const targetDeformRef = useRef<number>(0);
  const breathRef = useRef<number>(0);
  const noiseRef = useRef<number[]>(
    Array.from({ length: 20 }, () => Math.random() * Math.PI * 2)
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [connectingLabel, setConnectingLabel] = useState<string | null>(null);
  const errorTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const { theme: t } = useTheme();
  const { addPatientMessage, addIrisResponse, setPackets, backendConnected, startNewPatient, setOrbState, setStreamingText, isOnboarding, setOnboardingProgress, completeOnboarding } = useIris();

  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
  const orbSize = isMobile ? "min(85vw, 60vh, 320px)" : isTablet ? "min(80vw, 60vh, 400px)" : "min(80vw, 60vh, 420px)";

  // Onboarding auto-greet guard
  const greetedRef = useRef(false);

  // Tap-to-activate gate: no greeting until user taps
  const activatedRef = useRef(false);
  const [activated, setActivated] = useState(false);

  // Clinical knowledge graph (double-tap)
  const [showGraph, setShowGraph] = useState(false);

  // Track live mode failures — auto-fallback to REST after 2 failures
  const liveFailCountRef = useRef(0);
  const [liveFailed, setLiveFailed] = useState(false);
  const isLiveMode = isLiveEnabled && backendConnected && !liveFailed;

  // Real-time audio level from mic (drives orb in LISTENING state)
  const micLevelRef = useRef(0);

  // Refs for live event callbacks (avoids dependency on showError which is defined below)
  const showErrorRef = useRef<(msg: string) => void>(() => { });

  // Gemini Live hook — events bridge live session state to orb
  const liveEvents = useMemo(
    () => ({
      onTranscript: (text: string) => {
        addPatientMessage(text);
      },
      onPackets: (data: {
        action_packets: unknown[];
        validation: unknown;
        signals: unknown;
      }) => {
        setPackets(data.action_packets as import("../../api/types").ActionPacket[]);
      },
      onError: (msg: string) => {
        // Track live mode failures — auto-fallback after 2
        liveFailCountRef.current += 1;
        if (liveFailCountRef.current >= 2) {
          setLiveFailed(true);
          showErrorRef.current("Switching to voice recording mode");
        } else {
          showErrorRef.current(msg);
        }
      },
      onAudioLevel: (level: number) => {
        micLevelRef.current = level;
      },
    }),
    [addPatientMessage, setPackets]
  );

  const {
    status: liveStatus,
    connect: liveConnect,
    disconnect: liveDisconnect,
  } = useGeminiLive(liveEvents);

  // Sync live status to orb state & track unexpected disconnections
  const prevLiveStatusRef = useRef(liveStatus);
  useEffect(() => {
    if (!isLiveMode) return;
    // If we went from a connected state back to disconnected unexpectedly, count as failure
    const prev = prevLiveStatusRef.current;
    if (liveStatus === "disconnected" && prev !== "disconnected" && prev !== "idle") {
      liveFailCountRef.current += 1;
      if (liveFailCountRef.current >= 2) {
        setLiveFailed(true);
        showErrorRef.current("Switching to voice recording mode");
      }
    }
    prevLiveStatusRef.current = liveStatus;

    const statusMap: Record<string, OrbStateValue> = {
      disconnected: STATES.IDLE,
      connecting: STATES.THINKING,
      idle: STATES.IDLE,
      listening: STATES.LISTENING,
      thinking: STATES.THINKING,
      speaking: STATES.SPEAKING,
    };
    const mapped = statusMap[liveStatus] ?? STATES.IDLE;
    stateRef.current = mapped;
    setCurrentState(mapped);
    if (liveStatus === "connecting") {
      setConnectingLabel("Connecting\u2026");
    } else {
      setConnectingLabel(null);
    }
  }, [isLiveMode, liveStatus]);

  // Audio recording with VAD
  const handleSilence = useCallback(() => {
    // Auto-send when user stops speaking — simulate a "stop" tap
    if (stateRef.current === STATES.LISTENING) {
      // Trigger the handleTap logic for LISTENING → THINKING
      // We dispatch a synthetic click so handleTap picks it up
      canvasRef.current?.click();
    }
  }, []);

  const { startRecording, stopRecording } = useAudioRecorder({
    onAudioLevel: useCallback((level: number) => {
      micLevelRef.current = level;
    }, []),
    onSilence: handleSilence,
    silenceThreshold: 0.012,
    silenceDuration: 1000,
    minRecordingMs: 500,
  });
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Store theme ref for canvas animation loop
  const themeRef = useRef(t);
  useEffect(() => { themeRef.current = t; }, [t]);

  const showError = useCallback((msg: string) => {
    setErrorMsg(msg);
    if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
    errorTimeoutRef.current = setTimeout(() => setErrorMsg(null), 6000);
  }, []);
  showErrorRef.current = showError;

  // Pre-fetch TTS Voices immediately so they are cached before use.
  // This explicitly fixes the bug where the first query uses a robotic default voice.
  useEffect(() => {
    if ("speechSynthesis" in window) {
      speechSynthesis.getVoices();
      const handler = () => {
        speechSynthesis.getVoices();
      };
      speechSynthesis.addEventListener("voiceschanged", handler);
      return () => {
        speechSynthesis.removeEventListener("voiceschanged", handler);
      };
    }
  }, []);

  const updateState = useCallback((s: OrbStateValue) => {
    stateRef.current = s;
    setCurrentState(s);
    setOrbState(s);
  }, [setOrbState]);

  // Barge-in: user speaks over Iris → stop TTS, start listening
  const handleBargeIn = useCallback(() => {
    if (stateRef.current !== STATES.SPEAKING) return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    speechSynthesis.cancel();
    updateState(STATES.LISTENING);
    startRecording().catch(() => updateState(STATES.IDLE));
  }, [updateState, startRecording]);

  // Monitor mic during SPEAKING for barge-in detection
  useMicMonitor({
    enabled: currentState === STATES.SPEAKING,
    onVoiceDetected: handleBargeIn,
  });

  const speakWithBrowser = useCallback(
    (text: string) => {
      if (!("speechSynthesis" in window)) {
        updateState(STATES.IDLE);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);

      // Pick the most natural sounding voice available.
      // Thanks to the global pre-fetch effect, this array will be populated right away.
      const voices = speechSynthesis.getVoices();
      if (voices.length > 0) {
        // Prefer high quality voices in order of naturalness
        const preferred = [
          "Samantha",     // macOS — natural female
          "Karen",        // macOS — natural Australian
          "Daniel",       // macOS — natural British
          "Google UK English Female",
          "Google US English",
          "Microsoft Zira",
          "Microsoft Jenny",
        ];
        let best: SpeechSynthesisVoice | undefined;
        for (const name of preferred) {
          best = voices.find((v) => v.name.includes(name));
          if (best) break;
        }
        // Fallback: pick first English voice that isn't a compact/low quality variant
        if (!best) {
          best = voices.find(
            (v) => v.lang.startsWith("en") && !v.name.toLowerCase().includes("compact")
          );
        }
        if (best) utterance.voice = best;
      }

      utterance.rate = 0.92;
      utterance.pitch = 1.05;
      utterance.onend = () => {
        updateState(STATES.LISTENING);
        startRecording().catch(() => updateState(STATES.IDLE));
      };
      utterance.onerror = () => updateState(STATES.IDLE);
      speechSynthesis.speak(utterance);
    },
    [updateState]
  );


  // Auto-greet on onboarding — only after user taps (activated)
  useEffect(() => {
    if (!isOnboarding || !backendConnected || !activated || greetedRef.current) return;
    greetedRef.current = true;

    (async () => {
      let pid = patientId;
      if (!pid) {
        try {
          pid = await startNewPatient();
        } catch {
          return;
        }
      }
      try {
        updateState(STATES.THINKING);
        const res = await sendOnboardingChat(pid);
        setOnboardingProgress(res.progress);
        addIrisResponse({ role: "iris", content: res.response_text });

        // Stay in THINKING until audio is ready, then switch to SPEAKING
        const transitionToListening = () => {
          updateState(STATES.LISTENING);
          startRecording().catch(() => updateState(STATES.IDLE));
        };

        fetchTTS(res.response_text)
          .then((ttsRes) => {
            if (ttsRes.audio) {
              updateState(STATES.SPEAKING);
              return playTTSAudio(ttsRes.audio, audioRef);
            }
            updateState(STATES.SPEAKING);
            speakWithBrowser(res.response_text);
            // speakWithBrowser handles its own onend -> LISTENING transition
            return;
          })
          .then(() => {
            // Only auto-transition if playTTSAudio was used (speakWithBrowser handles its own)
            if (stateRef.current === STATES.SPEAKING) {
              transitionToListening();
            }
          })
          .catch(() => {
            updateState(STATES.SPEAKING);
            speakWithBrowser(res.response_text);
          });
      } catch {
        updateState(STATES.IDLE);
      }
    })();
  }, [isOnboarding, backendConnected, activated, patientId, startNewPatient, addIrisResponse, updateState, speakWithBrowser, setOnboardingProgress, startRecording]);

  // Reset greeted/activated refs when onboarding ends
  useEffect(() => {
    if (!isOnboarding) {
      greetedRef.current = false;
      activatedRef.current = false;
      setActivated(false);
    }
  }, [isOnboarding]);

  // ── Live mode tap: toggle session ──
  const handleLiveTap = useCallback(async () => {
    if (!backendConnected) {
      showError("Backend is offline. Start the server and try again.");
      return;
    }
    let pid = patientId;
    if (!pid) {
      try {
        pid = await startNewPatient();
      } catch {
        showError("Could not create patient. Try again.");
        return;
      }
    }
    if (liveStatus === "disconnected" || liveStatus === "idle") {
      liveConnect(pid);
    } else {
      liveDisconnect();
    }
  }, [liveStatus, liveConnect, liveDisconnect, patientId, startNewPatient, showError, backendConnected]);

  // ── Fallback mode tap: existing record/stop/send flow ──
  const handleFallbackTap = useCallback(async () => {
    if (!backendConnected) {
      showError("Backend is offline. Start the server and try again.");
      return;
    }

    const s = stateRef.current;

    if (s === STATES.IDLE) {
      // Activation gate: first tap activates, triggers onboarding greeting
      if (!activatedRef.current) {
        activatedRef.current = true;
        setActivated(true);
        // If onboarding, the useEffect will fire the greeting
        if (isOnboarding) return;
      }
      // If no patient selected, create one first
      if (!patientId) {
        try {
          await startNewPatient();
        } catch {
          showError("Could not create patient. Try again.");
          return;
        }
      }
      updateState(STATES.LISTENING);
      try {
        await startRecording();
      } catch {
        showError("Microphone access needed");
        updateState(STATES.IDLE);
      }
    } else if (s === STATES.LISTENING) {
      updateState(STATES.THINKING);
      const audioData = await stopRecording();
      if (audioData) {
        try {
          // Send audio to /chat for transcription
          const response = await sendChat({
            patient_id: patientId,
            audio_data: audioData.base64,
            audio_mime_type: audioData.mimeType,
            conversation_history: conversations.map((t) => ({ role: t.role, content: t.content })),
          });

          // If onboarding, use transcript and route to onboarding endpoint
          if (isOnboarding && response.transcript) {
            addPatientMessage(response.transcript);
            const history = conversations.map((t) => ({ role: t.role, content: t.content }));
            history.push({ role: "patient", content: response.transcript });
            const obRes = await sendOnboardingChat(patientId, response.transcript, history);
            setOnboardingProgress(obRes.progress);
            addIrisResponse({ role: "iris", content: obRes.response_text });

            if (obRes.complete) {
              await completeOnboarding();
            }

            // Stay in THINKING until audio ready
            fetchTTS(obRes.response_text)
              .then((ttsRes) => {
                if (ttsRes.audio) {
                  updateState(STATES.SPEAKING);
                  return playTTSAudio(ttsRes.audio, audioRef);
                }
                updateState(STATES.SPEAKING);
                speakWithBrowser(obRes.response_text);
              })
              .then(() => {
                if (stateRef.current === STATES.SPEAKING) {
                  updateState(STATES.LISTENING);
                  startRecording().catch(() => updateState(STATES.IDLE));
                }
              })
              .catch(() => {
                updateState(STATES.SPEAKING);
                speakWithBrowser(obRes.response_text);
              });
          } else {
            // Normal clinical pipeline
            if (response.transcript) {
              addPatientMessage(response.transcript);
            }
            if (response.action_packets) setPackets(response.action_packets);
            addIrisResponse({ role: "iris", content: response.response_text });
            onResponse?.(response);

            // Stay in THINKING until audio ready
            fetchTTS(response.response_text)
              .then((res) => {
                if (res.audio) {
                  updateState(STATES.SPEAKING);
                  return playTTSAudio(res.audio, audioRef);
                }
                updateState(STATES.SPEAKING);
                speakWithBrowser(response.response_text);
              })
              .then(() => {
                if (stateRef.current === STATES.SPEAKING) {
                  updateState(STATES.LISTENING);
                  startRecording().catch(() => updateState(STATES.IDLE));
                }
              })
              .catch(() => {
                updateState(STATES.SPEAKING);
                speakWithBrowser(response.response_text);
              });
          }
        } catch {
          showError("Could not connect. Try again.");
          updateState(STATES.IDLE);
        }
      } else {
        updateState(STATES.IDLE);
      }
    } else if (s === STATES.SPEAKING) {
      // Interrupt TTS and transition to listening (consistent with barge-in)
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      speechSynthesis.cancel();
      updateState(STATES.LISTENING);
      startRecording().catch(() => updateState(STATES.IDLE));
    }
  }, [
    updateState,
    startRecording,
    stopRecording,
    patientId,
    conversations,
    onResponse,
    speakWithBrowser,
    showError,
    addPatientMessage,
    addIrisResponse,
    setPackets,
    startNewPatient,
    backendConnected,
    isOnboarding,
    setOnboardingProgress,
    completeOnboarding,
  ]);

  const handleTap = isLiveMode ? handleLiveTap : handleFallbackTap;

  // Send text message (called from PatientView text input) — uses SSE streaming
  const sendTextMessage = useCallback(
    async (message: string) => {
      let pid = patientId;
      if (!pid) {
        try {
          pid = await startNewPatient();
        } catch {
          showError("Could not create patient. Try again.");
          return;
        }
      }
      addPatientMessage(message);
      updateState(STATES.THINKING);

      // Route through onboarding if active
      if (isOnboarding) {
        try {
          const history = conversations.map((t) => ({ role: t.role, content: t.content }));
          // Include the message we just added
          history.push({ role: "patient", content: message });
          const res = await sendOnboardingChat(pid, message, history);
          setOnboardingProgress(res.progress);
          addIrisResponse({ role: "iris", content: res.response_text });

          if (res.complete) {
            await completeOnboarding();
          }

          // Stay in THINKING until audio ready
          fetchTTS(res.response_text)
            .then((ttsRes) => {
              if (ttsRes.audio) {
                updateState(STATES.SPEAKING);
                return playTTSAudio(ttsRes.audio, audioRef);
              }
              updateState(STATES.SPEAKING);
              speakWithBrowser(res.response_text);
            })
            .then(() => {
              if (stateRef.current === STATES.SPEAKING) {
                updateState(STATES.LISTENING);
                startRecording().catch(() => updateState(STATES.IDLE));
              }
            })
            .catch(() => {
              updateState(STATES.SPEAKING);
              speakWithBrowser(res.response_text);
            });
        } catch {
          showError("Could not connect. Try again.");
          updateState(STATES.IDLE);
        }
        return;
      }

      setStreamingText("");
      try {
        const fullText = await sendChatStream(
          {
            patient_id: pid,
            message,
            conversation_history: conversations.map((t) => ({ role: t.role, content: t.content })),
          },
          (evt: StreamEvent) => {
            if (evt.event === "packets") {
              const pkts = evt.data.action_packets as import("../../api/types").ActionPacket[];
              if (pkts) setPackets(pkts);
            } else if (evt.event === "chunk") {
              setStreamingText((prev) => prev + ((evt.data.text as string) || ""));
            } else if (evt.event === "replace") {
              setStreamingText((evt.data.text as string) || "");
            }
          }
        );
        // Streaming complete — finalize
        setStreamingText("");
        const responseText = fullText.trim();
        addIrisResponse({ role: "iris", content: responseText });

        // Stay in THINKING until audio ready, then SPEAKING, then LISTENING
        fetchTTS(responseText)
          .then((res) => {
            if (res.audio) {
              updateState(STATES.SPEAKING);
              return playTTSAudio(res.audio, audioRef);
            }
            updateState(STATES.SPEAKING);
            speakWithBrowser(responseText);
          })
          .then(() => {
            if (stateRef.current === STATES.SPEAKING) {
              updateState(STATES.LISTENING);
              startRecording().catch(() => updateState(STATES.IDLE));
            }
          })
          .catch(() => {
            updateState(STATES.SPEAKING);
            speakWithBrowser(responseText);
          });
      } catch {
        setStreamingText("");
        showError("Could not connect. Try again.");
        updateState(STATES.IDLE);
      }
    },
    [updateState, patientId, conversations, speakWithBrowser, showError, addPatientMessage, addIrisResponse, setPackets, startNewPatient, setStreamingText, isOnboarding, setOnboardingProgress, completeOnboarding, startRecording]
  );

  // Expose sendTextMessage via window for PatientView to call
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__irisSendText = sendTextMessage;
    return () => {
      delete (window as unknown as Record<string, unknown>).__irisSendText;
    };
  }, [sendTextMessage]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const animate = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const cx = w / 2;
      const cy = h / 2;
      const baseRadius = Math.min(w, h) * 0.25;

      ctx.clearRect(0, 0, w, h);

      const state = stateRef.current;
      const tTime = timeRef.current;
      const noise = noiseRef.current;

      // Determine colors based on state and theme
      const theme = themeRef.current;
      let r = theme.name === "dark" ? 255 : 0;
      let g = theme.name === "dark" ? 255 : 0;
      let b = theme.name === "dark" ? 255 : 0;

      if (state === STATES.LISTENING) {
        // Green
        r = 74; g = 222; b = 128;
      } else if (state === STATES.SPEAKING) {
        // Blue
        r = 96; g = 165; b = 250;
      } else if (state === STATES.THINKING) {
        // Orange
        r = 255; g = 107; b = 0;
      }

      // Slow idle breathing
      breathRef.current += 0.006;
      const breathe = Math.sin(breathRef.current) * 0.006;

      // Drift the noise seeds slowly for organic variation
      for (let i = 0; i < noise.length; i++) {
        noise[i] += 0.003 + i * 0.0004;
      }

      // Target amplitude 
      switch (state) {
        case STATES.IDLE:
          targetDeformRef.current = 2;
          break;
        case STATES.LISTENING:
          targetDeformRef.current =
            38 +
            Math.sin(tTime * 1.9) * 14 +
            Math.sin(tTime * 3.3) * 8 +
            Math.sin(tTime * 5.7) * 5;
          break;
        case STATES.THINKING:
          targetDeformRef.current =
            14 + Math.sin(tTime * 4.5) * 8 + Math.sin(tTime * 7) * 4;
          break;
        case STATES.SPEAKING:
          targetDeformRef.current =
            30 +
            Math.sin(tTime * 2.1) * 12 +
            Math.sin(tTime * 3.9) * 9 +
            Math.sin(tTime * 6.3) * 6 +
            Math.sin(tTime * 9.1) * 4;
          break;
      }

      // Smooth transition
      const ease = state === STATES.IDLE ? 0.025 : 0.09;
      deformRef.current +=
        (targetDeformRef.current - deformRef.current) * ease;
      const amp = deformRef.current;

      // Wave travel speed
      const speed =
        state === STATES.THINKING
          ? 4
          : state === STATES.SPEAKING
            ? 2.2
            : state === STATES.LISTENING
              ? 1.5
              : 0.4;

      // Layer configs
      const layers = [
        {
          ampScale: 0.25,
          freqs: [3, 7, 13],
          amps: [0.5, 0.3, 0.2],
          alpha: 0.04 * (theme.name === "light" ? 1.5 : 1),
          width: 0.8,
          speedMul: 0.6,
          phaseOff: 0,
        },
        {
          ampScale: 0.45,
          freqs: [4, 9, 14],
          amps: [0.45, 0.35, 0.2],
          alpha: 0.08 * (theme.name === "light" ? 1.5 : 1),
          width: 1,
          speedMul: 0.75,
          phaseOff: 1.8,
        },
        {
          ampScale: 0.7,
          freqs: [3, 6, 11, 17],
          amps: [0.35, 0.3, 0.2, 0.15],
          alpha: 0.15 * (theme.name === "light" ? 1.5 : 1),
          width: 1.4,
          speedMul: 0.9,
          phaseOff: 3.2,
        },
        {
          ampScale: 1.0,
          freqs: [2, 5, 9, 15, 21],
          amps: [0.25, 0.25, 0.2, 0.17, 0.13],
          alpha: 0.7 * (theme.name === "light" ? 1.2 : 1),
          width: 1.8,
          speedMul: 1.0,
          phaseOff: 0,
        },
      ];

      for (const layer of layers) {
        ctx.beginPath();

        const segments = 256;
        for (let i = 0; i <= segments; i++) {
          const angle = (i / segments) * Math.PI * 2;

          let wave = 0;
          for (let f = 0; f < layer.freqs.length; f++) {
            const freq = layer.freqs[f];
            const harmAmp = layer.amps[f];
            const phase =
              tTime * speed * layer.speedMul +
              layer.phaseOff +
              noise[f % noise.length];
            wave += Math.sin(angle * freq + phase) * harmAmp;
          }

          if (amp > 5) {
            wave +=
              Math.sin(angle * 27 + tTime * 8) * 0.06 * (amp / 50) +
              Math.sin(angle * 43 + tTime * 11) * 0.03 * (amp / 50);
          }

          const rRadius =
            baseRadius * (1 + breathe) + wave * amp * layer.ampScale;

          const x = cx + Math.cos(angle) * rRadius;
          const y = cy + Math.sin(angle) * rRadius;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }

        ctx.closePath();
        ctx.strokeStyle = `rgba(${r},${g},${b},${layer.alpha})`;
        ctx.lineWidth = layer.width;
        ctx.lineJoin = "round";
        ctx.stroke();
      }

      // Glow layer when active
      if (amp > 4) {
        ctx.save();
        ctx.filter = `blur(${Math.min(amp * 0.35, 18)}px)`;
        ctx.beginPath();
        const seg = 256;
        const gl = layers[3]; // trace the main layer
        for (let i = 0; i <= seg; i++) {
          const angle = (i / seg) * Math.PI * 2;
          let wave = 0;
          for (let f = 0; f < gl.freqs.length; f++) {
            wave +=
              Math.sin(
                angle * gl.freqs[f] +
                tTime * speed +
                noise[f % noise.length]
              ) * gl.amps[f];
          }
          const rRadius = baseRadius * (1 + breathe) + wave * amp * 0.85;
          const x = cx + Math.cos(angle) * rRadius;
          const y = cy + Math.sin(angle) * rRadius;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = `rgba(${r},${g},${b},${Math.min(amp * 0.004, 0.14)})`;
        ctx.lineWidth = 4;
        ctx.stroke();
        ctx.restore();
      }

      timeRef.current += 0.016;
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("resize", resize);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, []);


  // Click handler — immediate single tap (no delay)
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (!e.isTrusted) {
        handleTap();
        return;
      }
      handleTap();
    },
    [handleTap]
  );

  // Double-click opens clinical graph (separate from single tap)
  const handleDoubleClick = useCallback(() => {
    if (stateRef.current === STATES.IDLE && patientId) {
      setShowGraph(true);
    }
  }, [patientId]);

  // Show clinical knowledge graph on double-tap
  if (showGraph) {
    return <ClinicalGraph onClose={() => setShowGraph(false)} />;
  }

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        userSelect: "none",
        fontFamily:
          "'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Only the orb area is tappable */}
      <div
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        style={{
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          position: "relative",
        }}
      >
        <canvas
          ref={canvasRef}
          style={{
            position: "relative",
            width: orbSize,
            height: orbSize,
            filter: "drop-shadow(0 0 12px rgba(255,255,255,0.1))"
          }}
        />
        <div
          style={{
            marginTop: "40px",
            fontSize: "15px",
            fontFamily: "var(--font-serif)",
            fontStyle: "italic",
            fontWeight: 400,
            letterSpacing: "0.02em",
            color:
              currentState === STATES.IDLE
                ? t.textFaint
                : t.textMuted,
            transition: "color 0.8s ease",
            textTransform: "lowercase",
          }}
        >
          {connectingLabel
            ? connectingLabel
            : isOnboarding && currentState === STATES.IDLE
              ? "tap to introduce yourself"
              : !patientId && currentState === STATES.IDLE
                ? "tap to begin"
                : isLiveMode ? LIVE_STATE_LABELS[currentState] : STATE_LABELS[currentState]}
        </div>
        {/* Voice mode indicator */}
        <div
          style={{
            marginTop: 8,
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            fontWeight: 400,
            letterSpacing: "0.04em",
            color: t.textFaint,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: !backendConnected
                ? "#dc2626"
                : currentState === STATES.LISTENING
                  ? "#4ade80"
                  : isLiveMode
                    ? "#60a5fa"
                    : "#4ade80",
              display: "inline-block",
              opacity: !backendConnected ? 1 : 0.7,
            }}
          />
          {!backendConnected
            ? "offline"
            : currentState === STATES.LISTENING
              ? "voice recording"
              : isLiveMode
                ? "live mode"
                : "voice mode"}
        </div>
        {/* Health map hint */}
        {currentState === STATES.IDLE && patientId && (
          <div
            style={{
              marginTop: 12,
              fontSize: 10,
              fontStyle: "italic",
              fontFamily: "var(--font-serif)",
              color: t.textFaint,
              letterSpacing: "0.02em",
              opacity: 0.6,
              transition: "opacity 0.5s ease",
            }}
          >
            double tap to explore your health map
          </div>
        )}
      </div>
      {/* Error */}
      {errorMsg && (
        <div
          style={{
            marginTop: "14px",
            fontSize: "14px",
            fontWeight: 500,
            letterSpacing: "0.03em",
            color: "#f87171",
            padding: "8px 18px",
            borderRadius: 12,
            ...glassStyle(t),
            background: "rgba(220,38,38,0.12)",
            border: "1px solid rgba(220,38,38,0.25)",
          }}
        >
          {errorMsg}
        </div>
      )}
    </div>
  );
}
