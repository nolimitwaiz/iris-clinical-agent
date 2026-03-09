/**
 * IrisContext — shared state between PatientView and ClinicianView.
 *
 * Holds: selected patient, conversation history, action packets,
 * backend health status, and patient list.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { getHealth, listPatients, getPatient, startPatient, fetchEducation } from "../api/client";
import type {
  PatientSummary,
  PatientDetail,
  ActionPacket,
  HealthCheck,
  OrbState,
  MOSResponse,
  EducationContent,
} from "../api/types";

export interface ConversationTurn {
  role: "patient" | "iris";
  content: string;
  packets?: ActionPacket[];
  validation?: { approved: boolean; violations: string[] };
}

interface IrisContextValue {
  /** Backend health status */
  backendConnected: boolean;
  healthChecking: boolean;
  healthData: HealthCheck | null;
  retryHealth: () => void;

  /** Patient list */
  patients: PatientSummary[];
  patientsLoading: boolean;
  patientsError: string | null;
  retryPatients: () => void;

  /** Selected patient */
  selectedPatientId: string;
  setSelectedPatientId: (id: string) => void;
  patientDetail: PatientDetail | null;
  patientLoading: boolean;
  patientError: string | null;
  retryPatientDetail: () => void;

  /** Onboarding */
  isOnboarding: boolean;
  setIsOnboarding: (v: boolean) => void;
  onboardingProgress: { current_step: number; total_steps: number; step_name: string; complete: boolean } | null;
  setOnboardingProgress: React.Dispatch<React.SetStateAction<{ current_step: number; total_steps: number; step_name: string; complete: boolean } | null>>;
  completeOnboarding: () => Promise<void>;

  /** Start a new anonymous patient for conversational onboarding */
  startNewPatient: () => Promise<string>;

  /** Conversation */
  conversations: ConversationTurn[];
  setConversations: React.Dispatch<React.SetStateAction<ConversationTurn[]>>;
  addPatientMessage: (msg: string) => void;
  addIrisResponse: (turn: ConversationTurn) => void;

  /** Action packets (latest) */
  packets: ActionPacket[];
  setPackets: React.Dispatch<React.SetStateAction<ActionPacket[]>>;

  /** Medication Optimization Score */
  mos: MOSResponse | null;
  setMos: React.Dispatch<React.SetStateAction<MOSResponse | null>>;

  /** Orb state (for typing indicator) */
  orbState: OrbState;
  setOrbState: React.Dispatch<React.SetStateAction<OrbState>>;

  /** Streaming text (partial response during generation) */
  streamingText: string;
  setStreamingText: React.Dispatch<React.SetStateAction<string>>;

  /** Education content for tooltips */
  educationContent: EducationContent | null;
}

const IrisContext = createContext<IrisContextValue>(null!);

export function IrisProvider({ children }: { children: ReactNode }) {
  // Health
  const [backendConnected, setBackendConnected] = useState(false);
  const [healthChecking, setHealthChecking] = useState(true);
  const [healthData, setHealthData] = useState<HealthCheck | null>(null);
  const healthInterval = useRef<ReturnType<typeof setInterval>>(undefined);

  const checkHealth = useCallback(async () => {
    setHealthChecking(true);
    try {
      const h = await getHealth();
      setHealthData(h);
      setBackendConnected(true);
    } catch {
      setBackendConnected(false);
      setHealthData(null);
    } finally {
      setHealthChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    healthInterval.current = setInterval(checkHealth, 30000);
    return () => clearInterval(healthInterval.current);
  }, [checkHealth]);

  // Patients
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [patientsError, setPatientsError] = useState<string | null>(null);

  const loadPatients = useCallback(async () => {
    setPatientsLoading(true);
    setPatientsError(null);
    try {
      const list = await listPatients();
      setPatients(list);
    } catch {
      setPatientsError("Could not load patient list");
      setPatients([]);
    } finally {
      setPatientsLoading(false);
    }
  }, []);

  useEffect(() => { loadPatients(); }, [loadPatients]);

  // Selected patient
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [patientDetail, setPatientDetail] = useState<PatientDetail | null>(null);
  const [patientLoading, setPatientLoading] = useState(false);
  const [patientError, setPatientError] = useState<string | null>(null);

  const loadPatientDetail = useCallback(async (id: string) => {
    if (!id) return;
    setPatientLoading(true);
    setPatientError(null);
    try {
      const p = await getPatient(id);
      setPatientDetail(p);
    } catch {
      setPatientError("Could not load patient details");
      setPatientDetail(null);
    } finally {
      setPatientLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPatientDetail(selectedPatientId);
  }, [selectedPatientId, loadPatientDetail]);

  // Auto-select first patient when list loads non-empty and no selection
  useEffect(() => {
    if (!patientsLoading && patients.length > 0 && !selectedPatientId) {
      setSelectedPatientId(patients[0].patient_id);
    }
  }, [patientsLoading, patients, selectedPatientId]);

  // Onboarding
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [onboardingProgress, setOnboardingProgress] = useState<{
    current_step: number; total_steps: number; step_name: string; complete: boolean;
  } | null>(null);

  // Create anonymous patient for conversational onboarding
  const startNewPatient = useCallback(async (): Promise<string> => {
    const patient = await startPatient();
    setSelectedPatientId(patient.patient_id);
    await loadPatients();
    return patient.patient_id;
  }, [loadPatients]);

  // Complete onboarding — clear flag, reload patients
  const completeOnboarding = useCallback(async () => {
    setIsOnboarding(false);
    setOnboardingProgress(null);
    await loadPatients();
    // Reload patient detail so name/data updates
    if (selectedPatientId) {
      await loadPatientDetail(selectedPatientId);
    }
  }, [loadPatients, loadPatientDetail, selectedPatientId]);

  // Auto-detect first-time user: if patients list is empty after loading, start onboarding
  useEffect(() => {
    if (!patientsLoading && patients.length === 0 && backendConnected && !isOnboarding) {
      setIsOnboarding(true);
    }
  }, [patientsLoading, patients.length, backendConnected, isOnboarding]);

  // Conversation & packets
  const [conversations, setConversations] = useState<ConversationTurn[]>([]);
  const [packets, setPackets] = useState<ActionPacket[]>([]);
  const [mos, setMos] = useState<MOSResponse | null>(null);
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [streamingText, setStreamingText] = useState("");

  // Education content
  const [educationContent, setEducationContent] = useState<EducationContent | null>(null);

  useEffect(() => {
    if (backendConnected && !educationContent) {
      fetchEducation().then((data) => setEducationContent(data as EducationContent)).catch(() => {});
    }
  }, [backendConnected, educationContent]);

  // Seed conversation from persisted history when patient detail loads
  useEffect(() => {
    if (patientDetail?.conversation_history?.length) {
      setConversations(
        patientDetail.conversation_history.map((t) => ({
          role: t.role as "patient" | "iris",
          content: t.content,
        }))
      );
    } else {
      setConversations([]);
    }
    setPackets([]);
    setMos(null);
  }, [patientDetail]);

  const addPatientMessage = useCallback((msg: string) => {
    setConversations((prev) => [...prev, { role: "patient", content: msg }]);
  }, []);

  const addIrisResponse = useCallback((turn: ConversationTurn) => {
    setConversations((prev) => [...prev, turn]);
  }, []);

  return (
    <IrisContext.Provider
      value={{
        backendConnected,
        healthChecking,
        healthData,
        retryHealth: checkHealth,
        patients,
        patientsLoading,
        patientsError,
        retryPatients: loadPatients,
        selectedPatientId,
        setSelectedPatientId,
        patientDetail,
        patientLoading,
        patientError,
        retryPatientDetail: () => loadPatientDetail(selectedPatientId),
        isOnboarding,
        setIsOnboarding,
        onboardingProgress,
        setOnboardingProgress,
        completeOnboarding,
        startNewPatient,
        conversations,
        setConversations,
        addPatientMessage,
        addIrisResponse,
        packets,
        setPackets,
        mos,
        setMos,
        orbState,
        setOrbState,
        streamingText,
        setStreamingText,
        educationContent,
      }}
    >
      {children}
    </IrisContext.Provider>
  );
}

export function useIris() {
  return useContext(IrisContext);
}
