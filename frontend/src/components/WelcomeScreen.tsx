/**
 * WelcomeScreen — Gateway for first-time visitors.
 * Shows when no patient is selected and not onboarding.
 * Two paths: conversational (orb) or clinical form.
 */

import { useTheme, glassStyle } from "../context/ThemeContext";
import { useIris } from "../context/IrisContext";
import { useIsMobile } from "../hooks/useMediaQuery";

interface Props {
  onStartTalking: () => void;
  onEnterInfo: () => void;
}

export default function WelcomeScreen({ onStartTalking, onEnterInfo }: Props) {
  const { theme: t } = useTheme();
  const { patients } = useIris();
  const isMobile = useIsMobile();

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 10,
        pointerEvents: "auto",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 12,
          maxWidth: isMobile ? "90vw" : 400,
        }}
      >
        {/* Heading */}
        <h1
          style={{
            fontFamily: "var(--font-serif)",
            fontStyle: "italic",
            fontWeight: 400,
            fontSize: isMobile ? 36 : 44,
            color: t.text,
            margin: 0,
            letterSpacing: "-0.01em",
          }}
        >
          Hi, I'm Iris
        </h1>

        <p
          style={{
            fontSize: 16,
            color: t.textMuted,
            margin: "0 0 24px 0",
            letterSpacing: "0.01em",
          }}
        >
          Your heart failure care companion
        </p>

        {/* Action buttons */}
        <div
          style={{
            display: "flex",
            flexDirection: isMobile ? "column" : "row",
            gap: 12,
            width: "100%",
            justifyContent: "center",
          }}
        >
          <button
            onClick={onStartTalking}
            style={{
              padding: "14px 28px",
              borderRadius: 24,
              border: "none",
              background: t.accent,
              color: "#fff",
              fontSize: 16,
              fontFamily: "inherit",
              fontWeight: 500,
              cursor: "pointer",
              letterSpacing: "0.01em",
              transition: "transform 0.2s ease, opacity 0.2s ease",
              minWidth: 160,
            }}
          >
            Start talking
          </button>

          <button
            onClick={onEnterInfo}
            style={{
              padding: "14px 28px",
              borderRadius: 24,
              ...glassStyle(t),
              color: t.textMuted,
              fontSize: 16,
              fontFamily: "inherit",
              fontWeight: 500,
              cursor: "pointer",
              letterSpacing: "0.01em",
              transition: "transform 0.2s ease, opacity 0.2s ease",
              minWidth: 160,
            }}
          >
            Enter my info
          </button>
        </div>

        {/* Existing patients */}
        {patients.length > 0 && (
          <div
            style={{
              marginTop: 32,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span
              style={{
                fontSize: 12,
                color: t.textFaint,
                letterSpacing: "0.04em",
              }}
            >
              or continue as
            </span>
            <PatientLinks />
          </div>
        )}
      </div>
    </div>
  );
}

function PatientLinks() {
  const { patients, setSelectedPatientId, setIsOnboarding, setConversations } = useIris();
  const { theme: t } = useTheme();

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
      {patients.map((p) => (
        <button
          key={p.patient_id}
          onClick={() => {
            setIsOnboarding(false);
            setSelectedPatientId(p.patient_id);
            setConversations([]);
          }}
          style={{
            background: "none",
            border: `1px solid ${t.border}`,
            borderRadius: 16,
            padding: "6px 14px",
            fontSize: 14,
            color: t.textMuted,
            cursor: "pointer",
            fontFamily: "inherit",
            transition: "border-color 0.2s ease",
          }}
        >
          {p.name}
        </button>
      ))}
    </div>
  );
}
