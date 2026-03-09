/**
 * PatientView — Full-screen voice-first interface.
 * Clean, immersive. Orb is the centerpiece. Text input at bottom.
 *
 * UX overhaul: accessibility (16px text, 44px touch targets), WelcomeScreen,
 * CareSummaryCard, EducationTooltips, patient-friendly errors, onboarding
 * completion confirmation, and OnboardingForm glass overlay.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import RadialNodes from "../components/orb/RadialNodes";
import WelcomeScreen from "../components/WelcomeScreen";
import CareSummaryCard from "../components/CareSummaryCard";
import OnboardingForm from "../components/OnboardingForm";
import { AnnotatedText } from "../components/EducationTooltip";
import { useIris } from "../context/IrisContext";
import { useTheme, glassStyle } from "../context/ThemeContext";
import { useIsMobile, useIsTablet } from "../hooks/useMediaQuery";
import type { ChatResponse, EducationContent } from "../api/types";

export default function PatientView() {
  const {
    selectedPatientId,
    setSelectedPatientId,
    patients,
    patientsLoading,
    patientsError,
    retryPatients,
    isOnboarding,
    setIsOnboarding,
    onboardingProgress,
    conversations,
    setConversations,
    backendConnected,
    retryHealth,
    orbState,
    streamingText,
    packets,
    educationContent,
    patientDetail,
  } = useIris();
  const { theme: t } = useTheme();
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();

  // Responsive chat input width
  const chatMaxWidth = isMobile ? "min(480px, 100vw - 32px)" : isTablet ? "min(560px, 100vw - 40px)" : "min(480px, 100vw - 40px)";

  const [textInput, setTextInput] = useState("");
  const [imageData, setImageData] = useState<string | null>(null);
  const [imageMime, setImageMime] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [showFormOverlay, setShowFormOverlay] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [scrollScale, setScrollScale] = useState(1);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Scroll chat to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversations]);

  const handleResponse = useCallback((response: ChatResponse) => {
    void response;
  }, []);

  const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageName(file.name);
    setImageMime(file.type || "image/jpeg");
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(",")[1];
      setImageData(base64);
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  }, []);

  const handleTextSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!textInput.trim() && !imageData) return;

      const msg = textInput;
      setTextInput("");

      const imgData = imageData;
      const imgMime = imageMime;
      setImageData(null);
      setImageMime(null);
      setImageName(null);

      const sendText = (window as unknown as Record<string, unknown>).__irisSendText as
        | ((msg: string, imgData?: string, imgMime?: string) => Promise<void>)
        | undefined;
      if (sendText) {
        await sendText(msg, imgData || undefined, imgMime || undefined);
      }
    },
    [textInput, imageData, imageMime]
  );

  // Onboarding completion detection
  useEffect(() => {
    if (onboardingProgress?.complete) {
      setOnboardingComplete(true);
      const timer = setTimeout(() => setOnboardingComplete(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [onboardingProgress?.complete]);

  // Determine if we should show the welcome screen
  const showWelcome = !selectedPatientId && !isOnboarding && !showFormOverlay;

  // Get patient name for onboarding completion
  const patientName = patientDetail?.name?.split(" ")[0] || "there";

  return (
    <div className="aurora-bg" style={{ position: "relative", width: "100vw", height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* Welcome screen overlay */}
      {showWelcome && (
        <WelcomeScreen
          onStartTalking={() => {
            setIsOnboarding(true);
          }}
          onEnterInfo={() => {
            setShowFormOverlay(true);
          }}
        />
      )}

      {/* OnboardingForm glass overlay */}
      {showFormOverlay && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background: "rgba(0,0,0,0.5)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 20,
          }}
        >
          <div
            style={{
              maxWidth: 480,
              width: "90vw",
              maxHeight: "85vh",
              overflowY: "auto",
              ...glassStyle(t),
              borderRadius: 20,
              padding: 24,
            }}
          >
            <OnboardingForm
              onCreated={(patientId) => {
                setShowFormOverlay(false);
                setSelectedPatientId(patientId);
                setIsOnboarding(false);
              }}
              onCancel={() => setShowFormOverlay(false)}
            />
          </div>
        </div>
      )}

      {/* Onboarding completion confirmation */}
      {onboardingComplete && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 15,
            pointerEvents: "none",
            animation: "fadeIn 0.3s ease",
          }}
        >
          <div
            style={{
              ...glassStyle(t),
              borderRadius: 20,
              padding: "28px 36px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 22, fontWeight: 500, color: t.text, marginBottom: 8 }}>
              You're all set, {patientName}!
            </div>
            <div style={{ fontSize: 15, color: t.textMuted, lineHeight: 1.6 }}>
              You can now talk to Iris about your heart health anytime.
            </div>
          </div>
        </div>
      )}

      {/* Overlay — only the bottom section */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
        }}
      >
        {/* Patient selector — top left */}
        <div
          style={{
            position: "absolute",
            top: 44,
            left: 16,
            pointerEvents: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {patientsError && (
            <div
              style={{
                fontSize: 14,
                color: "rgba(248,113,113,0.8)",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              Something went wrong loading patients
              <button
                onClick={retryPatients}
                style={{
                  background: "none",
                  border: `1px solid rgba(248,113,113,0.3)`,
                  color: "rgba(248,113,113,0.8)",
                  borderRadius: 8,
                  padding: "4px 10px",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Retry
              </button>
            </div>
          )}
          {!patientsLoading && patients.length > 0 && !showWelcome && (
            <select
              value={isOnboarding ? "__new__" : selectedPatientId}
              onChange={(e) => {
                if (e.target.value === "__new__") {
                  setIsOnboarding(true);
                  setSelectedPatientId("");
                  setConversations([]);
                } else {
                  setIsOnboarding(false);
                  setSelectedPatientId(e.target.value);
                }
              }}
              style={{
                ...glassStyle(t),
                color: t.textMuted,
                borderRadius: 10,
                padding: "6px 12px",
                fontSize: 14,
                fontFamily: "inherit",
                outline: "none",
                cursor: "pointer",
                minWidth: 140,
              }}
            >
              {patients.map((p) => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.name} ({p.age}{p.sex})
                </option>
              ))}
              <option value="__new__">+ New Patient</option>
            </select>
          )}
        </div>

        {/* Onboarding progress dots — top right */}
        {isOnboarding && onboardingProgress && (
          <div
            style={{
              position: "absolute",
              top: 50,
              right: 20,
              display: "flex",
              gap: 6,
              pointerEvents: "none",
            }}
          >
            {Array.from({ length: onboardingProgress?.total_steps || 0 }, (_, i) => (
              <div
                key={i}
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: i < (onboardingProgress?.current_step || 0)
                    ? t.accent
                    : t.name === "dark"
                      ? "rgba(255,255,255,0.12)"
                      : "rgba(26,26,26,0.1)",
                  transition: "background 0.3s ease",
                }}
              />
            ))}
          </div>
        )}

        {/* Main Interactive Flex Column */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", width: "100%", height: "100%", position: "absolute", top: 0, left: 0, pointerEvents: "none", zIndex: 10 }}>

          {/* Top: Chat history area (stretches up to a max limit) */}
          <div style={{
            flex: (conversations.length > 0 || orbState === "thinking") ? "0 1 35vh" : "0 0 max(60px, env(safe-area-inset-top))",
            width: "100%",
            display: "flex",
            justifyContent: "center",
            pointerEvents: "none",
            overflow: "hidden",
            minHeight: 0,
            transition: "flex 0.6s cubic-bezier(0.16, 1, 0.3, 1)"
          }}>
            {(conversations.length > 0 || orbState === "thinking") && (
              <div
                onClick={(e) => e.stopPropagation()}
                onScroll={(e) => {
                  const target = e.target as HTMLDivElement;
                  // If scrolled from bottom, shrink orb up to 15%
                  const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
                  // e.g., if scrolled 200px up from bottom, we get 0.85
                  const shrinkFactor = Math.max(0.85, 1 - (distanceFromBottom / 1200));
                  setScrollScale(shrinkFactor);
                }}
                style={{
                  width: "100%",
                  height: "100%",
                  maxWidth: chatMaxWidth,
                  overflowY: "auto",
                  padding: "max(40px, env(safe-area-inset-top)) 20px 16px 20px",
                  pointerEvents: "auto",
                  maskImage: "linear-gradient(to bottom, transparent 0%, black 10%, black 90%, transparent 100%)",
                  WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 10%, black 90%, transparent 100%)",
                }}
              >
                {conversations.map((turn, i) => (
                  <div
                    key={i}
                    className="chat-bubble-enter"
                    style={{
                      display: "flex",
                      justifyContent: turn.role === "patient" ? "flex-end" : "flex-start",
                      marginBottom: 16,
                      animationDelay: `${Math.min((conversations.length - i) * 30, 200)}ms`,
                    }}
                  >
                    <div
                      className={turn.role === "iris" ? "glass-panel" : ""}
                      style={{
                        maxWidth: "85%",
                        padding: "16px 20px",
                        borderRadius: turn.role === "patient" ? "24px 24px 6px 24px" : "24px 24px 24px 6px",
                        background: turn.role === "patient" ? t.accent : "transparent",
                        color: turn.role === "patient" ? "#fff" : t.textMuted,
                        fontSize: 16,
                        lineHeight: 1.6,
                        letterSpacing: "0.01em",
                        boxShadow: turn.role === "patient" ? "0 8px 24px rgba(255,107,0,0.25)" : "none",
                      }}
                    >
                      {turn.role === "iris" ? (
                        <AnnotatedText
                          text={turn.content}
                          education={educationContent as EducationContent | null}
                        />
                      ) : (
                        <span style={{ fontWeight: 500 }}>{turn.content}</span>
                      )}
                    </div>
                  </div>
                ))}
                {orbState === "thinking" && (
                  <div className="chat-bubble-enter" style={{ display: "flex", justifyContent: "flex-start", marginBottom: 16 }}>
                    <div
                      className="glass-panel"
                      style={{
                        padding: "16px 20px",
                        borderRadius: "24px 24px 24px 6px",
                        color: t.textMuted,
                        fontSize: 16,
                        lineHeight: 1.6,
                        minWidth: 120,
                      }}
                    >
                      {streamingText ? (
                        <span>{streamingText}</span>
                      ) : (
                        <>
                          <div className="shimmer-bar" style={{ width: "100%", marginTop: 4, marginBottom: 4 }} />
                          <div style={{ fontSize: 13, color: t.textFaint, marginTop: 4 }}>Iris is thinking...</div>
                        </>
                      )}
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} style={{ height: 40 }} />
              </div>
            )}
          </div>

          {/* Middle: Orb area (takes remaining space naturally) */}
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", position: "relative", minHeight: 120, overflow: "hidden", pointerEvents: "auto" }}>
            <div style={{
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
              transform: `scale(${scrollScale}) translateY(${-(1 - scrollScale) * 100}px)`,
              transition: "transform 0.15s ease-out",
              willChange: "transform"
            }}>
              <RadialNodes
                patientId={selectedPatientId}
                conversations={conversations}
                onResponse={handleResponse}
              />
            </div>
          </div>

          {/* Disconnect banner — inline if disconnected */}
          {!backendConnected && (
            <div style={{ flexShrink: 0, paddingBottom: 12, display: "flex", justifyContent: "center", pointerEvents: "auto" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 18px",
                  borderRadius: 16,
                  ...glassStyle(t),
                  background: "rgba(220,38,38,0.12)",
                  border: "1px solid rgba(220,38,38,0.2)",
                  fontSize: 14,
                  color: "rgba(248,113,113,0.9)",
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#dc2626", flexShrink: 0 }} />
                Iris is having trouble connecting
                <button
                  onClick={retryHealth}
                  style={{
                    background: "rgba(220,38,38,0.1)",
                    border: "1px solid rgba(220,38,38,0.2)",
                    color: "rgba(248,113,113,0.8)",
                    borderRadius: 10,
                    padding: "4px 12px",
                    fontSize: 13,
                    cursor: "pointer",
                    marginLeft: 4,
                  }}
                >
                  Tap retry
                </button>
              </div>
            </div>
          )}

          {/* Bottom: Text input and Care summary container */}
          <div style={{
            flexShrink: 0,
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            paddingBottom: isMobile ? "max(80px, calc(60px + env(safe-area-inset-bottom)))" : "max(20px, env(safe-area-inset-bottom))",
            pointerEvents: "auto"
          }}>


            {/* Care summary card — shows after Iris responds with actionable packets */}
            {packets.length > 0 && orbState !== "thinking" && conversations.length > 0 && conversations[conversations.length - 1]?.role === "iris" && (
              <div style={{ width: "100%", maxWidth: chatMaxWidth }}>
                <CareSummaryCard packets={packets} />
              </div>
            )}

            {/* Image attachment chip */}
            {imageData && (
              <div style={{ maxWidth: chatMaxWidth, padding: "0 20px 6px", width: "100%" }}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    background: t.name === "dark" ? "rgba(255,255,255,0.07)" : "rgba(26,26,26,0.05)",
                    borderRadius: 20,
                    padding: "5px 12px",
                    fontSize: 11,
                    color: t.textMuted,
                  }}
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                  {imageName}
                  <button
                    type="button"
                    onClick={() => { setImageData(null); setImageMime(null); setImageName(null); }}
                    style={{ background: "none", border: "none", color: t.textMuted, cursor: "pointer", padding: 0, fontSize: 13, lineHeight: 1, opacity: 0.5 }}
                  >
                    x
                  </button>
                </div>
              </div>
            )}

            {/* Text input */}
            <form
              onSubmit={handleTextSubmit}
              style={{ width: "100%", maxWidth: chatMaxWidth, padding: "0 20px", marginBottom: "24px" }}
            >
              <input
                ref={imageInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleImageSelect}
                style={{ display: "none" }}
              />
              <div
                className="glass-panel"
                style={{
                  display: "flex",
                  alignItems: "center",
                  borderRadius: 40,
                  padding: "8px 10px 8px 24px",
                  transition: "border-color 0.3s ease, box-shadow 0.3s ease",
                }}
              >
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Message Iris..."
                  style={{
                    flex: 1,
                    background: "transparent",
                    color: t.name === "dark" ? "rgba(255,255,255,0.85)" : "rgba(26,26,26,0.85)",
                    border: "none",
                    padding: "10px 0",
                    fontSize: 15,
                    outline: "none",
                    fontFamily: "inherit",
                    letterSpacing: "0.01em",
                  }}
                />
                {/* Attachment — subtle */}
                <button
                  type="button"
                  onClick={() => imageInputRef.current?.click()}
                  style={{
                    background: "transparent",
                    border: "none",
                    padding: 6,
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    opacity: imageData ? 0.8 : 0.25,
                    transition: "opacity 0.2s ease",
                    flexShrink: 0,
                  }}
                  title="Attach image"
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke={t.name === "dark" ? "#fff" : "#1A1A1A"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>
                {/* Send — 44px touch target */}
                <button
                  type="submit"
                  disabled={!textInput.trim() && !imageData}
                  style={{
                    background: (textInput.trim() || imageData)
                      ? t.accent
                      : "transparent",
                    color: (textInput.trim() || imageData) ? "#fff" : (t.name === "dark" ? "#fff" : "#1A1A1A"),
                    border: "none",
                    borderRadius: "50%",
                    width: 44,
                    height: 44,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: (textInput.trim() || imageData) ? "pointer" : "default",
                    opacity: (textInput.trim() || imageData) ? 0.9 : 0.15,
                    transition: "all 0.3s ease",
                    transform: (textInput.trim() || imageData) ? "scale(1)" : "scale(0.9)",
                    animation: (textInput.trim() || imageData) ? "pulseGlow 2s ease-in-out infinite" : "none",
                    flexShrink: 0,
                  }}
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5" />
                    <polyline points="5 12 12 5 19 12" />
                  </svg>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
