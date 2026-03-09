# Separate Patient and Clinician Views

Date: 2026-03-01
Made By: Architecture decision during Session 3
Reason: Patients should never see Action Packets, clinical reasoning, drug interaction alerts, or escalation triggers. Exposing this information could cause unnecessary anxiety and does not align with the care assistant role. Clinicians need full transparency for trust and oversight. Two separate routes enforce this separation at the UI level.
Impact: `/` route shows only the voice orb and spoken responses. `/clinician` route shows the 3 column dashboard with conversation monitor, patient data, and color coded Action Packets. Both routes hit the same API endpoints.
