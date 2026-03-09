/**
 * ActionPacketCard — Color-coded display of a single Action Packet.
 *
 * Colors follow transparency_panel.py:
 *   green  = safe, feasible, adherent, no_escalation, low, maintain, no_change
 *   yellow = moderate, barrier_identified, non_adherent, hold
 *   red    = blocked, escalate, critical, high, stop
 *   blue   = increase, start
 */

import { useTheme } from "../../context/ThemeContext";
import type { ActionPacket } from "../../api/types";

interface Props {
  packet: ActionPacket;
  defaultOpen?: boolean;
}

const GREEN_DECISIONS = new Set([
  "safe", "feasible", "adherent", "no_escalation", "low", "maintain", "no_change",
]);
const YELLOW_DECISIONS = new Set([
  "moderate", "barrier_identified", "non_adherent", "hold",
]);
const RED_DECISIONS = new Set([
  "blocked", "escalate", "critical", "high", "stop",
]);
const BLUE_DECISIONS = new Set(["increase", "start"]);

function getColor(decision: string): { bg: string; border: string; text: string } {
  if (GREEN_DECISIONS.has(decision))
    return { bg: "rgba(50,200,100,0.08)", border: "rgba(50,200,100,0.3)", text: "#4ade80" };
  if (YELLOW_DECISIONS.has(decision))
    return { bg: "rgba(250,200,50,0.08)", border: "rgba(250,200,50,0.3)", text: "#fbbf24" };
  if (RED_DECISIONS.has(decision))
    return { bg: "rgba(240,60,60,0.08)", border: "rgba(240,60,60,0.3)", text: "#f87171" };
  if (BLUE_DECISIONS.has(decision))
    return { bg: "rgba(60,130,255,0.08)", border: "rgba(60,130,255,0.3)", text: "#60a5fa" };
  return { bg: "rgba(128,128,128,0.08)", border: "rgba(128,128,128,0.3)", text: "#9ca3af" };
}

function confidenceIcon(confidence: string): string {
  switch (confidence) {
    case "high": return "\u25CF\u25CF\u25CF";
    case "moderate": return "\u25CF\u25CF\u25CB";
    case "low": return "\u25CF\u25CB\u25CB";
    default: return "\u25CB\u25CB\u25CB";
  }
}

export default function ActionPacketCard({ packet, defaultOpen = false }: Props) {
  const { theme: t } = useTheme();
  const color = getColor(packet.decision);
  const toolName = packet.tool_name.replace(/_/g, " ").toUpperCase();
  const labelColor = t.name === "dark" ? "#bbb" : "#666";
  const valueColor = t.name === "dark" ? "#ddd" : "#333";

  // Show dose for "start" decisions where current_dose is null but new_dose exists
  const showDose =
    (packet.current_dose_mg != null && packet.new_dose_mg != null) ||
    (packet.current_dose_mg == null && packet.new_dose_mg != null);

  return (
    <details
      open={defaultOpen}
      style={{
        background: t.name === "dark" ? "rgba(235,230,220,0.02)" : "rgba(26,25,23,0.015)",
        borderLeft: `4px solid ${color.text}`,
        border: `1px solid ${t.border}`,
        borderLeftWidth: 4,
        borderLeftColor: color.text,
        borderRadius: 8,
        marginBottom: 8,
        overflow: "hidden",
      }}
    >
      <summary
        style={{
          padding: "10px 14px",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: 13,
          fontWeight: 600,
          color: color.text,
        }}
      >
        <span style={{ fontFamily: "var(--font-serif)" }}>
          {toolName}: {packet.decision.toUpperCase()}
          {packet.drug ? ` (${packet.drug})` : ""}
        </span>
        <span style={{ fontSize: 11, opacity: 0.7 }}>
          {confidenceIcon(packet.confidence)}
        </span>
      </summary>
      <div style={{ padding: "8px 14px 14px", fontSize: 12, lineHeight: 1.7 }}>
        {packet.drug && (
          <div>
            <strong style={{ color: labelColor }}>Drug:</strong>{" "}
            <span style={{ color: valueColor }}>{packet.drug}</span>
          </div>
        )}
        {showDose && (
          <div>
            <strong style={{ color: labelColor }}>Dose:</strong>{" "}
            <span style={{ color: valueColor }}>
              {packet.current_dose_mg != null
                ? `${packet.current_dose_mg}mg \u2192 ${packet.new_dose_mg}mg`
                : `Start at ${packet.new_dose_mg}mg`}
            </span>
          </div>
        )}
        <div>
          <strong style={{ color: labelColor }}>Reason:</strong>{" "}
          <span style={{ color: valueColor }}>{packet.reason}</span>
        </div>
        <div>
          <strong style={{ color: labelColor }}>Guideline:</strong>{" "}
          <span style={{ color: valueColor }}>{packet.guideline}</span>
        </div>
        {packet.monitoring && (
          <div>
            <strong style={{ color: labelColor }}>Monitoring:</strong>{" "}
            <span style={{ color: valueColor }}>{packet.monitoring}</span>
          </div>
        )}
        <div>
          <strong style={{ color: labelColor }}>Risk if no action:</strong>{" "}
          <span style={{ color: valueColor }}>{packet.risk_of_inaction}</span>
        </div>
        {packet.data_quality && (
          <div style={{ color: "#fbbf24", marginTop: 4 }}>
            Warning: Data quality: {packet.data_quality}
          </div>
        )}
      </div>
    </details>
  );
}
