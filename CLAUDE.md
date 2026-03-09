# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

You are building Iris Core, a tool first heart failure care agent. Read SOUL.md first for the philosophy. This file tells you how to build it.

## Critical Rules

1. **The LLM never makes clinical decisions.** Every clinical fact must come from a deterministic Python tool. The LLM extracts patient input and communicates tool outputs. Nothing else.
2. **Every tool returns an Action Packet.** A structured dictionary with: tool_name, inputs_used, decision, drug (if applicable), reason, guideline, monitoring, confidence, and risk_of_inaction. No exceptions.
3. **The tool pipeline runs in fixed order every time.** Adherence Monitor > Trajectory Analyzer > GDMT Engine > Safety Checker > Barrier Planner > Escalation Manager. The LLM does not choose which tools to call. Python code runs all of them.
4. **The Response Validator blocks hallucinations.** After the LLM drafts a patient message, a Python function checks every medication name and dose against the Action Packets. If anything was invented, regenerate.
5. **No hyphens in patient facing text.** Use spaces instead. This is a style requirement.

## Commands

```bash
pip install -r requirements.txt                          # install Python dependencies
python -m pytest tests/                                  # run all tests
python -m pytest tests/test_gdmt.py                      # run a single test file
python -m pytest tests/test_gdmt.py::test_function_name -v  # run a single test

# FastAPI backend (primary)
uvicorn api.main:app --reload --port 8000                # run the API server

# React frontend
cd frontend && npm install                               # install frontend dependencies
cd frontend && npm run dev                               # run Vite dev server (port 5173)

# Streamlit frontend (legacy)
streamlit run app.py                                     # run the Streamlit app
```

Requires a `.env` file with `GEMINI_API_KEY` set.

## Tech Stack

- Python 3.11+
- Gemini 2.0 Flash (free tier) for LLM extraction and response generation
- FastAPI backend (`api/`) with Pydantic schemas
- React 19 + TypeScript + Vite frontend (`frontend/`) with React Router 7
- Streamlit frontend (`app.py` + `src/frontend/`) as legacy alternative
- JSON files for patient data, drug database, and alternative mappings
- No paid APIs, no cloud services, everything runs locally
- Use google-genai Python SDK for Gemini

## Architecture

### Data Flow (NEVER DEVIATE FROM THIS)

```
Patient Message
      │
      ▼
[LLM Extractor] ── Gemini extracts structured JSON only:
      │              {symptoms, side_effects, adherence, questions, barriers}
      │
      ▼
[Python Orchestrator] ── runs FIXED pipeline, every time, no skipping:
      │
      ├── 1. Adherence Monitor ── refill timing/barrier detection ── returns Action Packet
      ├── 2. Trajectory Analyzer ── weight/vitals trends ── returns Action Packet
      ├── 3. GDMT Engine ── medication optimization ── returns Action Packet
      ├── 4. Safety Checker ── drug interactions/contraindications ── returns Action Packet
      ├── 5. Barrier Planner ── cost/access/feasibility ── returns Action Packet
      └── 6. Escalation Manager ── clinician alert if needed ── returns Action Packet
      │
      ▼
[LLM Responder] ── Gemini generates patient message using ONLY Action Packet contents
      │
      ▼
[Response Validator] ── Python checks every med/dose against Action Packets
      │                   If hallucination detected: BLOCK and regenerate
      ▼
Patient receives validated response
```

### Action Packet Schema

Every tool MUST return this format:

```python
{
    "tool_name": str,           # e.g. "gdmt_engine"
    "timestamp": str,           # ISO format
    "inputs_used": dict,        # exact inputs the tool processed
    "decision": str,            # "increase", "maintain", "hold", "start", "stop", "escalate", "no_change"
    "drug": str | None,         # drug name if applicable
    "current_dose_mg": float | None,
    "new_dose_mg": float | None,
    "reason": str,              # plain English reason
    "guideline": str,           # specific guideline citation e.g. "AHA/ACC 2022 HF Guideline 7.3.2"
    "monitoring": str | None,   # required followup e.g. "BMP in 7 days"
    "confidence": str,          # "high", "moderate", "low"
    "risk_of_inaction": str,    # what happens if we do nothing
    "data_quality": str | None  # flag if data is missing or unreliable
}
```

### Patient Data Schema

```python
{
    "patient_id": str,
    "name": str,
    "age": int,
    "sex": str,
    "height_cm": float,
    "weight_kg": float,
    "ejection_fraction": float,       # e.g. 0.30 for 30%
    "nyha_class": int,                # 1-4
    "medical_history": [str],
    "allergies": [str],
    "medications": [
        {
            "drug": str,
            "dose_mg": float,
            "frequency_per_day": int,
            "route": str,
            "start_date": str,
            "last_changed_date": str
        }
    ],
    "labs": {
        "potassium": [{"value": float, "date": str}],
        "creatinine": [{"value": float, "date": str}],
        "egfr": [{"value": float, "date": str}],
        "bnp": [{"value": float, "date": str}],
        "sodium": [{"value": float, "date": str}]
    },
    "vitals": {
        "weight_kg": [{"value": float, "date": str}],
        "systolic_bp": [{"value": float, "date": str}],
        "diastolic_bp": [{"value": float, "date": str}],
        "heart_rate": [{"value": float, "date": str}]
    },
    "social_factors": {
        "lives_alone": bool,
        "insurance_tier": str,        # "tier1_generic", "tier2_preferred", "tier3_nonpreferred", "uninsured"
        "income_bracket": str,        # "low", "medium", "high"
        "works_nights": bool,
        "has_refrigeration": bool,
        "pharmacy_distance_miles": float,
        "health_literacy": str,       # "low", "moderate", "high"
        "preferred_language": str
    },
    "adherence": {
        "last_refill_date": str,
        "days_since_refill": int,
        "refill_on_time": bool,
        "reported_barriers": [str]
    },
    "conversation_history": []
}
```

## Drug Database Schema

```python
{
    "drug_name": str,
    "brand_name": str,
    "drug_class": str,           # "loop_diuretic", "beta_blocker", "arni", "ace_inhibitor", "arb", "mra", "sglt2i"
    "available_doses_mg": [float],
    "target_dose_mg": float,
    "starting_dose_mg": float,
    "max_dose_mg": float,
    "cost_per_month": {
        "tier1_generic": float,
        "tier2_preferred": float,
        "tier3_nonpreferred": float,
        "uninsured": float
    },
    "interactions": [str],       # list of drug names that interact
    "contraindications": [str],  # list of conditions
    "renal_adjustment": {
        "egfr_threshold": float,
        "action": str            # "reduce_dose", "avoid", "monitor_closely"
    },
    "monitoring_requirements": [str],
    "side_effects": [str]
}
```

## GDMT Engine Rules (Diuretics)

These are the rules for diuretic management. Implement as Python if/else logic:

- If weight gain > 2 lbs over 5 days AND potassium >= 3.5 AND eGFR >= 20: recommend diuretic dose increase
- If weight gain > 3 lbs in 24 hours: flag urgent, consider escalation
- If potassium < 3.5: hold diuretic increase, recommend potassium supplementation, recheck in 3 days
- If eGFR < 20: flag for nephrology input, do not adjust without clinician
- If currently on no diuretic and signs of congestion: start furosemide 20mg daily
- If on furosemide < 40mg: increase to 40mg
- If on furosemide 40mg: increase to 80mg
- If on furosemide >= 80mg: consider adding metolazone or escalate
- After any diuretic change: require BMP (basic metabolic panel) in 7 days
- Guideline citation: AHA/ACC 2022 HF Guideline Section 7.3.2

## GDMT Engine Rules (Beta Blockers)

- If ejection fraction <= 40% AND not on beta blocker AND systolic BP > 90 AND heart rate > 60: start carvedilol 3.125mg twice daily or metoprolol succinate 12.5mg daily
- If on beta blocker below target dose AND systolic BP > 90 AND heart rate > 60 AND no recent decompensation (14 days): uptitrate
- Carvedilol titration: 3.125 > 6.25 > 12.5 > 25mg (twice daily). Target: 25mg twice daily
- Metoprolol succinate titration: 12.5 > 25 > 50 > 100 > 200mg (daily). Target: 200mg daily
- If heart rate < 55: hold uptitration, consider dose reduction
- If systolic BP < 85: hold uptitration
- If recent decompensation within 14 days: do not uptitrate, reassess at next visit
- Wait at least 2 weeks between uptitrations
- Guideline citation: AHA/ACC 2022 HF Guideline Section 7.3.3

## Safety Checker Rules

Key interactions to implement:
- ARNI + ACE inhibitor: CONTRAINDICATED (36 hour washout required)
- Potassium sparing diuretic + MRA: HIGH RISK for hyperkalemia, requires close K+ monitoring
- ACE inhibitor + ARB: generally avoid dual RAAS blockade
- NSAID + any HF medication: avoid, worsens fluid retention
- If eGFR < 30: avoid or reduce dose of spironolactone/eplerenone
- If eGFR < 15: flag for nephrology, most dose adjustments need specialist input
- If potassium > 5.0: hold MRA, hold potassium supplements, recheck in 48 hours
- If potassium > 5.5: urgent flag, hold ACEi/ARB/ARNI/MRA, escalate
- After starting or increasing ACEi/ARB/ARNI: check creatinine and potassium in 1 to 2 weeks
- If creatinine rises > 30% after ACEi/ARB/ARNI change: hold medication, escalate

## Gemini Integration

Use the google-generativeai Python SDK:

```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
```

For extraction:
```python
extraction_prompt = """You are a clinical information extractor. Given a patient message, extract ONLY the following as JSON. Do not interpret, diagnose, or recommend anything.
{
    "symptoms": [],
    "side_effects": [],
    "adherence_signals": [],
    "questions": [],
    "barriers_mentioned": [],
    "mood": ""
}
Patient message: {message}"""
```

For response generation:
```python
response_prompt = """You are a heart failure care assistant. Generate a warm, clear response to the patient using ONLY the clinical facts in the Action Packets below. Rules:
- Do NOT add any medication, dose, lab value, or clinical recommendation not in the packets
- Do NOT use medical jargon unless explaining it in plain language
- Be empathetic and conversational
- If monitoring is required, explain why in simple terms
- Do not use hyphens in the text, use spaces instead

Action Packets: {packets_json}
Patient's original message: {message}
Patient's health literacy level: {literacy}"""
```

## Obsidian Integration

Claude Code must maintain notes in the obsidian/ directory. Follow these rules:

### Daily Notes (obsidian/daily/YYYY-MM-DD.md)

At the END of every coding session, create or update a daily note with:
```markdown
# YYYY-MM-DD

## What Was Built Today
- [list of features/files created or modified]

## Key Decisions Made
- [architecture decisions, tool changes, scope changes]

## Problems Encountered
- [bugs, design issues, things that didn't work]

## Current State
- [what works, what's broken, what's next]

## Tomorrow's Plan
- [next steps in priority order]
```

### Architecture Notes (obsidian/architecture/)

When any architecture decision is made, create a note:
```markdown
# [Decision Title]
Date: YYYY-MM-DD
Status: [Decided/Proposed/Superseded]

## Context
[Why this decision was needed]

## Decision
[What was decided]

## Alternatives Considered
[What else was considered and why it was rejected]

## Consequences
[What changes because of this decision]
```

### Decision Log (obsidian/decisions/)

For significant project decisions (scope changes, tech stack changes, strategy shifts), log:
```markdown
# [Decision]
Date: YYYY-MM-DD
Made By: [who decided]
Reason: [why]
Impact: [what changes]
```

## ARPA-H Context

This project originated from ARPA-H ADVOCATE program submissions:
- TA1 Solution Summary: Iris Core (patient facing agent)
- TA2 Solution Summary: Iris Sentinel (supervisory agent)
- Submitted: February 27, 2026 (late, after 5 PM deadline)
- Confirmation emails received for both
- Full proposal deadline if encouraged: April 1, 2026
- Solution summary documents are in docs/arpa-h/

The prototype must demonstrate the architecture described in the solution summaries. When ARPA-H reviewers or Spark/Fuel advisors see the demo, it should match what was proposed.

## Voice Biomarker Pipeline (New Capability)

Extract acoustic features passively from every voice interaction:
- Speaking rate, pause patterns, breathlessness indicators, vocal tremor, jitter, shimmer, harmonic-to-noise ratio
- 27 acoustic features correlate with BNP levels (AHA Circulation: Heart Failure systematic review)
- AHF-Voice study: 98% accuracy discriminating wet/dry states from speech measures
- Runs as background analysis during voice conversations via Gemini's native audio understanding
- Feeds structured feature scores into trajectory analyzer as additional decompensation signal
- NOT diagnostic alone — combined with vitals/weight for composite decompensation risk scoring
- Implementation: Gemini audio input → structured acoustic feature extraction → trajectory analyzer input

## Visual Assessment Pipeline (New Capability)

Accept photos via existing image upload endpoint, use Gemini Vision for structured extraction:
- **Ankle/foot edema photos**: Grade edema (0-4+), compare to prior photos, feed to trajectory analyzer
- **Medication pill photos**: Verify against patient's medication list, feed to adherence monitor
- **Scale display photos**: OCR extracts weight reading, feed to trajectory analyzer as vitals input
- **Device site photos**: Check cardiac device implant sites for infection/inflammation, feed to escalation manager
- Each visual input generates structured data that flows through existing deterministic pipeline
- Image analysis service (`api/services/image.py`) currently stubbed — implement with Gemini Vision

## Behavioral State Machine (New Capability)

Track each patient's behavioral profile and adapt communication:
- **COM-B assessment per patient**: Capability (do they know how?), Opportunity (can they access it?), Motivation (do they want to?)
- **Transtheoretical Model stage tracking per behavior**: precontemplation, contemplation, preparation, action, maintenance
- **Stage-aware response generation**: Don't push action on precontemplation patients. Reinforce maintenance patients. Match communication to readiness.
- **Intervention response history**: Track which approaches worked for this patient before
- Stage detection via LLM extraction from conversation patterns (not single messages)
- COM-B assessment updated by barrier planner based on conversation history
- Behavioral state stored in patient data, evolves over time

## 4-Layer Patient State (Enhancement)

Patient data model expands from clinical-only to four layers:
- **Clinical**: Existing vitals/labs/meds + voice biomarker scores + visual assessment results
- **Behavioral**: Stage of change per target behavior, barrier inventory with resolution history, intervention response tracking, COM-B assessment
- **Communication**: Health literacy (dynamic, not static), preferred framing (gain vs loss), engagement trend, dropout risk score
- **Social**: Support system changes, financial stress signals, access barrier updates, insurance changes

## Proactive Outreach (New Capability)

Don't wait for patient to report — predict and initiate:
- Combine trajectory analysis + voice biomarker trends + adherence patterns to detect early decompensation
- "Hi Maria, I noticed your weight has been trending up. Can we talk about how you are feeling?"
- Research shows 25-30% reduction in ED visits from proactive AI outreach in chronic disease management
- Proactive outreach triggers are deterministic (trajectory + adherence tools), not LLM-generated

## Digital Twin Lite (Future — Stub Only)

Simplified hemodynamic model per patient:
- "What-if" medication scenarios: "If we increase furosemide to 80mg, the model predicts weight decrease of 1.2kg over 5 days with 12% risk of K+ dropping below 3.5"
- Lightweight parametric model trained on population data, personalized with patient history
- NOT full computational fluid dynamics — simplified parametric approximations
- Stub the interface now, implement when clinical tools are mature

## What NOT To Build (Scope Control)

- Do NOT implement ARNI, MRA, or SGLT2i drug classes yet. Stub them.
- Do NOT build wearable device integration. Use JSON vitals data.
- Do NOT build real pharmacy API integration. Use the local formulary database.
- Do NOT build user authentication or multi patient support.
- Do NOT train any models. Use Gemini API for LLM and deterministic Python for everything clinical.
- Do NOT build TA2 yet. Build TA1 first. TA2 comes after TA1 works.
- Do NOT build custom ASR. Use Gemini's native audio understanding for voice biomarkers.
- Do NOT build custom CV models for edema/pill detection. Use Gemini Vision, validate against clinical grading scales.
- Do NOT build full computational fluid dynamics models. Use parametric approximations for digital twin.

## Testing

Every tool must have tests that verify:
- Returns valid Action Packet format
- Handles edge cases (missing data, extreme values)
- Follows guideline rules correctly
- Never returns a recommendation without a guideline citation
- Never returns a recommendation without monitoring requirements

Run tests with: `python -m pytest tests/`

## API Layer (`api/`)

FastAPI backend serving the React frontend. CORS configured for localhost:3000, 5173, 5174.

Key routes:
- `GET /api/health` - System status + Gemini API connectivity
- `GET /api/patients` - List all patients
- `POST /api/patients` - Create patient (onboarding)
- `GET /api/patients/{patient_id}` - Patient detail
- `POST /api/chat` - Process message through full pipeline (accepts text, audio, image)
- `WS /api/chat/ws` - WebSocket for voice (partially implemented)

Pipeline service (`api/services/pipeline_service.py`) wraps the orchestrator for API use. Audio (`api/services/audio.py`) and image (`api/services/image.py`) services are stubbed.

## React Frontend (`frontend/`)

Dual-view React SPA:
- **Patient View**: Chat interface with conversation graph visualization (orb)
- **Clinician View**: Dashboard with patient list, vitals charts, Action Packet cards, escalation alerts

State managed via `IrisContext` (React Context). API client in `frontend/src/api/client.ts`.

## Source Layout

```
src/orchestrator/pipeline.py     # 6-tool orchestrator (entry point for all clinical logic)
src/orchestrator/extractor.py    # Gemini signal extraction from patient messages
src/orchestrator/responder.py    # Gemini response generation from Action Packets
src/orchestrator/validator.py    # Hallucination blocker + no-hyphens enforcement
src/tools/adherence_monitor.py   # Refill timing + barrier detection
src/tools/trajectory_analyzer.py # Weight/BP/HR trend analysis
src/tools/gdmt_engine.py        # Diuretic + beta blocker titration rules
src/tools/safety_checker.py     # Drug interactions + lab safety checks
src/tools/barrier_planner.py    # Cost/access/literacy feasibility
src/tools/escalation_manager.py # Clinician alert triggers
src/utils/action_packet.py      # Action Packet creation + validation
src/utils/data_loader.py        # JSON data loading + patient persistence
data/drugs/heart_failure_drugs.json  # 20+ drugs with dosing, costs, interactions
data/mappings/alternatives.json      # Cheaper/accessible drug alternatives
tests/conftest.py               # 5 test patient fixtures (stable, decompensating, edge cases)
```

## Clinical Roadmap (Known Gaps)

Honest audit (2026-03-06) found architecture is 9/10 but clinical depth is 4/10. These are the specific improvements needed per tool:

### Trajectory Analyzer
- **Trend acceleration detection**: Rate of change of rate of change. A weight gain of 1 lb/day that's accelerating is more urgent than a stable 1 lb/day.
- **Clinical context awareness**: Recent med changes, infections, hospitalizations should modulate interpretation of trends.
- **Composite risk scoring**: Combine weight trend + BP trend + HR trend + voice biomarker scores into a single decompensation risk score, not just threshold-based alerts on individual vitals.
- **Voice biomarker integration**: Acoustic feature trends as additional decompensation signal.

### Adherence Monitor
- **Dose-level tracking**: Not just "refilled on time" but "taking correct dose at correct frequency."
- **Pattern detection**: Identify systematic patterns — skips weekends, stops after specific side effects, adherence drops during financial stress.
- **Medication complexity scoring**: 5 medications BID with specific timing requirements for a low-literacy patient = high non-adherence risk. Score this.
- **Silent non-disclosure detection**: Conversation pattern analysis to detect when patients aren't reporting problems.

### Safety Checker
- **Drug interaction cascades**: Triple interactions (spironolactone + ACEi + NSAID) are more dangerous than any pair. Check cascades, not just pairs.
- **Potassium rate-of-rise**: K+ of 5.1 rising from 4.2 in 3 days is more urgent than stable 5.1. Track velocity.
- **Acute kidney injury detection**: Creatinine jump > 0.3 mg/dL in 48 hours OR > 50% in 7 days (KDIGO criteria).
- **Digoxin toxicity checks**: Narrow therapeutic window, interaction with many HF drugs.

### Barrier Planner
- **Patient assistance program database**: Know which manufacturers offer PAPs and how to access them.
- **Behavioral economics nudges**: Pill organizers, SMS timing optimization, commitment devices, default effects.
- **Risk stratification**: Which barrier is most likely to cause non-adherence for THIS patient? Prioritize interventions.
- **Social determinant longitudinal tracking**: Track changes in social factors over time, not just snapshot.

### Escalation Manager
- **Routing to specific clinician types**: Cardiologist for medication decisions, nephrologist for renal concerns, social worker for access barriers, psychiatrist for depression screening.
- **Predictive escalation**: Trajectory will hit threshold in 2 weeks → escalate now instead of waiting for crisis.
- **30-day readmission risk scoring**: Composite score using HOSPITAL, LACE, or similar validated instrument.
- **Depression/mental health screening triggers**: PHQ-2 equivalent detection from conversation patterns.
