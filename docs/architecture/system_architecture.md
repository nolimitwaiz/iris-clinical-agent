# Iris Core — System Architecture

## Overview

Iris Core is a tool first heart failure care agent. The language model handles communication only. Every clinical decision comes from deterministic Python tools that follow published guidelines.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PATIENT INTERFACE                           │
│                    (Streamlit Chat Window)                          │
│                                                                     │
│  Patient types: "I feel tired and my ankles are swollen"            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LLM EXTRACTOR (Gemini)                        │
│                                                                     │
│  Input: Patient message (natural language)                          │
│  Output: Structured JSON only                                       │
│  {                                                                  │
│    "symptoms": ["fatigue", "ankle_edema"],                          │
│    "side_effects": [],                                              │
│    "adherence_signals": [],                                         │
│    "questions": [],                                                 │
│    "barriers_mentioned": []                                         │
│  }                                                                  │
│                                                                     │
│  THIS IS THE ONLY THING THE LLM DOES AT THIS STAGE.                │
│  NO CLINICAL REASONING. NO RECOMMENDATIONS. EXTRACTION ONLY.       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 PYTHON ORCHESTRATOR (pipeline.py)                    │
│                                                                     │
│  Runs EVERY tool in FIXED order. No skipping. No LLM choice.       │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐      │
│  │ STEP 1: TRAJECTORY ANALYZER                               │      │
│  │                                                           │      │
│  │ Inputs: 14 days weight, BP, HR from patient profile       │      │
│  │ Method: Rolling 3 day median, 3d and 7d deltas            │      │
│  │ Output: Action Packet                                     │      │
│  │   risk_level: "moderate"                                  │      │
│  │   reason: "Weight +3.2 lbs over 5 days"                  │      │
│  │   confidence: "high" (if <30% data missing)               │      │
│  └───────────────────────────┬───────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────┐      │
│  │ STEP 2: GDMT ENGINE                                       │      │
│  │                                                           │      │
│  │ Inputs: Current meds, trajectory risk, latest labs         │      │
│  │ Scope: Diuretics + Beta Blockers (Phase 1A)               │      │
│  │ Method: Guideline decision trees (AHA/ACC 2022)           │      │
│  │ Output: Action Packet                                     │      │
│  │   decision: "increase"                                    │      │
│  │   drug: "furosemide"                                      │      │
│  │   new_dose_mg: 60                                         │      │
│  │   guideline: "AHA/ACC 2022 HF Guideline 7.3.2"           │      │
│  └───────────────────────────┬───────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────┐      │
│  │ STEP 3: SAFETY CHECKER                                     │      │
│  │                                                           │      │
│  │ Inputs: Proposed change, full med list, labs, allergies    │      │
│  │ Checks: Drug interactions, renal dosing, K+ risk,         │      │
│  │         contraindications, required monitoring             │      │
│  │ Output: Action Packet                                     │      │
│  │   decision: "safe" or "blocked"                           │      │
│  │   monitoring: "BMP in 7 days"                             │      │
│  └───────────────────────────┬───────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────┐      │
│  │ STEP 4: BARRIER PLANNER                                    │      │
│  │                                                           │      │
│  │ Inputs: Proposed drug, patient social factors, formulary   │      │
│  │ Checks: Cost by insurance tier, alternatives if needed     │      │
│  │ Output: Action Packet                                     │      │
│  │   decision: "feasible" or "barrier_detected"              │      │
│  │   alternative: "generic equivalent at $4/month"           │      │
│  └───────────────────────────┬───────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────┐      │
│  │ STEP 5: ESCALATION MANAGER                                 │      │
│  │                                                           │      │
│  │ Inputs: All Action Packets, overall risk assessment        │      │
│  │ Decision: Escalate to clinician or not                     │      │
│  │ Output: Action Packet + clinician summary if escalating    │      │
│  └───────────────────────────┬───────────────────────────────┘      │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM RESPONDER (Gemini)                           │
│                                                                     │
│  Input: ALL Action Packets + patient's original message             │
│  Instruction: Use ONLY facts from Action Packets.                   │
│               Do NOT add any clinical content from own knowledge.   │
│  Output: Draft patient facing message                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESPONSE VALIDATOR (Python)                       │
│                                                                     │
│  Scans the draft message for:                                       │
│  - Any medication name not in Action Packets                        │
│  - Any dose not in Action Packets                                   │
│  - Any lab value not in Action Packets                              │
│  - Any clinical recommendation not in Action Packets                │
│                                                                     │
│  If violation found: BLOCK. Regenerate with stricter prompt.        │
│  If clean: APPROVE. Send to patient.                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     VALIDATED RESPONSE                               │
│                                                                     │
│  "Maria, I can see from your weight readings that you may be        │
│   holding on to some extra fluid. Based on your latest labs, I      │
│   think we should increase your water pill from 40mg to 60mg.       │
│   It costs $4 with your insurance. I would also like to check       │
│   your blood work in one week to make sure everything stays         │
│   balanced. Does that sound okay?"                                  │
│                                                                     │
│  EVERY clinical fact in this message is traceable to an Action      │
│  Packet. The LLM only contributed the conversational framing.       │
└─────────────────────────────────────────────────────────────────────┘
```

## Streamlit Frontend Layout

```
┌──────────────────┬──────────────────────┬─────────────────────────┐
│  PATIENT DASH    │     CHAT             │  TRANSPARENCY PANEL     │
│                  │                      │                         │
│  Name: Maria     │  Patient: My feet    │  ► Trajectory Analyzer  │
│  Age: 67         │  are swollen and     │    Risk: MODERATE       │
│  EF: 30%         │  I feel tired.       │    Weight: +3.2lbs/5d   │
│  NYHA: III       │                      │    Guideline: 7.3.2     │
│                  │  Iris: I can see     │                         │
│  Medications:    │  from your weight    │  ► GDMT Engine          │
│  - Furosemide    │  readings that you   │    Decision: INCREASE   │
│    40mg daily    │  may be holding on   │    Drug: Furosemide     │
│  - Lisinopril    │  to some extra       │    40mg → 60mg          │
│    10mg daily    │  fluid...            │    Guideline: 7.3.2     │
│  - Metoprolol    │                      │                         │
│    25mg daily    │                      │  ► Safety Checker       │
│                  │                      │    Status: SAFE         │
│  Latest Labs:    │                      │    Monitoring: BMP 7d   │
│  K+: 4.1         │                      │                         │
│  Cr: 1.1         │                      │  ► Barrier Planner      │
│  eGFR: 58        │                      │    Status: FEASIBLE     │
│                  │                      │    Cost: $4/month       │
│  ┌────────────┐  │                      │                         │
│  │ Weight     │  │                      │  ► Escalation Manager   │
│  │ Trend ↗    │  │                      │    Status: NOT NEEDED   │
│  │ Chart      │  │                      │                         │
│  └────────────┘  │                      │                         │
│                  │                      │                         │
│  Risk: MODERATE  │                      │                         │
└──────────────────┴──────────────────────┴─────────────────────────┘
```

## Future: TA2 Integration Point

When TA2 (Iris Sentinel) is built, it intercepts at one point:

```
[Tool Pipeline] ──produces──> [Action Packets]
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                        ▼                       ▼
                  [TA2: Iris Sentinel]    [LLM Responder]
                  Independent verify      (waits for TA2
                  Stress test             approval)
                  Safety check
                        │
                        ▼
                  [Approve / Revise /
                   Route / Hard Stop]
                        │
                        ▼
                  [LLM Responder proceeds
                   only if Approved]
```

The Action Packet format is designed so TA2 can intercept and verify without any changes to TA1's code. This is why we build Action Packets correctly from day one.
