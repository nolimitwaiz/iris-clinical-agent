# Behavioral Intelligence Architecture
Date: 2026-03-06
Status: Proposed

## Context
Current adherence monitoring is limited to refill timing and self-reported barriers. This misses the fundamental question: WHY does a patient not adhere? Without understanding the behavioral root cause, interventions are generic and often ineffective. A patient who can't afford medication needs a different response than one who doesn't believe medication helps.

## Research Findings

### COM-B Model (Michie et al.)
Framework for diagnosing behavior:
- **Capability**: Physical ability + psychological knowledge to perform the behavior
- **Opportunity**: Physical access + social environment supporting the behavior
- **Motivation**: Reflective (beliefs, intentions) + automatic (habits, emotions) drivers

Each non-adherent behavior maps to one or more COM-B deficits, which map to specific intervention types. This replaces "patient is non-adherent" with "patient lacks capability (doesn't understand dosing schedule) and opportunity (pharmacy is 12 miles away)."

### Transtheoretical Model (Prochaska & DiClemente)
Stages of change for each target behavior:
1. **Precontemplation**: Not aware or not considering change. Patient doesn't see the problem.
2. **Contemplation**: Aware of the problem, considering change but ambivalent.
3. **Preparation**: Intending to act soon, may be taking small steps.
4. **Action**: Actively making the change. High risk of relapse.
5. **Maintenance**: Sustained change (6+ months). Focus on preventing relapse.

Critical insight: pushing action-stage interventions on precontemplation-stage patients backfires. It increases resistance. Stage-matched communication is essential.

### AI Motivational Interviewing
- JMIR 2025 scoping review: only 15 studies worldwide on AI-driven motivational interviewing
- Dartmouth RCT: 51% depression reduction from generative AI therapeutic conversations
- Clare chatbot: formed therapeutic alliance in 3-5 days
- AHRQ research: reinforcement learning adapted messaging improves adherence by learning which message types work for each individual patient
- Key finding: the AI doesn't need to be a therapist — it needs to match its communication to the patient's readiness

## Decision

Implement a behavioral state machine that tracks each patient's COM-B profile and stage of change per behavior, and adapts communication strategy accordingly.

### Behavioral State Machine Design
```python
{
    "patient_id": str,
    "behaviors": {
        "medication_adherence": {
            "stage": "contemplation",  # precontemplation|contemplation|preparation|action|maintenance
            "com_b": {
                "capability": {"physical": "adequate", "psychological": "low"},
                "opportunity": {"physical": "limited", "social": "supportive"},
                "motivation": {"reflective": "ambivalent", "automatic": "no_habit"}
            },
            "barrier_inventory": [
                {"barrier": "cost", "severity": "high", "resolved": false, "interventions_tried": ["generic_switch"]},
                {"barrier": "side_effects", "severity": "moderate", "resolved": false, "interventions_tried": []}
            ],
            "intervention_history": [
                {"type": "education", "date": "2026-02-15", "response": "engaged"},
                {"type": "cost_assistance", "date": "2026-02-20", "response": "followed_through"}
            ]
        },
        "daily_weight": {
            "stage": "preparation",
            "com_b": {...},
            "barrier_inventory": [...],
            "intervention_history": [...]
        }
    }
}
```

### Stage-Aware Response Generation
The LLM responder prompt adapts based on detected stage:
- **Precontemplation**: Build awareness. Share information without pressure. "Many people with heart failure find that..."
- **Contemplation**: Explore ambivalence. Acknowledge difficulty. "It sounds like you have mixed feelings about..."
- **Preparation**: Support planning. Make it concrete. "What would make it easier to..."
- **Action**: Reinforce and troubleshoot. "You have been doing great with... Let's talk about what happened when..."
- **Maintenance**: Celebrate and prevent relapse. "You have kept this up for weeks now. That takes real commitment."

### Implementation Approach
1. Stage detection via LLM extraction from conversation patterns (not single messages)
2. COM-B assessment updated by barrier planner tool based on conversation history
3. Behavioral state stored in patient data, evolves over time
4. Response generation prompts include stage-appropriate communication guidance
5. All behavioral assessments are probabilistic — the tools still make deterministic clinical decisions

## Alternatives Considered
1. **Simple barrier checklist**: Current approach. Too shallow — doesn't distinguish "I forgot" from "I chose not to." Rejected as insufficient.
2. **Full RL-based message optimization**: Ideal but requires significant training data and infrastructure. Deferred — start with rule-based stage matching, add RL later.
3. **Clinician-assessed behavioral state**: Most accurate but defeats purpose of autonomous agent. Keep as validation mechanism.

## Consequences
- Patient data schema expands with behavioral layer
- Barrier planner tool becomes significantly more sophisticated
- LLM extraction prompt needs behavioral signal detection
- Response generation becomes stage-aware (new prompt templates per stage)
- Enables genuinely personalized care — not just clinically personalized but behaviorally personalized
- Intervention effectiveness tracking creates learning loop over time
