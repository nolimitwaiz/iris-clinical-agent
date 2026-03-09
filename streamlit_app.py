"""Iris Core — Heart Failure Care Agent

Streamlit entry point. Provides a 3-column layout:
  Left:   Patient Dashboard (demographics, meds, labs, weight chart)
  Center: Chat Interface (patient selector, conversation)
  Right:  Transparency Panel (Action Packets, clinical reasoning)
"""

import streamlit as st

from src.utils.data_loader import load_drug_database, load_alternatives
from src.frontend.patient_dashboard import render_patient_dashboard
from src.frontend.chat_interface import render_chat_interface
from src.frontend.transparency_panel import render_transparency_panel

st.set_page_config(
    page_title="Iris Core",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for cleaner layout
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    [data-testid="stChatMessage"] { font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("# Iris Core")
st.caption("Tool first heart failure care agent | Every clinical decision from deterministic Python")


@st.cache_data
def _load_drug_db():
    return load_drug_database()


@st.cache_data
def _load_alternatives():
    return load_alternatives()


drug_db = _load_drug_db()
alternatives = _load_alternatives()

# Tab layout (works on mobile and desktop)
tab_chat, tab_patient, tab_reasoning = st.tabs(["Chat", "Patient", "Reasoning"])

with tab_chat:
    render_chat_interface(drug_db, alternatives)

with tab_patient:
    patient = st.session_state.get("current_patient")
    packets = st.session_state.get("current_packets")
    if patient:
        render_patient_dashboard(patient, packets)
    else:
        st.info("Select a patient in the Chat tab first")

with tab_reasoning:
    packets = st.session_state.get("current_packets")
    render_transparency_panel(packets)
