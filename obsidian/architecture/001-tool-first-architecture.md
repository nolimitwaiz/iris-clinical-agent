# Tool First Architecture Decision

Date: 2026-02-27
Status: Decided

## Context

Clinical AI agents that use LLMs to generate medical recommendations risk hallucinating medications, doses, or clinical reasoning. In heart failure management, a hallucinated dose can be fatal. We needed an architecture that makes hallucination structurally impossible for clinical decisions, not just unlikely.

## Decision

The LLM never computes clinical decisions. It performs two functions: (1) extract structured information from patient messages, and (2) communicate tool outputs in natural language. All clinical reasoning flows through deterministic Python tools that implement published AHA/ACC guidelines. A Python orchestrator runs every tool in a fixed order every time. A Response Validator checks the LLM's output against Action Packets and blocks any hallucinated clinical content.

## Alternatives Considered

1. **LLM with function calling (LLM chooses tools):** Rejected because the LLM can skip tools, call them in wrong order, or fill gaps with its own knowledge.
2. **LLM with safety guardrails (prompt based):** Rejected because prompt instructions are not enforceable. The LLM can still hallucinate.
3. **Fully deterministic (no LLM):** Rejected because patient communication requires natural language understanding and generation that rule systems cannot match.
4. **Fine tuned clinical LLM:** Rejected because ARPA-H ISO explicitly says model training is out of scope. The hard problem is the system around the model.

## Consequences

- Clinical decisions are auditable and traceable to specific guideline citations
- Every tool output follows the Action Packet format for TA2 supervision
- The LLM layer can be swapped (Gemini, Claude, Llama) without affecting clinical logic
- Adding new drug classes means adding new tool functions, not retraining anything
- FDA regulatory pathway is simpler because clinical logic is in deterministic, testable tools
