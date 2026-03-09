# FDA Regulatory Pathway for Iris
Date: 2026-03-06
Status: Proposed

## Context
Iris Core autonomously recommends medication changes (diuretic titration, beta blocker uptitration). Under FDA guidance, this constitutes a medical device — specifically, Clinical Decision Support (CDS) software that does not meet the exemption criteria because it acts autonomously rather than presenting information for clinician review.

## Regulatory Landscape

### FDA CDS Guidance (January 2026)
- Updated guidance clarifies: software that makes autonomous clinical recommendations without requiring clinician review IS a medical device
- Four Bona Fide criteria for CDS exemption — Iris fails criterion 3 (must allow clinician independent review before action) because Iris acts without waiting for clinician approval on routine titrations
- This is expected and by design — the whole point is autonomous management

### Classification Pathway
- **De Novo classification required**: No predicate device exists for an autonomous patient-facing medication management agent
- De Novo creates a new regulatory classification that subsequent devices can reference
- Expected classification: Class II medical device with special controls
- ADVOCATE program timeline (39 months) includes regulatory pathway development

### PCCP (Predetermined Change Control Plan)
- FDA framework allowing pre-authorized algorithm updates
- Manufacturer specifies in advance what types of changes will be made and how they'll be validated
- Critical for Iris: clinical rules will be refined as evidence accumulates
- Example: "Updates to diuretic titration thresholds based on outcomes data, validated against the following test suite..."
- Avoids full re-submission for every algorithm improvement

### FDA MDDT (Medical Device Development Tool)
- ARPA-H ADVOCATE specifically targets MDDT qualification
- MDDT allows the tool (and its evaluation methodology) to be used by other companies
- TA2 (Iris Sentinel) as MDDT = every clinical AI company can use Iris Sentinel for safety validation
- This is the long-term business model: Sentinel becomes the standard supervisory layer

## Iris Architecture for FDA Compliance

### Action Packet Audit Trail
Every clinical recommendation traces to:
1. **Specific patient inputs** (vitals, labs, reported symptoms) — captured in `inputs_used`
2. **Specific guideline citation** — captured in `guideline` field (e.g., "AHA/ACC 2022 HF Guideline 7.3.2")
3. **Deterministic decision path** — Python if/else logic, not model inference
4. **Confidence assessment** — captured in `confidence` field
5. **Risk of inaction** — captured in `risk_of_inaction` field

No black box decisions. Every recommendation is reproducible given the same inputs.

### Response Validation as Safety Control
- Response Validator blocks any LLM-generated content not sourced from Action Packets
- This is a software safety control equivalent to a hardware interlock
- FDA will want evidence this works reliably — test suite must demonstrate hallucination blocking

### Escalation as Safety Boundary
- Escalation Manager defines when autonomous operation stops and clinician involvement begins
- Clear, deterministic criteria (e.g., eGFR < 15, potassium > 5.5, rapid decompensation)
- FDA will want these boundaries well-defined and validated

## ARPA-H ADVOCATE Context
- Program creates regulatory precedent for autonomous clinical AI
- 39-month timeline includes: development, clinical validation, FDA engagement
- Iris architecture designed from day one for this pathway
- Action Packets, Response Validator, and Escalation Manager are not just good engineering — they are regulatory requirements implemented as code

## Consequences
- All clinical tools must maintain complete audit trails (already implemented via Action Packets)
- Test suites must be comprehensive enough to serve as regulatory validation evidence
- Algorithm changes must be documented in a way compatible with PCCP submissions
- Clinical rules must cite specific guideline sections (already required in CLAUDE.md)
- TA2 design must anticipate MDDT qualification requirements
