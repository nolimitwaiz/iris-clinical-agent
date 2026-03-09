# Multimodal Visual Sensing
Date: 2026-03-06
Status: Proposed

## Context
Current patient assessment relies entirely on structured data (vitals, labs) and text-based self-reporting. Visual assessment — a core part of every in-person clinical exam — is completely absent from remote monitoring. Smartphone cameras can bridge this gap.

## Research Findings

### Photo-Based Edema Detection
- Home foot-scanning predicted HF hospitalizations 13 days in advance
- Outperformed daily weight monitoring alone as a predictor
- Volumetric changes in feet/ankles detectable via smartphone photos
- Longitudinal comparison (today vs last week) more valuable than single assessment

### Medication Photo Verification
- AiCure: computer vision medication verification via smartphone
- Confirms correct medication, correct dose, and actual ingestion
- Moves adherence monitoring from "did you take it?" (self-report) to visual confirmation
- YOLOv5-based pill detection achieves real-time classification

### Scale Photo OCR
- Patients who have non-connected scales can photograph the display
- OCR extracts weight reading, eliminating manual entry errors
- Reduces friction for patients who struggle with apps or data entry

## Decision

Implement visual assessment as a new sensing modality. Photos submitted through the chat interface are processed for structured clinical data that feeds into existing deterministic tools.

### Visual Input Types
1. **Ankle/foot edema photos** — graded on clinical scale (0-4+), compared to prior photos, fed to trajectory analyzer
2. **Medication pill photos** — verified against patient's medication list, fed to adherence monitor
3. **Scale display photos** — OCR extracts weight value, fed to trajectory analyzer as vitals input
4. **Device site photos** — cardiac device implant sites checked for infection/inflammation signs, fed to escalation manager if concerning

### Implementation Approach
1. Use Gemini Vision capabilities for initial image analysis (no custom CV models)
2. Gemini extracts structured data from images (edema grade, pill identification, weight reading)
3. Structured data flows into existing tools through normal pipeline
4. All visual assessments generate Action Packets like any other clinical input
5. Image analysis is deterministic tool output — Gemini extracts features, Python tools make decisions

### Architecture Integration
```
Patient Photo Upload
      │
      ▼
[Image Analyzer] ── Gemini Vision extracts structured data:
      │              {edema_grade, pill_match, weight_reading, site_status}
      │
      ▼
[Python Orchestrator] ── structured data feeds existing tools
      │
      ├── edema_grade → Trajectory Analyzer
      ├── pill_match → Adherence Monitor
      ├── weight_reading → Trajectory Analyzer (as vitals)
      └── site_status → Escalation Manager
```

## Alternatives Considered
1. **Custom CV models (YOLOv5 for pills, U-Net for edema)**: Higher accuracy for specific tasks but requires training data, GPU infrastructure, and ongoing model maintenance. Rejected for MVP — Gemini Vision sufficient for initial validation.
2. **Third-party medical imaging APIs**: Exist for some use cases but add cost, latency, and external dependency. Rejected.
3. **Patient self-grading with visual guides**: Lower accuracy, higher patient burden. Keep as fallback if Gemini Vision accuracy is insufficient.

## Consequences
- Image upload already partially supported in API (`POST /api/chat` accepts image). Need to implement actual processing.
- Patient state model needs visual assessment history storage
- Need clinical validation of Gemini Vision edema grading against clinician ratings
- Photos require privacy/storage considerations (PHI in images)
- Dramatically improves assessment richness for remote patients
