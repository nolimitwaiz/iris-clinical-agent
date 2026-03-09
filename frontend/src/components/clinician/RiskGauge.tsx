/**
 * RiskGauge — Composite decompensation risk score display.
 * Shows a large number + tier badge + component breakdown bars.
 */

import { useTheme } from "../../context/ThemeContext";
import type { RiskScore } from "../../api/types";

interface Props {
  riskScore: RiskScore | null;
}

function tierColor(tier: string): string {
  if (tier === "critical") return "#f87171";
  if (tier === "high") return "#fb923c";
  if (tier === "moderate") return "#fbbf24";
  return "#4ade80";
}

function tierBg(tier: string): string {
  if (tier === "critical") return "rgba(248,113,113,0.15)";
  if (tier === "high") return "rgba(251,146,60,0.15)";
  if (tier === "moderate") return "rgba(251,191,36,0.15)";
  return "rgba(74,222,128,0.15)";
}

const COMPONENT_LABELS: Record<string, string> = {
  weight_trend: "Weight",
  blood_pressure: "BP",
  heart_rate: "HR",
  adherence: "Adherence",
  bnp: "BNP",
};

export default function RiskGauge({ riskScore }: Props) {
  const { theme: t } = useTheme();

  const hasData = riskScore !== null;
  const composite = riskScore?.composite ?? 0;
  const tier = riskScore?.tier ?? "low";
  const color = hasData ? tierColor(tier) : "#525252";

  return (
    <div
      style={{
        background: t.bgInput,
        border: `1px solid ${t.border}`,
        borderRadius: 10,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        flex: 1,
        minWidth: 0,
      }}
    >
      {/* Large number */}
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: hasData ? color : t.textFaint,
          lineHeight: 1,
          marginTop: 8,
        }}
      >
        {hasData ? composite : "\u2014"}
      </div>

      {/* Tier badge */}
      <div
        style={{
          marginTop: 6,
          padding: "2px 10px",
          borderRadius: 10,
          background: hasData ? tierBg(tier) : "transparent",
          color: hasData ? color : t.textFaint,
          fontSize: 10,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: 0.5,
        }}
      >
        {hasData ? tier : "\u2014"}
      </div>

      {/* Label */}
      <div
        style={{
          fontSize: 11,
          color: t.textMuted,
          marginTop: 6,
          textAlign: "center",
          lineHeight: 1.3,
        }}
      >
        Decompensation Risk
      </div>

      {/* Component bars */}
      {riskScore && (
        <div style={{ width: "100%", marginTop: 10 }}>
          {Object.entries(riskScore.components).map(([key, comp]) => {
            const barColor =
              comp.score >= 70
                ? "#f87171"
                : comp.score >= 40
                  ? "#fbbf24"
                  : comp.score > 0
                    ? "#60a5fa"
                    : t.border;
            return (
              <div key={key} style={{ marginBottom: 4 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: t.textMuted,
                    marginBottom: 2,
                  }}
                >
                  <span>{COMPONENT_LABELS[key] || key}</span>
                  <span style={{ color: t.textFaint }}>{comp.detail}</span>
                </div>
                <div
                  style={{
                    height: 3,
                    borderRadius: 2,
                    background: t.border,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(comp.score, 100)}%`,
                      background: barColor,
                      borderRadius: 2,
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
