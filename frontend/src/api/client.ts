/** API client for FastAPI backend. */

import type {
  ChatRequest,
  ChatResponse,
  PatientSummary,
  PatientDetail,
  PatientCreateRequest,
  HealthCheck,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function fetchJSON<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

export async function getHealth(): Promise<HealthCheck> {
  return fetchJSON("/health");
}

export async function listPatients(): Promise<PatientSummary[]> {
  return fetchJSON("/patients");
}

export async function getPatient(id: string): Promise<PatientDetail> {
  return fetchJSON(`/patients/${id}`);
}

export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  return fetchJSON("/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function createPatient(
  request: PatientCreateRequest
): Promise<PatientDetail> {
  return fetchJSON("/patients", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function startPatient(): Promise<PatientDetail> {
  return fetchJSON("/patients/start", { method: "POST" });
}

/** SSE event from /api/chat/stream */
export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * Stream a chat response via SSE. Calls onEvent for each parsed event.
 * Returns the full response text when done.
 */
export async function sendChatStream(
  request: ChatRequest,
  onEvent: (event: StreamEvent) => void
): Promise<string> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let fullText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const lines = part.trim().split("\n");
      let eventName = "";
      let dataStr = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventName = line.slice(7);
        } else if (line.startsWith("data: ")) {
          dataStr = line.slice(6);
        }
      }

      if (eventName && dataStr) {
        try {
          const data = JSON.parse(dataStr);
          const evt: StreamEvent = { event: eventName, data };
          onEvent(evt);

          if (eventName === "chunk") {
            fullText += (data.text as string) || "";
          } else if (eventName === "replace") {
            fullText = (data.text as string) || "";
          }
        } catch {
          // Skip malformed events
        }
      }
    }
  }

  return fullText;
}

export interface OnboardingResponse {
  response_text: string;
  progress: { current_step: number; total_steps: number; step_name: string; complete: boolean };
  extracted: Record<string, unknown> | null;
  patient_data: Record<string, unknown> | null;
  complete: boolean;
}

export async function sendOnboardingChat(
  patientId: string,
  message?: string,
  history?: { role: string; content: string }[]
): Promise<OnboardingResponse> {
  return fetchJSON("/chat/onboarding", {
    method: "POST",
    body: JSON.stringify({
      patient_id: patientId,
      message: message || "",
      conversation_history: history || [],
    }),
  });
}

export async function fetchEducation(): Promise<Record<string, unknown>> {
  return fetchJSON("/education");
}

export async function fetchTTS(
  text: string
): Promise<{ audio: string | null }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    return await fetchJSON("/chat/tts", {
      method: "POST",
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}
