/**
 * ClinicianView — Dashboard + Action Packets + conversation monitor.
 * Shares state with PatientView via IrisContext.
 * Responsive: 3-col (desktop), 2-col (tablet), tabbed (mobile).
 */

import { useState, useCallback, useRef } from "react";
import { sendChat } from "../api/client";
import ActionPacketCard from "../components/clinician/ActionPacketCard";
import EscalationAlert from "../components/clinician/EscalationAlert";
import GDMTCard from "../components/clinician/GDMTCard";
import PatientDashboard from "../components/clinician/PatientDashboard";
import OnboardingForm from "../components/OnboardingForm";
import { useIris } from "../context/IrisContext";
import { useTheme, glassStyle } from "../context/ThemeContext";
import { useIsMobile, useIsTablet } from "../hooks/useMediaQuery";
import type { ChatResponse } from "../api/types";

type MobileTab = "chat" | "patient" | "clinical";

export default function ClinicianView() {
  const {
    patients,
    patientsError,
    retryPatients,
    selectedPatientId,
    setSelectedPatientId,
    patientDetail,
    patientLoading,
    patientError,
    retryPatientDetail,
    conversations,
    addPatientMessage,
    addIrisResponse,
    packets,
    setPackets,
    mos,
    setMos,
    backendConnected,
    healthChecking,
    retryHealth,
    isOnboarding,
    setIsOnboarding,
  } = useIris();
  const { theme: t } = useTheme();
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [imageData, setImageData] = useState<string | null>(null);
  const [imageMime, setImageMime] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<MobileTab>("chat");
  const imageInputRef = useRef<HTMLInputElement>(null);

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

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if ((!input.trim() && !imageData) || loading) return;

      const msg = input;
      setInput("");
      const imgData = imageData;
      const imgMime = imageMime;
      setImageData(null);
      setImageMime(null);
      setImageName(null);

      addPatientMessage(msg || (imgData ? "[Image sent]" : ""));
      setLoading(true);

      try {
        const response: ChatResponse = await sendChat({
          patient_id: selectedPatientId,
          message: msg || undefined,
          image_data: imgData || undefined,
          image_mime_type: imgMime || undefined,
          conversation_history: conversations.map((t) => ({ role: t.role, content: t.content })),
        });

        setPackets(response.action_packets);
        if (response.mos) setMos(response.mos);
        addIrisResponse({
          role: "iris",
          content: response.response_text,
          packets: response.action_packets,
          validation: response.validation,
        });
      } catch {
        addIrisResponse({
          role: "iris",
          content: "Error processing request. Check backend connection.",
        });
      } finally {
        setLoading(false);
      }
    },
    [input, selectedPatientId, loading, addPatientMessage, addIrisResponse, setPackets, setMos, imageData, imageMime]
  );

  const escalationPacket = packets.find(
    (p) => p.tool_name === "escalation_manager" && p.decision !== "no_escalation"
  );

  // Extract trajectory packet for risk score
  const trajectoryPacket = packets.find(p => p.tool_name === "trajectory_analyzer");
  const projections = trajectoryPacket?.projected_trajectories || [];

  // ── Shared sub-components ──────────────────────────────────────────────

  const connectionStatus = (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        marginBottom: 12,
        fontSize: 11,
        color: backendConnected ? "#4ade80" : "#f87171",
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: healthChecking ? "#fbbf24" : backendConnected ? "#4ade80" : "#dc2626",
          display: "inline-block",
        }}
      />
      {healthChecking ? "Connecting..." : backendConnected ? "Connected" : "Disconnected"}
      {!healthChecking && !backendConnected && (
        <button
          onClick={retryHealth}
          style={{
            background: "none",
            border: "none",
            color: "#f87171",
            fontSize: 11,
            cursor: "pointer",
            textDecoration: "underline",
            padding: 0,
          }}
        >
          Retry
        </button>
      )}
    </div>
  );

  const patientSelector = (
    <div style={{ marginBottom: 12 }}>
      {patientsError && (
        <div style={{ fontSize: 11, color: "#fbbf24", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
          {patientsError}
          <button
            onClick={retryPatients}
            style={{
              background: "none", border: "none", color: "#fbbf24",
              fontSize: 11, cursor: "pointer", textDecoration: "underline", padding: 0,
            }}
          >
            Retry
          </button>
        </div>
      )}
      <select
        value={isOnboarding ? "__new__" : selectedPatientId}
        onChange={(e) => {
          if (e.target.value === "__new__") {
            setIsOnboarding(true);
          } else {
            setIsOnboarding(false);
            setSelectedPatientId(e.target.value);
          }
        }}
        style={{
          width: "100%",
          background: t.bgInput,
          color: t.textMuted,
          border: `1px solid ${t.border}`,
          borderRadius: 6,
          padding: "8px 10px",
          fontSize: 12,
          outline: "none",
        }}
      >
        {patients.map((p) => (
          <option key={p.patient_id} value={p.patient_id}>
            {p.name} ({p.age}{p.sex})
          </option>
        ))}
        <option value="__new__">+ New Patient</option>
      </select>
    </div>
  );

  const dashboardContent = isOnboarding ? (
    <OnboardingForm
      onCreated={(newId) => {
        setIsOnboarding(false);
        retryPatients();
        setSelectedPatientId(newId);
      }}
      onCancel={() => setIsOnboarding(false)}
    />
  ) : patientLoading ? (
    <div style={{ color: t.textMuted, fontSize: 12, textAlign: "center", padding: 20 }}>
      Loading patient data...
    </div>
  ) : patientError ? (
    <div style={{ color: "#f87171", fontSize: 12, textAlign: "center", padding: 20 }}>
      {patientError}
      <br />
      <button
        onClick={retryPatientDetail}
        style={{
          background: "none", border: "none", color: "#f87171",
          fontSize: 12, cursor: "pointer", textDecoration: "underline",
          padding: 0, marginTop: 8,
        }}
      >
        Retry
      </button>
    </div>
  ) : (
    <PatientDashboard patient={patientDetail} mos={mos} riskScore={trajectoryPacket?.risk_score ?? null} />
  );

  const conversationPanel = (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div
        style={{
          padding: "12px 16px",
          borderBottom: `1px solid ${t.borderSubtle}`,
          color: t.textMuted,
          fontSize: 12,
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", textTransform: "none", letterSpacing: 0, fontSize: 15 }}>Conversation Monitor</span>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {conversations.length === 0 && (
          <div style={{ color: t.textFaint, textAlign: "center", marginTop: 40, fontSize: 13 }}>
            Send a message as the patient to start the pipeline
          </div>
        )}
        {conversations.map((turn, i) => (
          <div
            key={i}
            style={{
              marginBottom: 16,
              display: "flex",
              flexDirection: "column",
              alignItems: turn.role === "patient" ? "flex-end" : "flex-start",
            }}
          >
            <div style={{ fontSize: 10, color: t.textFaint, marginBottom: 4, textTransform: "uppercase" }}>
              {turn.role === "patient" ? "Patient" : "Iris"}
            </div>
            <div
              style={{
                background: turn.role === "patient" ? t.userMsgBg : t.bgInput,
                border: `1px solid ${turn.role === "patient" ? t.userMsgBorder : t.border}`,
                borderRadius: 10,
                padding: "10px 14px",
                fontSize: 13,
                color: t.name === "dark" ? "#ddd" : t.text,
                maxWidth: "80%",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
              }}
            >
              {turn.content}
            </div>
            {turn.validation && !turn.validation.approved && (
              <div style={{ fontSize: 11, color: "#f59e0b", marginTop: 4, maxWidth: "80%" }}>
                Warning: {turn.validation.violations.length} validation issue(s)
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ color: t.textMuted, fontSize: 13, fontStyle: "italic" }}>
            Running pipeline...
          </div>
        )}
      </div>
      <form
        onSubmit={handleSend}
        style={{ padding: 12, borderTop: `1px solid ${t.borderSubtle}` }}
      >
        {imageData && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <div
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "rgba(96,165,250,0.12)", border: "1px solid rgba(96,165,250,0.3)",
                borderRadius: 6, padding: "3px 8px", fontSize: 11, color: "#60a5fa",
              }}
            >
              {imageName}
              <button
                type="button"
                onClick={() => { setImageData(null); setImageMime(null); setImageName(null); }}
                style={{ background: "none", border: "none", color: "#60a5fa", cursor: "pointer", padding: 0, fontSize: 13 }}
              >
                x
              </button>
            </div>
          </div>
        )}
        <div style={{ display: "flex", gap: 8 }}>
          <input ref={imageInputRef} type="file" accept="image/*" capture="environment" onChange={handleImageSelect} style={{ display: "none" }} />
          <button
            type="button"
            onClick={() => imageInputRef.current?.click()}
            disabled={loading}
            style={{
              background: imageData ? "rgba(96,165,250,0.15)" : t.bgInput,
              color: imageData ? "#60a5fa" : t.textMuted,
              border: `1px solid ${imageData ? "rgba(96,165,250,0.3)" : t.border}`,
              borderRadius: 8, width: 40, display: "flex", alignItems: "center", justifyContent: "center",
              cursor: loading ? "not-allowed" : "pointer", flexShrink: 0,
            }}
            title="Attach image"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
          </button>
          <input
            type="text" value={input} onChange={(e) => setInput(e.target.value)}
            placeholder="Send message as patient..."
            style={{
              flex: 1, background: t.bgInput, color: t.text,
              border: `1px solid ${t.border}`, borderRadius: 8, padding: "10px 14px", fontSize: 13, outline: "none",
            }}
            disabled={loading}
          />
          <button
            type="submit" disabled={loading}
            style={{
              background: t.accent, color: t.text, border: "none", borderRadius: 8,
              padding: "10px 18px", fontSize: 13, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1,
            }}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );

  const clinicalPanel = (
    <div style={{ overflowY: "auto", padding: 12 }}>
      <div
        style={{
          color: t.textMuted, fontSize: 12, textTransform: "uppercase",
          letterSpacing: 1, marginBottom: 12,
        }}
      >
        <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", textTransform: "none", letterSpacing: 0, fontSize: 15 }}>Clinical Reasoning</span>
      </div>
      {escalationPacket && <EscalationAlert packet={escalationPacket} />}

      {/* GDMT Optimization card */}
      <GDMTCard mos={mos} packets={packets} />

      {/* Projected Outcomes card */}
      {projections.length > 0 && (
        <div
          style={{
            background: t.bgInput,
            border: `1px solid ${t.border}`,
            borderRadius: 10,
            padding: 12,
            marginBottom: 12,
          }}
        >
          <div style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: 14, color: t.text, marginBottom: 10 }}>
            Projected Outcomes (30 day)
          </div>
          {projections.map((proj, pi) => {
            const metricLabel = proj.metric.replace(/_/g, " ").replace("kg", "(kg)");
            const noAction = proj.projected_30d_no_action;
            const withAction = proj.projected_30d_with_action;
            const currentLast = proj.current_values[proj.current_values.length - 1];
            const isWorsening = Math.abs(noAction - currentLast) > Math.abs(withAction - currentLast);
            return (
              <div key={pi} style={{ marginBottom: pi < projections.length - 1 ? 10 : 0 }}>
                <div style={{ fontSize: 11, color: t.textMuted, marginBottom: 4, textTransform: "capitalize" }}>
                  {metricLabel}
                </div>
                <div style={{ display: "flex", gap: 16, fontSize: 12 }}>
                  <div>
                    <span style={{ color: t.textFaint, fontSize: 10 }}>Current: </span>
                    <span style={{ color: t.text, fontWeight: 500 }}>{currentLast}</span>
                  </div>
                  <div>
                    <span style={{ color: "#f87171", fontSize: 10 }}>No action: </span>
                    <span style={{ color: "#f87171", fontWeight: 500 }}>{noAction}</span>
                  </div>
                  <div>
                    <span style={{ color: "#4ade80", fontSize: 10 }}>With action: </span>
                    <span style={{ color: "#4ade80", fontWeight: 500 }}>{withAction}</span>
                  </div>
                </div>
                {/* Mini sparkline bar */}
                <div style={{ display: "flex", gap: 2, marginTop: 4, height: 3, borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ flex: 1, background: "rgba(248,113,113,0.3)" }} />
                  <div style={{ flex: isWorsening ? 0.6 : 1, background: "rgba(74,222,128,0.3)" }} />
                </div>
              </div>
            );
          })}
          <div style={{ fontSize: 10, color: t.textFaint, marginTop: 8, fontStyle: "italic" }}>
            Based on linear extrapolation from recent trends
          </div>
        </div>
      )}

      {packets.length === 0 ? (
        <div style={{ color: t.textFaint, fontSize: 12, textAlign: "center", marginTop: 20 }}>
          Action Packets will appear here after pipeline runs
        </div>
      ) : (
        packets.map((p, i) => (
          <ActionPacketCard
            key={`${p.tool_name}-${i}`}
            packet={p}
            defaultOpen={
              p.decision !== "no_change" &&
              p.decision !== "no_escalation" &&
              p.decision !== "adherent"
            }
          />
        ))
      )}
    </div>
  );

  // ── Mobile layout (tabbed) ─────────────────────────────────────────────
  if (isMobile) {
    const tabStyle = (active: boolean): React.CSSProperties => ({
      flex: 1,
      padding: "10px 0",
      background: active ? t.accent : "transparent",
      color: active ? t.text : t.textMuted,
      border: "none",
      fontSize: 12,
      fontWeight: active ? 600 : 400,
      cursor: "pointer",
      textTransform: "uppercase",
      letterSpacing: 0.5,
      fontFamily: "inherit",
    });

    return (
      <div
        style={{
          width: "100vw",
          height: "100vh",
          paddingTop: 44,
          background: t.bg,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxSizing: "border-box",
          fontFamily: "'Inter', system-ui, sans-serif",
        }}
      >
        {/* Tab bar */}
        <div style={{ display: "flex", borderBottom: `1px solid ${t.borderSubtle}` }}>
          <button style={tabStyle(mobileTab === "chat")} onClick={() => setMobileTab("chat")}>Chat</button>
          <button style={tabStyle(mobileTab === "patient")} onClick={() => setMobileTab("patient")}>Patient</button>
          <button style={tabStyle(mobileTab === "clinical")} onClick={() => setMobileTab("clinical")}>Clinical</button>
        </div>

        {/* Tab content */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, paddingBottom: 60 }}>
          {mobileTab === "chat" && conversationPanel}
          {mobileTab === "patient" && (
            <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>
              {connectionStatus}
              {patientSelector}
              {dashboardContent}
            </div>
          )}
          {mobileTab === "clinical" && clinicalPanel}
        </div>
      </div>
    );
  }

  // ── Tablet layout (2 columns) ──────────────────────────────────────────
  if (isTablet) {
    return (
      <div
        style={{
          width: "100vw",
          height: "100vh",
          paddingTop: 44,
          background: t.bg,
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: 1,
          fontFamily: "'Inter', system-ui, sans-serif",
          overflow: "hidden",
          boxSizing: "border-box",
        }}
      >
        {/* Left: dashboard */}
        <div style={{ ...glassStyle(t), padding: 12, overflowY: "auto", borderRight: `1px solid ${t.glassBorder}`, borderRadius: 0 }}>
          {connectionStatus}
          {patientSelector}
          {dashboardContent}
        </div>

        {/* Right: conversation + packets stacked */}
        <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            {conversationPanel}
          </div>
          <div
            style={{
              borderTop: `1px solid ${t.glassBorder}`,
              maxHeight: "35vh",
              overflowY: "auto",
              ...glassStyle(t),
              borderRadius: 0,
            }}
          >
            {clinicalPanel}
          </div>
        </div>
      </div>
    );
  }

  // ── Desktop layout (3 columns) ─────────────────────────────────────────
  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        paddingTop: 44,
        background: t.name === "dark" ? "#0a0a0a" : t.bg,
        display: "grid",
        gridTemplateColumns: "280px 1fr 340px",
        gap: 1,
        fontFamily: "'Inter', system-ui, sans-serif",
        overflow: "hidden",
        boxSizing: "border-box",
      }}
    >
      {/* Left panel: Patient Dashboard */}
      <div
        style={{
          ...glassStyle(t),
          borderRadius: 0,
          padding: 12,
          overflowY: "auto",
          borderRight: `1px solid ${t.glassBorder}`,
        }}
      >
        {connectionStatus}
        {patientSelector}
        {dashboardContent}
      </div>

      {/* Center: Conversation */}
      <div style={{ background: t.bg, display: "flex", flexDirection: "column" }}>
        {conversationPanel}
      </div>

      {/* Right panel: Action Packets */}
      <div
        style={{
          ...glassStyle(t),
          borderRadius: 0,
          overflowY: "auto",
          borderLeft: `1px solid ${t.glassBorder}`,
        }}
      >
        {clinicalPanel}
      </div>
    </div>
  );
}
