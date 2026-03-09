"""Patient Dashboard component for the Streamlit frontend.

Displays patient demographics, medications, labs, weight chart,
risk level, and social factors in the left column.
"""

import streamlit as st
import pandas as pd


def render_patient_dashboard(patient: dict, packets: list[dict] | None = None):
    """Render the patient dashboard in the left column.

    Args:
        patient: Patient data dictionary.
        packets: Optional list of Action Packets from the latest pipeline run.
    """
    st.markdown("### Patient Overview")

    # Demographics
    name = patient.get("name", "Unknown")
    age = patient.get("age", "?")
    sex = patient.get("sex", "?")
    ef = patient.get("ejection_fraction", 0)
    nyha = patient.get("nyha_class", "?")

    st.markdown(f"**{name}**")
    st.markdown(f"{age}y {sex} | EF {ef*100:.0f}% | NYHA {nyha}")

    # Risk level from trajectory
    if packets:
        traj = [p for p in packets if p.get("tool_name") == "trajectory_analyzer"]
        if traj:
            risk = traj[0].get("decision", "unknown")
            risk_colors = {
                "low": "🟢",
                "moderate": "🟡",
                "high": "🟠",
                "critical": "🔴",
            }
            icon = risk_colors.get(risk, "⚪")
            st.markdown(f"**Risk Level:** {icon} {risk.upper()}")

    st.divider()

    # Medications table
    st.markdown("#### Current Medications")
    meds = patient.get("medications", [])
    if meds:
        med_data = []
        for med in meds:
            freq = med.get("frequency_per_day", 1)
            freq_str = f"{freq}x/day" if freq > 1 else "daily"
            med_data.append({
                "Drug": med["drug"],
                "Dose": f"{med['dose_mg']}mg",
                "Frequency": freq_str,
            })
        st.dataframe(
            pd.DataFrame(med_data),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No medications on record")

    st.divider()

    # Latest labs
    st.markdown("#### Latest Labs")
    labs = patient.get("labs", {})
    lab_display = {
        "potassium": ("K+", "mEq/L"),
        "creatinine": ("Cr", "mg/dL"),
        "egfr": ("eGFR", "mL/min"),
        "bnp": ("BNP", "pg/mL"),
        "sodium": ("Na+", "mEq/L"),
    }

    cols = st.columns(3)
    col_idx = 0
    for lab_name, (label, unit) in lab_display.items():
        readings = labs.get(lab_name, [])
        if readings:
            sorted_readings = sorted(readings, key=lambda r: r["date"])
            latest = sorted_readings[-1]
            with cols[col_idx % 3]:
                st.metric(
                    label=label,
                    value=f"{latest['value']}",
                    help=f"{unit} ({latest['date']})",
                )
            col_idx += 1

    st.divider()

    # Weight chart
    st.markdown("#### 30 Day Weight Trend")
    weight_readings = patient.get("vitals", {}).get("weight_kg", [])
    if weight_readings:
        sorted_weights = sorted(weight_readings, key=lambda r: r["date"])
        weight_df = pd.DataFrame(sorted_weights)
        weight_df["date"] = pd.to_datetime(weight_df["date"])
        weight_df = weight_df.set_index("date")
        st.line_chart(weight_df["value"], y_label="Weight (kg)")
    else:
        st.info("No weight data available")

    st.divider()

    # Social factors
    st.markdown("#### Social Factors")
    social = patient.get("social_factors", {})
    insurance = social.get("insurance_tier", "unknown").replace("_", " ").title()
    literacy = social.get("health_literacy", "unknown").title()
    lives_alone = "Yes" if social.get("lives_alone", False) else "No"
    pharmacy = social.get("pharmacy_distance_miles", "?")

    st.markdown(f"**Insurance:** {insurance}")
    st.markdown(f"**Literacy:** {literacy}")
    st.markdown(f"**Lives Alone:** {lives_alone}")
    st.markdown(f"**Pharmacy:** {pharmacy} miles")
