/**
 * OnboardingForm — Patient onboarding form with vitals, labs, and medications.
 * Collects comprehensive info to create a new patient profile.
 */

import { useState } from "react";
import { createPatient } from "../api/client";
import { useTheme } from "../context/ThemeContext";
import type { PatientCreateRequest } from "../api/types";

interface Props {
  onCreated: (patientId: string) => void;
  onCancel: () => void;
}

const INSURANCE_OPTIONS = [
  { value: "tier1_generic", label: "Generic (Tier 1)" },
  { value: "tier2_preferred", label: "Preferred (Tier 2)" },
  { value: "tier3_nonpreferred", label: "Non Preferred (Tier 3)" },
  { value: "uninsured", label: "Uninsured" },
];

const COMMON_HF_DRUGS = [
  "furosemide",
  "bumetanide",
  "torsemide",
  "carvedilol",
  "metoprolol succinate",
  "lisinopril",
  "enalapril",
  "losartan",
  "valsartan",
  "sacubitril/valsartan",
  "spironolactone",
  "eplerenone",
  "dapagliflozin",
  "empagliflozin",
  "amlodipine",
  "digoxin",
  "hydralazine",
  "isosorbide dinitrate",
  "warfarin",
  "aspirin",
  "potassium chloride",
];

interface MedicationRow {
  drug: string;
  dose_mg: string;
  frequency_per_day: string;
}

export default function OnboardingForm({ onCreated, onCancel }: Props) {
  const { theme: t } = useTheme();

  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("F");
  const [ejectionFraction, setEjectionFraction] = useState("");
  const [nyhaClass, setNyhaClass] = useState("2");
  const [weightKg, setWeightKg] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [conditions, setConditions] = useState("");
  const [allergies, setAllergies] = useState("");
  const [insurance, setInsurance] = useState("tier1_generic");

  // Vitals
  const [systolicBp, setSystolicBp] = useState("");
  const [diastolicBp, setDiastolicBp] = useState("");
  const [heartRate, setHeartRate] = useState("");

  // Labs
  const [potassium, setPotassium] = useState("");
  const [creatinine, setCreatinine] = useState("");
  const [egfr, setEgfr] = useState("");

  // Medications
  const [medications, setMedications] = useState<MedicationRow[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: t.bgInput,
    border: `1px solid ${t.border}`,
    color: t.text,
    borderRadius: 6,
    padding: "8px 10px",
    fontSize: 13,
    outline: "none",
    fontFamily: "inherit",
    boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12,
    color: t.textMuted,
    marginBottom: 4,
    display: "block",
  };

  const sectionStyle: React.CSSProperties = {
    fontFamily: "var(--font-serif)",
    fontStyle: "italic",
    fontSize: 16,
    fontWeight: 400,
    color: t.text,
    marginTop: 16,
    marginBottom: 8,
    paddingBottom: 4,
    borderBottom: `1px solid ${t.border}`,
  };

  const addMedication = () => {
    setMedications((prev) => [
      ...prev,
      { drug: COMMON_HF_DRUGS[0], dose_mg: "", frequency_per_day: "1" },
    ]);
  };

  const removeMedication = (index: number) => {
    setMedications((prev) => prev.filter((_, i) => i !== index));
  };

  const updateMedication = (
    index: number,
    field: keyof MedicationRow,
    value: string
  ) => {
    setMedications((prev) =>
      prev.map((m, i) => (i === index ? { ...m, [field]: value } : m))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !age.trim()) {
      setError("Name and age are required");
      return;
    }

    setSubmitting(true);
    setError(null);

    const request: PatientCreateRequest = {
      name: name.trim(),
      age: parseInt(age, 10),
      sex,
      ejection_fraction: ejectionFraction
        ? parseFloat(ejectionFraction) / 100
        : 0.0,
      nyha_class: parseInt(nyhaClass, 10),
      weight_kg: weightKg ? parseFloat(weightKg) : 70.0,
      height_cm: heightCm ? parseFloat(heightCm) : 170.0,
      medical_history: conditions
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      allergies: allergies
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      insurance_tier: insurance,
      medications: medications
        .filter((m) => m.drug && m.dose_mg)
        .map((m) => ({
          drug: m.drug,
          dose_mg: parseFloat(m.dose_mg),
          frequency_per_day: parseInt(m.frequency_per_day, 10),
          route: "oral",
          start_date: new Date().toISOString().split("T")[0],
          last_changed_date: new Date().toISOString().split("T")[0],
        })),
    };

    // Add initial vitals if any provided
    const vitals: Record<string, number> = {};
    if (systolicBp) vitals.systolic_bp = parseFloat(systolicBp);
    if (diastolicBp) vitals.diastolic_bp = parseFloat(diastolicBp);
    if (heartRate) vitals.heart_rate = parseFloat(heartRate);
    if (Object.keys(vitals).length > 0) {
      request.initial_vitals = vitals;
    }

    // Add initial labs if any provided
    const labs: Record<string, number> = {};
    if (potassium) labs.potassium = parseFloat(potassium);
    if (creatinine) labs.creatinine = parseFloat(creatinine);
    if (egfr) labs.egfr = parseFloat(egfr);
    if (Object.keys(labs).length > 0) {
      request.initial_labs = labs;
    }

    try {
      const patient = await createPatient(request);
      onCreated(patient.patient_id);
    } catch {
      setError("Failed to create patient. Check backend connection.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ padding: 4 }}>
      <h3
        style={{
          color: t.text,
          margin: "0 0 16px",
          fontSize: 20,
          fontWeight: 400,
          fontFamily: "var(--font-serif)",
          fontStyle: "italic",
        }}
      >
        New Patient
      </h3>

      {error && (
        <div
          style={{
            color: "#f87171",
            fontSize: 12,
            marginBottom: 12,
            padding: "6px 10px",
            background: "rgba(220,38,38,0.1)",
            borderRadius: 6,
          }}
        >
          {error}
        </div>
      )}

      {/* Row: Name */}
      <div style={{ marginBottom: 12 }}>
        <label style={labelStyle}>Full Name *</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Jane Doe"
          style={inputStyle}
          required
        />
      </div>

      {/* Row: Age + Sex */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div>
          <label style={labelStyle}>Age *</label>
          <input
            type="number"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="e.g. 65"
            style={inputStyle}
            min={18}
            max={120}
            required
          />
        </div>
        <div>
          <label style={labelStyle}>Sex</label>
          <select
            value={sex}
            onChange={(e) => setSex(e.target.value)}
            style={inputStyle}
          >
            <option value="F">Female</option>
            <option value="M">Male</option>
          </select>
        </div>
      </div>

      {/* Row: EF + NYHA */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div>
          <label style={labelStyle}>Ejection Fraction %</label>
          <input
            type="number"
            value={ejectionFraction}
            onChange={(e) => setEjectionFraction(e.target.value)}
            placeholder="e.g. 35"
            style={inputStyle}
            min={0}
            max={80}
          />
        </div>
        <div>
          <label style={labelStyle}>NYHA Class</label>
          <select
            value={nyhaClass}
            onChange={(e) => setNyhaClass(e.target.value)}
            style={inputStyle}
          >
            <option value="1">I</option>
            <option value="2">II</option>
            <option value="3">III</option>
            <option value="4">IV</option>
          </select>
        </div>
      </div>

      {/* Row: Weight + Height */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div>
          <label style={labelStyle}>Weight (kg)</label>
          <input
            type="number"
            value={weightKg}
            onChange={(e) => setWeightKg(e.target.value)}
            placeholder="e.g. 70"
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelStyle}>Height (cm)</label>
          <input
            type="number"
            value={heightCm}
            onChange={(e) => setHeightCm(e.target.value)}
            placeholder="e.g. 170"
            style={inputStyle}
          />
        </div>
      </div>

      {/* Vitals Section */}
      <div style={sectionStyle}>Vitals</div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div>
          <label style={labelStyle}>Systolic BP (mmHg)</label>
          <input
            type="number"
            value={systolicBp}
            onChange={(e) => setSystolicBp(e.target.value)}
            placeholder="120"
            style={inputStyle}
            min={60}
            max={250}
          />
        </div>
        <div>
          <label style={labelStyle}>Diastolic BP (mmHg)</label>
          <input
            type="number"
            value={diastolicBp}
            onChange={(e) => setDiastolicBp(e.target.value)}
            placeholder="80"
            style={inputStyle}
            min={30}
            max={150}
          />
        </div>
        <div>
          <label style={labelStyle}>Heart Rate (bpm)</label>
          <input
            type="number"
            value={heartRate}
            onChange={(e) => setHeartRate(e.target.value)}
            placeholder="72"
            style={inputStyle}
            min={30}
            max={200}
          />
        </div>
      </div>

      {/* Labs Section */}
      <div style={sectionStyle}>Labs</div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div>
          <label style={labelStyle}>Potassium (mEq/L)</label>
          <input
            type="number"
            value={potassium}
            onChange={(e) => setPotassium(e.target.value)}
            placeholder="3.5 - 5.0"
            style={inputStyle}
            step={0.1}
            min={1}
            max={8}
          />
        </div>
        <div>
          <label style={labelStyle}>Creatinine (mg/dL)</label>
          <input
            type="number"
            value={creatinine}
            onChange={(e) => setCreatinine(e.target.value)}
            placeholder="0.6 - 1.2"
            style={inputStyle}
            step={0.1}
            min={0.1}
            max={15}
          />
        </div>
        <div>
          <label style={labelStyle}>eGFR (mL/min)</label>
          <input
            type="number"
            value={egfr}
            onChange={(e) => setEgfr(e.target.value)}
            placeholder="60 - 120"
            style={inputStyle}
            min={1}
            max={150}
          />
        </div>
      </div>

      {/* Conditions */}
      <div style={{ marginBottom: 12 }}>
        <label style={labelStyle}>Medical Conditions (comma separated)</label>
        <input
          type="text"
          value={conditions}
          onChange={(e) => setConditions(e.target.value)}
          placeholder="e.g. hypertension, diabetes"
          style={inputStyle}
        />
      </div>

      {/* Allergies */}
      <div style={{ marginBottom: 12 }}>
        <label style={labelStyle}>Allergies (comma separated)</label>
        <input
          type="text"
          value={allergies}
          onChange={(e) => setAllergies(e.target.value)}
          placeholder="e.g. penicillin, sulfa"
          style={inputStyle}
        />
      </div>

      {/* Insurance */}
      <div style={{ marginBottom: 12 }}>
        <label style={labelStyle}>Insurance Tier</label>
        <select
          value={insurance}
          onChange={(e) => setInsurance(e.target.value)}
          style={inputStyle}
        >
          {INSURANCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Medications Section */}
      <div style={sectionStyle}>Current Medications</div>
      {medications.map((med, i) => (
        <div
          key={i}
          style={{
            display: "grid",
            gridTemplateColumns: "2fr 1fr 1fr auto",
            gap: 6,
            marginBottom: 8,
            alignItems: "end",
          }}
        >
          <div>
            <label style={labelStyle}>Drug</label>
            <select
              value={med.drug}
              onChange={(e) => updateMedication(i, "drug", e.target.value)}
              style={inputStyle}
            >
              {COMMON_HF_DRUGS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Dose (mg)</label>
            <input
              type="number"
              value={med.dose_mg}
              onChange={(e) => updateMedication(i, "dose_mg", e.target.value)}
              placeholder="mg"
              style={inputStyle}
              min={0}
            />
          </div>
          <div>
            <label style={labelStyle}>Freq/day</label>
            <select
              value={med.frequency_per_day}
              onChange={(e) =>
                updateMedication(i, "frequency_per_day", e.target.value)
              }
              style={inputStyle}
            >
              <option value="1">1x daily</option>
              <option value="2">2x daily</option>
              <option value="3">3x daily</option>
            </select>
          </div>
          <button
            type="button"
            onClick={() => removeMedication(i)}
            style={{
              background: "transparent",
              color: "#f87171",
              border: `1px solid rgba(220,38,38,0.3)`,
              borderRadius: 6,
              padding: "8px 10px",
              fontSize: 13,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addMedication}
        style={{
          background: "transparent",
          color: t.textMuted,
          border: `1px dashed ${t.border}`,
          borderRadius: 6,
          padding: "8px 14px",
          fontSize: 12,
          cursor: "pointer",
          fontFamily: "inherit",
          marginBottom: 16,
          width: "100%",
        }}
      >
        + Add medication
      </button>

      {/* Actions */}
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="submit"
          disabled={submitting}
          style={{
            flex: 1,
            background: t.accent,
            color: t.text,
            border: "none",
            borderRadius: 6,
            padding: "10px 16px",
            fontSize: 13,
            cursor: submitting ? "not-allowed" : "pointer",
            opacity: submitting ? 0.6 : 1,
            fontFamily: "inherit",
          }}
        >
          {submitting ? "Creating..." : "Create Patient"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          style={{
            background: "transparent",
            color: t.textMuted,
            border: `1px solid ${t.border}`,
            borderRadius: 6,
            padding: "10px 16px",
            fontSize: 13,
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
