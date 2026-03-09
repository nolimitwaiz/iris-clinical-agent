/**
 * CareSummaryCard — Patient-friendly summary of what Iris recommended.
 * Sourced from Action Packets. Auto-collapses after 10 seconds.
 */

import { useState, useEffect, useRef } from "react";
import { useTheme, glassStyle } from "../context/ThemeContext";
import type { ActionPacket } from "../api/types";

const NO_ACTION_DECISIONS = new Set([
  "no_change", "maintain", "adherent", "no_escalation",
  "safe", "feasible", "low", "stable",
]);

/** Map tool decisions to patient-friendly language */
function describeAction(packet: ActionPacket): string | null {
  if (NO_ACTION_DECISIONS.has(packet.decision)) return null;

  const drug = packet.drug;
  const decision = packet.decision;

  if (drug) {
    switch (decision) {
      case "increase":
        return `Your care team may increase your ${drug} dose`;
      case "start":
        return `Your care team may start you on ${drug}`;
      case "decrease":
        return `Your care team may lower your ${drug} dose`;
      case "hold":
        return `Your ${drug} may be paused temporarily`;
      case "stop":
        return `Your care team may stop ${drug}`;
      default:
        return `Update regarding your ${drug}`;
    }
  }

  if (decision === "escalate") {
    return "Your care team will be notified about your results";
  }

  if (packet.reason && packet.reason.length < 100) {
    return packet.reason;
  }

  return null;
}

interface Props {
  packets: ActionPacket[];
}

export default function CareSummaryCard({ packets }: Props) {
  const { theme: t } = useTheme();
  const [visible, setVisible] = useState(true);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Auto-collapse after 10 seconds
  useEffect(() => {
    setVisible(true);
    timerRef.current = setTimeout(() => setVisible(false), 10000);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [packets]);

  const actions = packets
    .map(describeAction)
    .filter((a): a is string => a !== null);

  if (actions.length === 0 || !visible) return null;

  return (
    <div
      onClick={() => setVisible(false)}
      style={{
        width: "100%",
        padding: "0 20px",
        marginBottom: 8,
        cursor: "pointer",
        animation: "fadeIn 0.3s ease",
      }}
    >
      <div
        style={{
          ...glassStyle(t),
          borderRadius: 14,
          padding: "12px 16px",
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 500,
            color: t.textFaint,
            letterSpacing: "0.04em",
            marginBottom: 8,
            textTransform: "uppercase",
          }}
        >
          Here's what we discussed
        </div>
        <ul
          style={{
            margin: 0,
            paddingLeft: 18,
            listStyleType: "disc",
          }}
        >
          {actions.map((action, i) => (
            <li
              key={i}
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: t.textMuted,
                marginBottom: 4,
              }}
            >
              {action}
            </li>
          ))}
        </ul>
        {packets.some((p) => p.monitoring) && (
          <div
            style={{
              fontSize: 13,
              color: t.accent,
              marginTop: 8,
              fontStyle: "italic",
            }}
          >
            Follow up labs or monitoring may be needed
          </div>
        )}
      </div>
    </div>
  );
}
