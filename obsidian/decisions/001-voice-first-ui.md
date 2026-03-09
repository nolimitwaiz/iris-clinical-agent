# Voice First UI for Patient Interaction

Date: 2026-03-01
Made By: Architecture decision during Session 3
Reason: Heart failure patients are often elderly, may have low health literacy, and may find typing on screens difficult. Voice is the most natural and accessible interface for this population. ARPA-H demo also needs a clear visual differentiator from text chat UIs.
Impact: Built React frontend with radial node orb as primary interaction. Text input preserved as secondary fallback. Patient view shows zero clinical data. Clinician view remains a full dashboard on a separate route.
