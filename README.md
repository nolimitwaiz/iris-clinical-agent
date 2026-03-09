# Iris Core — Tool First Heart Failure Care Agent

An autonomous heart failure care management agent where the AI never makes clinical decisions. Every medication recommendation comes from deterministic tools following AHA/ACC guidelines. The AI handles communication only.

## Quick Start

```bash
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
streamlit run app.py
```

## Architecture

See `docs/architecture/system_architecture.md` for the full architecture diagram.

The core principle: **the language model never makes clinical decisions.** It extracts patient input and communicates tool outputs. A Response Validator blocks any hallucinated clinical content.

## Project Philosophy

See `SOUL.md` for why this exists and what we believe.

## For Claude Code

See `CLAUDE.md` for complete build instructions, schemas, and rules.
