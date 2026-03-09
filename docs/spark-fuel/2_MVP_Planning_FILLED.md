# MVP PLANNING — Worksheet 2

**Founder Name:** Waiz Khan
**Venture Name:** Iris Health
**Venture Description:** Iris is an AI powered heart failure care agent that provides 24/7 patient monitoring and medication optimization. It uses a tool first architecture where every clinical decision comes from deterministic Python tools following AHA/ACC guidelines — the language model never makes clinical decisions, only extracts patient information and communicates tool outputs. A Response Validator blocks any hallucinated clinical content. Iris monitors weight trends, optimizes GDMT medications, detects barriers to adherence, predicts decompensation, and escalates to clinicians when needed. It features a voice first interface, clinician dashboard with transparent clinical reasoning (Action Packets), and runs entirely locally with no paid APIs.

---

## 1. What is the core value that your product delivers to customers? Summarize it in one sentence.

Iris provides continuous, guideline concordant heart failure monitoring and medication optimization between clinic visits, catching decompensation early and reducing preventable hospitalizations.

---

## 2. When your product is complete, what are the features it'll have that will deliver this value? List the 5 most important features below.

1. **Deterministic Clinical Pipeline** — 6 tool pipeline (Adherence Monitor, Trajectory Analyzer, GDMT Engine, Safety Checker, Barrier Planner, Escalation Manager) that runs every patient interaction, producing structured Action Packets with guideline citations
2. **Voice First Patient Interface** — patients check in via natural conversation (voice or text), and Iris responds with warm, plain language explanations of their care status
3. **Clinician Dashboard** — real time view of patient panels with Action Packet transparency, escalation alerts, and projected outcome trajectories so clinicians can review and override AI recommendations
4. **Barrier Aware Planning** — every recommendation accounts for the patient's insurance tier, pharmacy distance, health literacy, and income bracket — a perfect prescription that never gets filled helps nobody
5. **Predictive Trajectory Analysis** — linear extrapolation of weight, blood pressure, and heart rate trends with 30 day projections showing "with action" vs "no action" outcomes

**The 1 to 2 most important features and why:**

The Deterministic Clinical Pipeline is the most critical — it is the architectural foundation that makes everything else safe. Without it, Iris would be another chatbot hallucinating medical advice. The tool first design is what makes Iris clinically credible and fundable. Second is the Voice First Patient Interface because accessibility drives adoption — many HF patients are elderly with limited tech literacy, and voice interaction removes the barrier to daily check ins.

---

## 3. Out of the five types of MVPs described, which one makes most sense for your venture? Why?

A **Single Feature MVP** (functional prototype) makes the most sense. Heart failure care is safety critical — you cannot use a landing page MVP or wizard-of-oz MVP when the product makes clinical recommendations. We need a working system that demonstrates the actual tool first architecture processing real clinical scenarios to build trust with clinicians, satisfy regulatory requirements, and prove to ARPA-H reviewers that the approach works. The prototype must show real guideline concordant decision making, not mockups.

---

## 4. What will an MVP look like for your product?

The MVP is a **working web application** (already built) with:

- **Patient facing view:** Voice and text interface with an animated orb visualization. Patient speaks or types a check in ("I gained 3 pounds this week and I'm feeling short of breath"). Iris processes this through the full 6 tool pipeline and responds with validated, guideline based guidance.
- **Clinician facing view:** Dashboard showing patient list, conversation history, Action Packets from each pipeline tool (with decision, drug, dose, guideline citation, confidence, risk of inaction), escalation alerts, and projected outcome trajectories.
- **Clinical network graph:** Visual representation of clinical reasoning — patients can double tap the orb to see how their message was processed, which tools made which decisions, and why.
- **5 test patients:** Realistic HF patient profiles covering stable management, acute decompensation, medication titration, barrier discovery, and edge cases (renal impairment, hyperkalemia).
- **97 automated tests:** Verifying every tool returns valid Action Packets, follows guideline rules correctly, handles edge cases, and never recommends without a citation.

**Not in the MVP:** Real EHR integration (FHIR export is a bridge), multi patient authentication, wearable device data, TA2 supervisory agent, ARNI/MRA/SGLT2i drug classes (stubbed).

---

## 5. What resources will you need to build this MVP?

**Tools (software):**
- Python 3.11+ with FastAPI (backend) — free
- React 19 + TypeScript + Vite (frontend) — free
- Gemini 2.0 Flash API for LLM extraction/response (free tier) — free
- JSON files for patient data and drug database — no database costs
- Claude Code for development assistance
- GitHub for version control

**Manpower (skills + time):**
- 1 full stack developer (me) — Python backend, React frontend, clinical guideline implementation
- Clinical advisor (cardiologist) for guideline validation — 2 to 4 hours/month
- Total development time: ~4 weeks for core MVP (already complete)

**Funds (money needed to get it live):**
- $0 for the prototype — runs entirely locally with free APIs
- $50 to $100/month for cloud hosting when ready for pilot deployment (DigitalOcean or similar)
- $500 to $2,000 for FDA regulatory consultation (if pursuing formal classification)
- $0 to $5,000 for initial pilot infrastructure depending on health system requirements
