# Competitive Landscape Analysis
Date: 2026-03-06
Status: Decided

## Context
Understanding where every competitor stands is essential for positioning Iris and for ARPA-H reviewers who will ask "why not just use X?" This analysis covers the major players in clinical AI for cardiac care and adjacent spaces.

## Competitor Analysis

### Remote Patient Monitoring (RPM)

**Biofourmis**
- What they do: FDA-cleared RPM platform. Wearable sensors + dashboard for clinical teams. AI-powered analytics detect clinical deterioration.
- What they don't do: No patient-facing intelligence. No autonomous action. Alerts go to nurses who then call patients. The AI monitors; humans act.
- Iris difference: Iris acts autonomously within guardrails. The patient talks to Iris directly. No nurse-in-the-loop for routine management.

**CoPilotIQ**
- What they do: RPM for chronic conditions. Connected devices + care team monitoring. Proactive outreach by human nurses when readings are concerning.
- What they don't do: Human-dependent care delivery. AI assists the care team, doesn't interact with patients.
- Iris difference: Iris IS the care interaction for routine management. Clinicians are involved for escalations, not routine care.

### Cardiac AI Screening

**Eko Health**
- What they do: AI-powered stethoscope and ECG. FDA-cleared for detecting heart murmurs, AFib, low EF. Brilliant screening technology.
- What they don't do: Post-detection management. Eko finds the problem; someone else manages it. No ongoing patient relationship.
- Iris difference: Iris manages patients after diagnosis. Continuous, not episodic. Could integrate Eko screening data as input.

### Clinical AI Agents

**Hippocratic AI**
- What they do: Polaris constellation — 22 specialized models working together. Makes phone calls to patients for post-discharge follow-up, medication reminders, chronic care check-ins. Raised $150M+.
- What they don't do: Continuous care relationship. Calls are episodic. All 22 models in one system (no separate supervisory agent). No multimodal sensing (voice biomarkers, photo assessment). No behavioral intelligence.
- Iris difference: Iris maintains a persistent, evolving patient state. Every conversation builds on the last. Separate supervisory agent (TA2) for safety. Multimodal sensing. Deterministic clinical decisions, not model-generated.

### Clinician-Facing AI

**Abridge**
- What they do: Ambient clinical documentation. Records visit conversations, generates structured notes. FDA and clinician focused.
- What they don't do: Patient-facing anything. Helps doctors after the visit, not patients between visits.

**Suki AI**
- What they do: Voice-powered clinical assistant. Note generation, coding suggestions, clinical queries. Clinician workflow tool.
- What they don't do: Patient-facing care.

**Nabla**
- What they do: Clinical copilot for providers. Ambient documentation, care coordination.
- What they don't do: Patient-facing autonomous care.

Iris difference from all three: These are clinician productivity tools. Iris is a patient care tool. Different users, different purpose, different architecture.

### Mental Health AI (Adjacent Space)

**Woebot / Wysa**
- What they do: CBT-based chatbots for mental health. Rule-based + some ML. FDA breakthrough designation (Woebot).
- What they don't do: Clinical medication management. Vital sign monitoring. Medical device territory.
- Iris relevance: Behavioral intelligence techniques overlap. Iris can learn from their engagement and therapeutic alliance approaches.

## The Gap Nobody Fills

| Capability | Biofourmis | Eko | Hippocratic | Abridge | Iris |
|---|---|---|---|---|---|
| Patient-facing | No | No | Yes (calls) | No | Yes (continuous) |
| Autonomous action | No | No | Limited | No | Yes (deterministic) |
| Multimodal sensing | Wearables | Stethoscope | Voice only | Audio | Voice + Vision + Data |
| Behavioral intelligence | No | No | No | No | Yes (COM-B + TTM) |
| Continuous relationship | Dashboard | Episodic | Episodic calls | Visit-based | Persistent state |
| Supervisory agent | No | No | No | No | Yes (TA2) |
| FDA audit trail | Yes | Yes | Unknown | Yes | Yes (Action Packets) |

## Key Insight
Nobody is combining patient-facing + autonomous + multimodal + deterministic + behaviorally-aware in a single system. This is not because it's a bad idea — it's because it's hard. The regulatory pathway didn't exist until ADVOCATE. The architecture requires separating LLM communication from clinical reasoning. And behavioral intelligence in clinical AI is almost unexplored (15 studies worldwide).
