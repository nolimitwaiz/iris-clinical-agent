/** TypeScript types matching the FastAPI Pydantic schemas. */

export interface ProjectedTrajectory {
  metric: string;
  current_values: number[];
  projected_30d_no_action: number;
  projected_30d_with_action: number;
  method: string;
  confidence: string;
}

export interface RiskComponent {
  score: number;
  weight: number;
  contribution: number;
  detail: string;
}

export interface RiskScore {
  composite: number;
  tier: string;
  components: Record<string, RiskComponent>;
}

export interface ActionPacket {
  tool_name: string;
  timestamp?: string;
  inputs_used?: Record<string, unknown>;
  decision: string;
  drug?: string;
  current_dose_mg?: number;
  new_dose_mg?: number;
  reason: string;
  guideline: string;
  monitoring?: string;
  confidence: string;
  risk_of_inaction: string;
  data_quality?: string;
  projected_trajectories?: ProjectedTrajectory[];
  risk_score?: RiskScore;
}

export interface ValidationResult {
  approved: boolean;
  violations: string[];
}

export interface Signals {
  symptoms: string[];
  side_effects: string[];
  adherence_signals: string[];
  questions: string[];
  barriers_mentioned: string[];
  mood: string;
}

export interface ChatRequest {
  patient_id: string;
  message?: string;
  audio_data?: string;
  audio_mime_type?: string;
  image_data?: string;
  image_mime_type?: string;
  conversation_history?: { role: string; content: string }[];
  generate_audio?: boolean;
}

export interface InitialVitals {
  systolic_bp?: number;
  diastolic_bp?: number;
  heart_rate?: number;
}

export interface InitialLabs {
  potassium?: number;
  creatinine?: number;
  egfr?: number;
}

export interface PatientCreateRequest {
  name: string;
  age: number;
  sex: string;
  ejection_fraction?: number;
  nyha_class?: number;
  weight_kg?: number;
  height_cm?: number;
  medical_history?: string[];
  allergies?: string[];
  medications?: Record<string, unknown>[];
  insurance_tier?: string;
  initial_vitals?: InitialVitals;
  initial_labs?: InitialLabs;
}

export interface PillarScore {
  name: string;
  drug: string | null;
  current_dose_mg: number | null;
  target_dose_mg: number | null;
  score: number;
  max_score: number;
  status: string;
}

export interface MOSResponse {
  mos_score: number;
  pillars: PillarScore[];
}

export interface ChatResponse {
  response_text: string;
  audio_response?: string;
  action_packets: ActionPacket[];
  validation: ValidationResult;
  signals: Signals;
  transcript?: string;
  conversation_history?: { role: string; content: string }[];
  mos?: MOSResponse;
}

export interface PatientSummary {
  patient_id: string;
  name: string;
  age: number;
  sex: string;
  ejection_fraction: number;
  nyha_class: number;
}

export interface Medication {
  drug: string;
  dose_mg: number;
  frequency_per_day: number;
  route: string;
  start_date: string;
  last_changed_date: string;
}

export interface LabValue {
  value: number;
  date: string;
}

export interface PatientDetail {
  patient_id: string;
  name: string;
  age: number;
  sex: string;
  height_cm: number;
  weight_kg: number;
  ejection_fraction: number;
  nyha_class: number;
  medical_history: string[];
  allergies: string[];
  medications: Medication[];
  labs: Record<string, LabValue[]>;
  vitals: Record<string, LabValue[]>;
  social_factors: Record<string, unknown>;
  adherence: Record<string, unknown>;
  conversation_history?: { role: string; content: string }[];
}

export interface HealthCheck {
  status: string;
  gemini_configured: boolean;
  drugs_loaded: number;
  alternatives_loaded: number;
}

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

export interface EducationTopic {
  full_name: string;
  what_it_measures: string;
  normal_range?: string;
  why_it_matters: string;
  simple_analogy?: string;
}

export type EducationContent = Record<string, EducationTopic>;
