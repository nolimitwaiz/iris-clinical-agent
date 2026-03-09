# Voice Biomarkers for Heart Failure Detection
Date: 2026-03-06
Status: Proposed

## Context
Current trajectory analysis relies on patient-reported vitals (weight, BP, HR) and lab values. Patients often fail to report symptoms or don't recognize early decompensation signs. Voice biomarkers offer a passive sensing modality — clinical data extracted from normal conversation without requiring any extra effort from the patient.

## Research Findings

### AHF-Voice Study
- 88% of hospitalized ADHF patients showed measurable speech changes
- 98% accuracy discriminating wet vs dry states
- Speech measures changed before clinical recognition of decompensation
- Source: Acute Heart Failure Voice biomarker study

### AHA Systematic Review (Circulation: Heart Failure)
- 27 acoustic features correlate with BNP (B-type natriuretic peptide) levels
- Features include: speaking rate, pause frequency, pause duration, jitter, shimmer, breathlessness indicators, vocal tremor, harmonic-to-noise ratio
- Correlation strengthens with higher BNP levels (more severe fluid overload)

### Key Acoustic Features for HF Detection
1. **Speaking rate** — decreases with dyspnea and fatigue
2. **Pause patterns** — longer and more frequent pauses indicate breathlessness
3. **Vocal tremor** — increases with cardiac decompensation
4. **Jitter/shimmer** — voice quality measures affected by fluid in airways
5. **Breathlessness indicators** — audible respiratory effort during speech
6. **Harmonic-to-noise ratio** — degrades with airway fluid

## Decision

Implement voice biomarker extraction as a passive analysis layer during voice conversations with Iris. Extracted features feed into the trajectory analyzer as additional clinical signals.

### Implementation Approach
1. Use Gemini's native audio understanding capabilities for initial feature extraction (no custom ASR needed)
2. Extract structured acoustic feature scores from each voice interaction
3. Feed scores as additional input to the trajectory analyzer tool
4. Trajectory analyzer combines voice biomarker trends with vitals/weight trends for composite risk scoring
5. Voice biomarkers alone are NOT diagnostic — they are one signal among many

### Architecture Integration
```
Voice Conversation
      │
      ├── [LLM Extractor] ── extracts patient message content (existing)
      │
      └── [Voice Biomarker Analyzer] ── extracts acoustic features (new)
              │
              ▼
      [Trajectory Analyzer] ── incorporates voice scores into trend analysis
```

## Alternatives Considered
1. **Custom ASR + acoustic analysis pipeline**: More accurate but requires training data, ML infrastructure, and maintenance. Rejected for MVP — Gemini's native audio capabilities are sufficient for initial validation.
2. **Wearable-based voice monitoring**: Continuous monitoring via smartwatch. Out of scope per CLAUDE.md — no wearable integration.
3. **Separate voice analysis API**: Third-party service for acoustic analysis. Rejected — adds dependency, cost, and latency.

## Consequences
- Trajectory analyzer tool needs new input fields for voice biomarker scores
- Patient state model needs voice biomarker history storage
- Voice conversations become clinically richer than text conversations (expected)
- Need to validate Gemini's acoustic feature extraction accuracy against clinical benchmarks
- Adds passive clinical measurement without any patient burden
