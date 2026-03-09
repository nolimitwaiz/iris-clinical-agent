# FastAPI Wraps Existing Pipeline, Does Not Replace

Date: 2026-03-01
Made By: Architecture decision during Session 3
Reason: The clinical pipeline (6 tools, 81 tests) is the core value of the system. Modifying it to fit a web framework would risk introducing bugs in safety critical code. The FastAPI layer is a thin HTTP translation that calls `run_pipeline()` the same way the Streamlit chat interface does.
Impact: Zero changes to `src/tools/`, `src/orchestrator/pipeline.py`, `src/orchestrator/validator.py`, or `src/utils/`. All 81 tests pass without modification. Streamlit app preserved as fallback. Two frontends can coexist.
