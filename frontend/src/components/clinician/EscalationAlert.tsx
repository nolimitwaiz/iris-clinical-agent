/**
 * EscalationAlert — Alert bar for escalation packets.
 * Uses CSS colored dots instead of emoji for cross-browser reliability.
 */

import { useTheme } from "../../context/ThemeContext";
import type { ActionPacket } from "../../api/types";

interface Props {
  packet: ActionPacket;
}

export default function EscalationAlert({ packet }: Props) {
  const { theme: t } = useTheme();
  if (packet.decision === "no_escalation") return null;

  const isUrgent = packet.reason?.toLowerCase().includes("urgent");

  return (
    <div
      style={{
        background: t.name === "dark" ? "rgba(235,230,220,0.02)" : "rgba(26,25,23,0.015)",
        borderLeft: `4px solid ${isUrgent ? "#dc2626" : "#f59e0b"}`,
        border: `1px solid ${t.border}`,
        borderLeftWidth: 4,
        borderLeftColor: isUrgent ? "#dc2626" : "#f59e0b",
        borderRadius: 10,
        padding: 16,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 8,
        }}
      >
        <span
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: isUrgent ? "#dc2626" : "#f59e0b",
            display: "inline-block",
            flexShrink: 0,
          }}
        />
        <strong
          style={{
            color: isUrgent ? "#f87171" : "#fbbf24",
            fontSize: 14,
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          {isUrgent ? "Urgent Escalation" : "Routine Escalation"}
        </strong>
      </div>
      <div style={{ color: t.name === "dark" ? "#ddd" : "#333", fontSize: 13, lineHeight: 1.6 }}>
        {packet.reason}
      </div>
      {packet.monitoring && (
        <div
          style={{
            color: t.name === "dark" ? "#aaa" : "#666",
            fontSize: 12,
            marginTop: 8,
            fontStyle: "italic",
          }}
        >
          {packet.monitoring}
        </div>
      )}
    </div>
  );
}
