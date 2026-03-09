/**
 * GDMTCard — Shows the 4 GDMT pillars with visual progress bars
 * and active recommendations from GDMT packets.
 */

import { useTheme } from "../../context/ThemeContext";
import type { MOSResponse, ActionPacket } from "../../api/types";

interface Props {
  mos: MOSResponse | null;
  packets: ActionPacket[];
}

function statusColor(status: string): string {
  if (status === "at_target") return "#4ade80";
  if (status === "below_target") return "#60a5fa";
  if (status === "contraindicated") return "#a78bfa";
  if (status === "not_started") return "#525252";
  return "#525252";
}

export default function GDMTCard({ mos, packets }: Props) {
  const { theme: t } = useTheme();

  if (!mos) return null;

  // Find GDMT packets with active recommendations
  const gdmtPackets = packets.filter(
    (p) =>
      p.tool_name === "gdmt_engine" &&
      p.decision !== "maintain" &&
      p.decision !== "no_change"
  );

  // Map pillar names to their recommendation
  const pillarRecs: Record<string, ActionPacket | undefined> = {};
  for (const pkt of gdmtPackets) {
    const drug = pkt.drug?.toLowerCase() || "";
    if (
      drug.includes("carvedilol") ||
      drug.includes("metoprolol")
    ) {
      pillarRecs["Beta Blocker"] = pkt;
    } else if (
      drug.includes("sacubitril") ||
      drug.includes("lisinopril") ||
      drug.includes("enalapril") ||
      drug.includes("ramipril") ||
      drug.includes("losartan") ||
      drug.includes("valsartan")
    ) {
      pillarRecs["ARNI/ACEi/ARB"] = pkt;
    } else if (
      drug.includes("spironolactone") ||
      drug.includes("eplerenone")
    ) {
      pillarRecs["MRA"] = pkt;
    } else if (
      drug.includes("dapagliflozin") ||
      drug.includes("empagliflozin")
    ) {
      pillarRecs["SGLT2i"] = pkt;
    }
  }

  return (
    <div
      style={{
        background: t.bgInput,
        border: `1px solid ${t.border}`,
        borderRadius: 10,
        padding: 12,
        marginBottom: 12,
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-serif)",
          fontStyle: "italic",
          fontSize: 14,
          color: t.text,
          marginBottom: 10,
        }}
      >
        GDMT Optimization
      </div>

      {mos.pillars.map((p) => {
        const pct =
          p.max_score > 0 ? Math.round((p.score / p.max_score) * 100) : 0;
        const rec = pillarRecs[p.name];
        const barBg = statusColor(p.status);
        const doseText =
          p.current_dose_mg !== null && p.target_dose_mg !== null
            ? `${p.current_dose_mg} / ${p.target_dose_mg} mg`
            : p.status === "contraindicated"
              ? "Contraindicated"
              : "\u2014 / \u2014 mg";

        return (
          <div key={p.name} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <span style={{ fontSize: 12, fontWeight: 600, color: t.text }}>
                  {p.name}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    color: t.textMuted,
                    marginLeft: 6,
                  }}
                >
                  {p.drug || "Not started"}
                </span>
              </div>
              <span style={{ fontSize: 11, color: t.textMuted }}>{doseText}</span>
            </div>

            {/* Progress bar */}
            <div
              style={{
                height: 5,
                borderRadius: 3,
                background: t.border,
                overflow: "hidden",
                marginTop: 4,
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${pct}%`,
                  background: barBg,
                  borderRadius: 3,
                  transition: "width 0.4s ease",
                }}
              />
            </div>

            {/* Recommendation badge */}
            {rec && (
              <div
                style={{
                  marginTop: 4,
                  display: "inline-block",
                  fontSize: 10,
                  padding: "2px 8px",
                  borderRadius: 4,
                  background: "rgba(96,165,250,0.12)",
                  border: "1px solid rgba(96,165,250,0.3)",
                  color: "#60a5fa",
                }}
              >
                {rec.decision === "start"
                  ? `Start ${rec.drug} ${rec.new_dose_mg}mg`
                  : rec.decision === "increase"
                    ? `Uptitrate to ${rec.new_dose_mg}mg`
                    : rec.decision === "hold"
                      ? `Hold ${rec.drug || ""}`
                      : rec.decision === "stop"
                        ? `Stop ${rec.drug || ""}`
                        : `${rec.decision} ${rec.drug || ""}`}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
