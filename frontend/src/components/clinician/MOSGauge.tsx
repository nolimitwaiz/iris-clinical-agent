/**
 * MOSGauge — Circular progress gauge showing Medication Optimization Score.
 * Centerpiece of the clinician dashboard hero metrics.
 */

import { useTheme } from "../../context/ThemeContext";
import type { MOSResponse } from "../../api/types";

interface Props {
  mos: MOSResponse | null;
}

function scoreColor(score: number): string {
  if (score < 33) return "#f87171";
  if (score < 67) return "#fbbf24";
  return "#4ade80";
}

function pillarColor(status: string): string {
  if (status === "at_target") return "#4ade80";
  if (status === "below_target") return "#60a5fa";
  if (status === "contraindicated") return "#a78bfa";
  if (status === "not_started") return "#525252";
  return "#525252";
}

export default function MOSGauge({ mos }: Props) {
  const { theme: t } = useTheme();

  const score = mos?.mos_score ?? 0;
  const hasData = mos !== null;
  const color = hasData ? scoreColor(score) : "#525252";

  // SVG circle math
  const size = 100;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = hasData ? (score / 100) * circumference : 0;

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
      {/* Ring */}
      <svg width={size} height={size} style={{ display: "block" }}>
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={t.border}
          strokeWidth={strokeWidth}
        />
        {/* Progress ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        {/* Center text */}
        <text
          x={size / 2}
          y={size / 2 + 1}
          textAnchor="middle"
          dominantBaseline="central"
          fill={hasData ? color : t.textFaint}
          fontSize={24}
          fontWeight={700}
          fontFamily="'Inter', system-ui, sans-serif"
        >
          {hasData ? `${score}%` : "\u2014"}
        </text>
      </svg>

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
        Medication Optimization
      </div>

      {/* Pillar bars */}
      {mos && (
        <div style={{ width: "100%", marginTop: 10 }}>
          {mos.pillars.map((p) => {
            const pct = p.max_score > 0 ? (p.score / p.max_score) * 100 : 0;
            return (
              <div key={p.name} style={{ marginBottom: 4 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: t.textMuted,
                    marginBottom: 2,
                  }}
                >
                  <span>{p.name}</span>
                  <span>{Math.round(pct)}%</span>
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
                      width: `${pct}%`,
                      background: pillarColor(p.status),
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
