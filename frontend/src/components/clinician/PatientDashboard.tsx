/**
 * PatientDashboard — Patient demographics, meds, labs, vitals.
 * Replicates patient_dashboard.py logic for the clinician view.
 * Theme-aware.
 */

import { useTheme, glassStyle } from "../../context/ThemeContext";
import MetricTooltip from "./MetricTooltip";
import MOSGauge from "./MOSGauge";
import RiskGauge from "./RiskGauge";
import type { PatientDetail, MOSResponse, RiskScore } from "../../api/types";

interface Props {
  patient: PatientDetail | null;
  mos?: MOSResponse | null;
  riskScore?: RiskScore | null;
}

function getLatestLab(
  patient: PatientDetail,
  labName: string
): { value: number; date: string } | null {
  const values = patient.labs?.[labName];
  if (!values || values.length === 0) return null;
  return values[values.length - 1];
}

function riskColor(ef: number, nyha: number): string {
  if (nyha >= 4 || ef <= 0.2) return "#f87171";
  if (nyha >= 3 || ef <= 0.3) return "#fbbf24";
  return "#4ade80";
}

export default function PatientDashboard({ patient, mos, riskScore }: Props) {
  const { theme: t } = useTheme();

  if (!patient) {
    return (
      <div style={{ color: t.textFaint, padding: 20, textAlign: "center" }}>
        Select a patient to view dashboard
      </div>
    );
  }

  const ef = patient.ejection_fraction;
  const rc = riskColor(ef, patient.nyha_class);

  const labs = ["potassium", "creatinine", "egfr", "bnp", "sodium"];
  const labLabels: Record<string, string> = {
    potassium: "K+",
    creatinine: "Cr",
    egfr: "eGFR",
    bnp: "BNP",
    sodium: "Na+",
  };

  return (
    <div style={{ fontSize: 13, color: t.name === "dark" ? "#ccc" : t.text }}>
      {/* Hero Metrics: MOS + Risk */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <MOSGauge mos={mos ?? null} />
        <RiskGauge riskScore={riskScore ?? null} />
      </div>

      {/* Demographics */}
      <div style={{ marginBottom: 20 }}>
        <h3 style={{ color: t.text, margin: "0 0 8px", fontSize: 16 }}>
          {patient.name}
        </h3>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <span>
            {patient.age}y {patient.sex}
          </span>
          <MetricTooltip metricKey="ejection_fraction">
            <span style={{ color: rc }}>
              EF {Math.round(ef * 100)}%
            </span>
          </MetricTooltip>
          <MetricTooltip metricKey="nyha_class">
            <span>NYHA {patient.nyha_class}</span>
          </MetricTooltip>
        </div>
      </div>

      {/* Medications */}
      <div style={{ marginBottom: 20 }}>
        <h4 style={{ color: t.textMuted, margin: "0 0 8px", fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>
          Current Medications
        </h4>
        {patient.medications.length === 0 ? (
          <div style={{ color: t.textFaint, fontSize: 12, fontStyle: "italic", padding: "8px 0" }}>
            No medications on record
          </div>
        ) : (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 12,
            }}
          >
            <thead>
              <tr style={{ color: t.textMuted, borderBottom: `1px solid ${t.border}` }}>
                <th style={{ textAlign: "left", padding: "4px 8px" }}>Drug</th>
                <th style={{ textAlign: "right", padding: "4px 8px" }}>Dose</th>
                <th style={{ textAlign: "right", padding: "4px 8px" }}>Freq</th>
              </tr>
            </thead>
            <tbody>
              {patient.medications.map((med, i) => (
                <tr
                  key={i}
                  style={{
                    borderBottom: `1px solid ${t.borderSubtle}`,
                  }}
                >
                  <td style={{ padding: "4px 8px", color: t.name === "dark" ? "#ddd" : t.text }}>
                    {med.drug}
                  </td>
                  <td style={{ padding: "4px 8px", textAlign: "right" }}>
                    {med.dose_mg}mg
                  </td>
                  <td style={{ padding: "4px 8px", textAlign: "right" }}>
                    {med.frequency_per_day}x/day
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Latest Labs */}
      <div style={{ marginBottom: 20 }}>
        <h4 style={{ color: t.textMuted, margin: "0 0 8px", fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>
          Latest Labs
        </h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
          {labs.map((lab) => {
            const latest = getLatestLab(patient, lab);
            return (
              <MetricTooltip key={lab} metricKey={lab}>
                <div
                  style={{
                    ...glassStyle(t),
                    borderRadius: 6,
                    padding: "8px",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: 11, color: t.textMuted, marginBottom: 4 }}>
                    {labLabels[lab]}
                  </div>
                  <div style={{ fontSize: 14, color: t.text, fontWeight: 600 }}>
                    {latest ? latest.value : "\u2014"}
                  </div>
                </div>
              </MetricTooltip>
            );
          })}
        </div>
      </div>

      {/* Social Factors */}
      <div>
        <h4 style={{ color: t.textMuted, margin: "0 0 8px", fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>
          Social Factors
        </h4>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 4,
            fontSize: 12,
          }}
        >
          <span style={{ color: t.textMuted }}>Insurance:</span>
          <span>{String(patient.social_factors?.insurance_tier || "\u2014").replace(/_/g, " ")}</span>
          <span style={{ color: t.textMuted }}>Literacy:</span>
          <span>{String(patient.social_factors?.health_literacy || "\u2014")}</span>
          <span style={{ color: t.textMuted }}>Lives alone:</span>
          <span>{patient.social_factors?.lives_alone ? "Yes" : "No"}</span>
          <span style={{ color: t.textMuted }}>Pharmacy:</span>
          <span>{String(patient.social_factors?.pharmacy_distance_miles || "\u2014")} mi</span>
        </div>
      </div>
    </div>
  );
}
