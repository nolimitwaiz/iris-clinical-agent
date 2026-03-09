"""Chat Interface component for the Streamlit frontend.

Handles patient selection, message input, conversation display,
and orchestrates the pipeline execution.
"""

import os

import streamlit as st

from src.utils.data_loader import load_patient
from src.orchestrator.extractor import extract_signals
from src.orchestrator.responder import generate_response
from src.orchestrator.validator import validate_response, get_strict_regeneration_prompt
from src.orchestrator.pipeline import run_pipeline


def _has_api_key() -> bool:
    """Check if a Gemini API key is available."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(key)


PATIENT_OPTIONS = {
    "001": "Maria Santos (67F, Stable, BB Uptitration)",
    "002": "James Mitchell (72M, Weight Gain, Congestion)",
    "003": "Robert (58M, Kidney Decline, Safety Alerts)",
    "004": "Susan (63F, Cost Barriers, Non Adherent)",
    "005": "David (78M, Critical, Urgent Escalation)",
}

MAX_VALIDATION_RETRIES = 2


def _initialize_session_state():
    """Set up session state defaults."""
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "selected_patient_id" not in st.session_state:
        st.session_state.selected_patient_id = "001"
    if "current_packets" not in st.session_state:
        st.session_state.current_packets = None
    if "current_patient" not in st.session_state:
        st.session_state.current_patient = None


def _process_message(message: str, patient: dict, drug_db: list, alternatives: list):
    """Process a patient message through the full pipeline.

    Returns (response_text, packets, validation_result).
    """
    # Step 1: Extract signals with LLM
    signals = extract_signals(message)

    # Step 2: Run deterministic pipeline
    packets = run_pipeline(patient, signals, drug_db, alternatives)

    # Step 3: Generate response with LLM
    draft = generate_response(packets, message, patient)

    # Step 4: Validate response
    result = validate_response(draft, packets)

    if result["approved"]:
        return draft, packets, result

    # In demo mode (no API key), skip retries since response is deterministic
    if not _has_api_key():
        return draft, packets, result

    # Retry with stricter prompt if validation fails
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    patient_name = patient.get("name", "there").split()[0]
    literacy = patient.get("social_factors", {}).get("health_literacy", "moderate")

    for _ in range(MAX_VALIDATION_RETRIES):
        strict_prompt = get_strict_regeneration_prompt(
            packets, message, patient_name, literacy, result["violations"]
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=[strict_prompt]
            )
            draft = response.text.strip()
        except Exception:
            break

        result = validate_response(draft, packets)
        if result["approved"]:
            return draft, packets, result

    # If still not approved, return with violations noted
    return draft, packets, result


def render_chat_interface(drug_db: list, alternatives: list):
    """Render the chat interface in the center column.

    Args:
        drug_db: Drug database list.
        alternatives: Alternative drug mappings list.
    """
    _initialize_session_state()

    st.markdown("### Iris Care Chat")

    # API key status
    if not _has_api_key():
        st.info(
            "Running in **demo mode** (no Gemini API key). "
            "Clinical tools work fully. Chat responses are deterministic summaries. "
            "Add your key to `.env` for natural language responses."
        )

    # Patient selector
    patient_id = st.selectbox(
        "Select Patient",
        options=list(PATIENT_OPTIONS.keys()),
        format_func=lambda x: PATIENT_OPTIONS[x],
        key="patient_selector",
    )

    # Handle patient change
    if patient_id != st.session_state.selected_patient_id:
        st.session_state.selected_patient_id = patient_id
        st.session_state.conversation_history = []
        st.session_state.current_packets = None

    # Load patient data
    patient = load_patient(patient_id)
    st.session_state.current_patient = patient

    # Display conversation history
    for turn in st.session_state.conversation_history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn["role"] == "assistant" and turn.get("violations"):
                st.warning(
                    f"Validation issues detected ({len(turn['violations'])}). "
                    "Some content may not be fully verified."
                )

    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.conversation_history.append({
            "role": "user",
            "content": prompt,
        })

        # Process and display response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your message..."):
                response_text, packets, validation = _process_message(
                    prompt, patient, drug_db, alternatives
                )
                st.session_state.current_packets = packets
                st.markdown(response_text)

                if not validation["approved"]:
                    st.warning(
                        f"Validation issues detected ({len(validation['violations'])}). "
                        "Some content may not be fully verified."
                    )

        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response_text,
            "violations": validation.get("violations", []),
        })

        # Rerun to update the dashboard and transparency panel
        st.rerun()
