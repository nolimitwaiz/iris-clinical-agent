/**
 * clinicalGraph.ts — Pure functions to build a clinical knowledge graph
 * from patient data and action packets.
 *
 * Node types: drug, lab, vital, symptom, condition
 * Edge types: depends_on, interacts, triggers, affects, blocks, indicates, treated_by
 */

import type { PatientDetail, ActionPacket } from "../api/types";

// ── Node & Edge Types ──────────────────────────────────────────

export type ClinicalNodeType = "drug" | "lab" | "vital" | "symptom" | "condition";

export type ClinicalEdgeType =
  | "depends_on"   // drug → lab (furosemide gated by K+)
  | "interacts"    // drug ↔ drug (ARNI + ACEi)
  | "triggers"     // vital → drug (weight gain → diuretic)
  | "affects"      // drug → vital (BB → HR)
  | "blocks"       // lab → drug (K+ > 5.0 blocks MRA)
  | "indicates"    // symptom → condition
  | "treated_by";  // condition → drug

export interface ClinicalNode {
  id: string;
  type: ClinicalNodeType;
  label: string;
  value?: string;          // latest value for display ("4.2 mEq/L", "40mg")
  active: boolean;         // highlighted by current packets
  trend?: number[];        // last 3 values for sparkline (labs/vitals)
  meta?: Record<string, unknown>; // extra info for detail card
}

export interface ClinicalEdge {
  source: string;          // node id
  target: string;          // node id
  type: ClinicalEdgeType;
  label?: string;          // e.g. "blocks if K+ > 5.0"
  active: boolean;         // highlighted by current packets
  blocked: boolean;        // safety issue
}

export interface ClinicalGraphData {
  nodes: ClinicalNode[];
  edges: ClinicalEdge[];
}

// ── Static Clinical Relationships ──────────────────────────────
// Derived from GDMT engine + safety checker rules in Python

interface Relationship {
  source: string;  // generic key (drug class or specific drug)
  target: string;
  type: ClinicalEdgeType;
  label?: string;
}

const CLINICAL_RELATIONSHIPS: Relationship[] = [
  // Drug → Lab dependencies (GDMT/safety rules)
  { source: "furosemide", target: "potassium", type: "depends_on", label: "gated by K+ >= 3.5" },
  { source: "furosemide", target: "egfr", type: "depends_on", label: "gated by eGFR >= 20" },
  { source: "spironolactone", target: "potassium", type: "depends_on", label: "hold if K+ > 5.0" },
  { source: "eplerenone", target: "potassium", type: "depends_on", label: "hold if K+ > 5.0" },
  { source: "spironolactone", target: "egfr", type: "depends_on", label: "avoid if eGFR < 30" },
  { source: "eplerenone", target: "egfr", type: "depends_on", label: "avoid if eGFR < 30" },
  { source: "lisinopril", target: "potassium", type: "depends_on", label: "hold if K+ > 5.5" },
  { source: "enalapril", target: "potassium", type: "depends_on", label: "hold if K+ > 5.5" },
  { source: "losartan", target: "potassium", type: "depends_on", label: "hold if K+ > 5.5" },
  { source: "valsartan", target: "potassium", type: "depends_on", label: "hold if K+ > 5.5" },
  { source: "sacubitril_valsartan", target: "potassium", type: "depends_on", label: "hold if K+ > 5.5" },
  { source: "lisinopril", target: "creatinine", type: "depends_on", label: "hold if Cr rises > 30%" },
  { source: "enalapril", target: "creatinine", type: "depends_on", label: "hold if Cr rises > 30%" },
  { source: "losartan", target: "creatinine", type: "depends_on", label: "hold if Cr rises > 30%" },
  { source: "valsartan", target: "creatinine", type: "depends_on", label: "hold if Cr rises > 30%" },
  { source: "sacubitril_valsartan", target: "creatinine", type: "depends_on", label: "hold if Cr rises > 30%" },

  // Drug ↔ Drug interactions (safety checker)
  { source: "sacubitril_valsartan", target: "lisinopril", type: "interacts", label: "contraindicated (36h washout)" },
  { source: "sacubitril_valsartan", target: "enalapril", type: "interacts", label: "contraindicated (36h washout)" },
  { source: "lisinopril", target: "losartan", type: "interacts", label: "avoid dual RAAS" },
  { source: "enalapril", target: "losartan", type: "interacts", label: "avoid dual RAAS" },
  { source: "lisinopril", target: "valsartan", type: "interacts", label: "avoid dual RAAS" },
  { source: "enalapril", target: "valsartan", type: "interacts", label: "avoid dual RAAS" },
  { source: "spironolactone", target: "potassium_supplement", type: "interacts", label: "hyperkalemia risk" },

  // Vital → Drug triggers (GDMT rules)
  { source: "weight_kg", target: "furosemide", type: "triggers", label: "weight gain triggers increase" },
  { source: "systolic_bp", target: "carvedilol", type: "triggers", label: "BP > 90 allows uptitration" },
  { source: "systolic_bp", target: "metoprolol_succinate", type: "triggers", label: "BP > 90 allows uptitration" },
  { source: "heart_rate", target: "carvedilol", type: "triggers", label: "HR > 60 allows uptitration" },
  { source: "heart_rate", target: "metoprolol_succinate", type: "triggers", label: "HR > 60 allows uptitration" },

  // Drug → Vital affects (clinical knowledge)
  { source: "carvedilol", target: "heart_rate", type: "affects", label: "lowers heart rate" },
  { source: "metoprolol_succinate", target: "heart_rate", type: "affects", label: "lowers heart rate" },
  { source: "carvedilol", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },
  { source: "metoprolol_succinate", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },
  { source: "furosemide", target: "weight_kg", type: "affects", label: "reduces fluid weight" },
  { source: "lisinopril", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },
  { source: "enalapril", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },
  { source: "losartan", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },
  { source: "valsartan", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },
  { source: "sacubitril_valsartan", target: "systolic_bp", type: "affects", label: "lowers blood pressure" },

  // Lab → Drug blocks (safety rules)
  { source: "potassium", target: "spironolactone", type: "blocks", label: "K+ > 5.0 blocks" },
  { source: "potassium", target: "eplerenone", type: "blocks", label: "K+ > 5.0 blocks" },
  { source: "egfr", target: "spironolactone", type: "blocks", label: "eGFR < 30 blocks" },
  { source: "egfr", target: "eplerenone", type: "blocks", label: "eGFR < 30 blocks" },

  // Symptom → Condition (static clinical map)
  { source: "swelling", target: "heart_failure", type: "indicates" },
  { source: "fatigue", target: "heart_failure", type: "indicates" },
  { source: "shortness_of_breath", target: "heart_failure", type: "indicates" },
  { source: "dizziness", target: "heart_failure", type: "indicates" },
  { source: "weight_gain", target: "heart_failure", type: "indicates", label: "fluid retention" },
  { source: "cough", target: "heart_failure", type: "indicates" },
  { source: "palpitations", target: "heart_failure", type: "indicates" },

  // Condition → Drug (treatment)
  { source: "heart_failure", target: "furosemide", type: "treated_by" },
  { source: "heart_failure", target: "carvedilol", type: "treated_by" },
  { source: "heart_failure", target: "metoprolol_succinate", type: "treated_by" },
  { source: "heart_failure", target: "lisinopril", type: "treated_by" },
  { source: "heart_failure", target: "enalapril", type: "treated_by" },
  { source: "heart_failure", target: "losartan", type: "treated_by" },
  { source: "heart_failure", target: "valsartan", type: "treated_by" },
  { source: "heart_failure", target: "sacubitril_valsartan", type: "treated_by" },
  { source: "heart_failure", target: "spironolactone", type: "treated_by" },
  { source: "heart_failure", target: "eplerenone", type: "treated_by" },
  { source: "diabetes", target: "metformin", type: "treated_by" },
  { source: "hypertension", target: "lisinopril", type: "treated_by" },
  { source: "hypertension", target: "losartan", type: "treated_by" },
];

// ── Display helpers ────────────────────────────────────────────

const LAB_UNITS: Record<string, string> = {
  potassium: "mEq/L",
  creatinine: "mg/dL",
  egfr: "mL/min",
  bnp: "pg/mL",
  sodium: "mEq/L",
};

const LAB_RANGES: Record<string, string> = {
  potassium: "3.5 \u2013 5.0",
  creatinine: "0.7 \u2013 1.3",
  egfr: "> 60",
  bnp: "< 100",
  sodium: "136 \u2013 145",
};

const VITAL_UNITS: Record<string, string> = {
  weight_kg: "kg",
  systolic_bp: "mmHg",
  diastolic_bp: "mmHg",
  heart_rate: "bpm",
};

const VITAL_DISPLAY: Record<string, string> = {
  weight_kg: "weight",
  systolic_bp: "systolic BP",
  diastolic_bp: "diastolic BP",
  heart_rate: "heart rate",
};

function normalizeDrugId(name: string): string {
  return name.toLowerCase().replace(/[\s\-\/]+/g, "_").replace(/[^a-z0-9_]/g, "");
}

function normalizeName(name: string): string {
  return name.toLowerCase().replace(/[\s\-]+/g, "_").replace(/[^a-z0-9_]/g, "");
}

// ── Build Graph ────────────────────────────────────────────────

export function buildClinicalGraph(
  patientDetail: PatientDetail | null,
  packets: ActionPacket[],
): ClinicalGraphData {
  if (!patientDetail) return { nodes: [], edges: [] };

  const nodeMap = new Map<string, ClinicalNode>();
  const edgeList: ClinicalEdge[] = [];

  // Collect active drug names and decision types from packets
  const activeDrugs = new Set<string>();
  const activeDecisions = new Map<string, string>(); // drugId → decision
  for (const pkt of packets) {
    if (pkt.drug) {
      const id = normalizeDrugId(pkt.drug);
      activeDrugs.add(id);
      activeDecisions.set(id, pkt.decision);
    }
  }

  // Extract symptoms from latest packets' inputs_used
  const symptoms = new Set<string>();
  for (const pkt of packets) {
    if (pkt.inputs_used) {
      const syms = pkt.inputs_used.symptoms as string[] | undefined;
      if (syms) syms.forEach((s) => symptoms.add(normalizeName(s)));
      const sides = pkt.inputs_used.side_effects as string[] | undefined;
      if (sides) sides.forEach((s) => symptoms.add(normalizeName(s)));
    }
  }

  // 1. Drug nodes
  for (const med of patientDetail.medications) {
    const id = normalizeDrugId(med.drug);
    const decision = activeDecisions.get(id);
    nodeMap.set(id, {
      id,
      type: "drug",
      label: med.drug,
      value: `${med.dose_mg}mg`,
      active: activeDrugs.has(id),
      meta: {
        dose_mg: med.dose_mg,
        frequency: med.frequency_per_day,
        route: med.route,
        start_date: med.start_date,
        last_changed: med.last_changed_date,
        decision,
      },
    });
  }

  // 2. Lab nodes
  for (const [labName, values] of Object.entries(patientDetail.labs)) {
    if (!values || values.length === 0) continue;
    const id = normalizeName(labName);
    const sorted = [...values].sort((a, b) => a.date.localeCompare(b.date));
    const latest = sorted[sorted.length - 1];
    const trend = sorted.slice(-3).map((v) => v.value);
    const unit = LAB_UNITS[id] || "";
    nodeMap.set(id, {
      id,
      type: "lab",
      label: labName,
      value: `${latest.value} ${unit}`.trim(),
      active: false,
      trend,
      meta: {
        latest_value: latest.value,
        latest_date: latest.date,
        unit,
        normal_range: LAB_RANGES[id],
      },
    });
  }

  // 3. Vital nodes
  for (const [vitalName, values] of Object.entries(patientDetail.vitals)) {
    if (!values || values.length === 0) continue;
    const id = normalizeName(vitalName);
    const sorted = [...values].sort((a, b) => a.date.localeCompare(b.date));
    const latest = sorted[sorted.length - 1];
    const trend = sorted.slice(-5).map((v) => v.value);
    const unit = VITAL_UNITS[id] || "";
    nodeMap.set(id, {
      id,
      type: "vital",
      label: VITAL_DISPLAY[id] || vitalName,
      value: `${latest.value} ${unit}`.trim(),
      active: false,
      trend,
      meta: {
        latest_value: latest.value,
        latest_date: latest.date,
        unit,
      },
    });
  }

  // 4. Symptom nodes
  for (const sym of symptoms) {
    nodeMap.set(sym, {
      id: sym,
      type: "symptom",
      label: sym.replace(/_/g, " "),
      active: true,
    });
  }

  // 5. Condition nodes
  for (const condition of patientDetail.medical_history) {
    const id = normalizeName(condition);
    nodeMap.set(id, {
      id,
      type: "condition",
      label: condition,
      active: false,
    });
  }

  // Mark labs/vitals as active if referenced by active packets
  for (const pkt of packets) {
    if (pkt.inputs_used) {
      for (const key of Object.keys(pkt.inputs_used)) {
        const nk = normalizeName(key);
        const node = nodeMap.get(nk);
        if (node) node.active = true;
      }
    }
    // GDMT/safety monitoring references
    if (pkt.monitoring) {
      const monLower = pkt.monitoring.toLowerCase();
      if (monLower.includes("potassium")) { const n = nodeMap.get("potassium"); if (n) n.active = true; }
      if (monLower.includes("creatinine")) { const n = nodeMap.get("creatinine"); if (n) n.active = true; }
      if (monLower.includes("egfr") || monLower.includes("gfr")) { const n = nodeMap.get("egfr"); if (n) n.active = true; }
      if (monLower.includes("bmp")) {
        for (const k of ["potassium", "creatinine", "sodium"]) {
          const n = nodeMap.get(k); if (n) n.active = true;
        }
      }
    }
  }

  // 6. Build edges from CLINICAL_RELATIONSHIPS
  const seenEdges = new Set<string>();

  for (const rel of CLINICAL_RELATIONSHIPS) {
    const srcNode = nodeMap.get(rel.source);
    const tgtNode = nodeMap.get(rel.target);
    if (!srcNode || !tgtNode) continue;

    const edgeKey = `${rel.source}--${rel.type}--${rel.target}`;
    if (seenEdges.has(edgeKey)) continue;
    seenEdges.add(edgeKey);

    const isActive = srcNode.active || tgtNode.active;
    const isBlocked = rel.type === "interacts" || rel.type === "blocks";

    edgeList.push({
      source: rel.source,
      target: rel.target,
      type: rel.type,
      label: rel.label,
      active: isActive,
      blocked: isBlocked && isActive,
    });
  }

  return {
    nodes: Array.from(nodeMap.values()),
    edges: edgeList,
  };
}
