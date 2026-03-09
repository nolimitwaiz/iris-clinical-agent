"""Barrier Planner tool.

Evaluates feasibility of safe medication changes based on patient social
factors including cost, access, and health literacy. Returns a list of
barrier Action Packets, one per safe change evaluated.
"""

from src.utils.action_packet import create_action_packet

TOOL_NAME = "barrier_planner"
GUIDELINE = "AHA/ACC 2022 HF Guideline Section 7.3.8"

# Cost thresholds per month by income bracket
COST_THRESHOLDS = {
    "low": 50.0,
    "medium": 100.0,
    "high": 200.0,
}


def _find_drug_in_db(drug_name: str, drug_db: list[dict]) -> dict | None:
    """Look up a drug by name in the drug database."""
    for entry in drug_db:
        if entry["drug_name"].lower() == drug_name.lower():
            return entry
    return None


def _find_alternatives(drug_name: str, alternatives: list[dict]) -> list[dict]:
    """Find all alternative drug entries for a given primary drug."""
    results = []
    for alt in alternatives:
        if alt["primary_drug"].lower() == drug_name.lower():
            results.append(alt)
    return results


def _get_drug_cost(drug_entry: dict, insurance_tier: str) -> float | None:
    """Get the monthly cost of a drug for a given insurance tier."""
    cost_map = drug_entry.get("cost_per_month", {})
    return cost_map.get(insurance_tier)


def plan_barriers(
    safe_changes: list[dict],
    patient: dict,
    drug_db: list[dict],
    alternatives: list[dict],
    signals: dict | None = None,
) -> list[dict]:
    """Evaluate feasibility of safe medication changes based on patient social factors.

    Args:
        safe_changes: List of Action Packets that passed safety checking
            (those with decision != "blocked").
        patient: Patient data dictionary following the Patient Data Schema.
        drug_db: List of drug database entries.
        alternatives: List of alternative drug mapping entries.
        signals: Optional extracted signals from the LLM extractor containing
            barriers_mentioned from the patient's message.

    Returns:
        A list of barrier Action Packets, one per safe change evaluated.
    """
    results: list[dict] = []
    signals = signals or {}

    social = patient.get("social_factors", {})
    insurance_tier = social.get("insurance_tier", "uninsured")
    income_bracket = social.get("income_bracket", "medium")
    lives_alone = social.get("lives_alone", False)
    works_nights = social.get("works_nights", False)
    health_literacy = social.get("health_literacy", "moderate")
    pharmacy_distance = social.get("pharmacy_distance_miles", 0.0)

    cost_threshold = COST_THRESHOLDS.get(income_bracket, 100.0)

    # Collect barriers mentioned by the patient in their message
    patient_reported_barriers = signals.get("barriers_mentioned", [])

    for packet in safe_changes:
        drug_name = packet.get("drug")
        decision = packet.get("decision", "")

        barriers: list[str] = []
        social_notes: list[str] = []
        monitoring_notes: list[str] = []
        alternative_info: str | None = None
        requires_safety_recheck = False
        has_cost_barrier = False

        # ── Cost barrier check ───────────────────────────────────────────
        if drug_name:
            db_entry = _find_drug_in_db(drug_name, drug_db)
            if db_entry:
                monthly_cost = _get_drug_cost(db_entry, insurance_tier)
                if monthly_cost is not None and monthly_cost > cost_threshold:
                    has_cost_barrier = True
                    barriers.append(
                        f"{drug_name} costs ${monthly_cost:.0f} per month "
                        f"which exceeds the ${cost_threshold:.0f} threshold "
                        f"for {income_bracket} income patients"
                    )

                    # Look for cheaper alternatives
                    alts = _find_alternatives(drug_name, alternatives)
                    for alt in alts:
                        alt_db = _find_drug_in_db(alt["alternative_drug"], drug_db)
                        if alt_db:
                            alt_cost = _get_drug_cost(alt_db, insurance_tier)
                            if alt_cost is not None and alt_cost <= cost_threshold:
                                alternative_info = (
                                    f"Consider {alt['alternative_drug']} as a lower cost "
                                    f"alternative at ${alt_cost:.0f} per month. "
                                    f"{alt.get('clinical_notes', '')}"
                                )
                                requires_safety_recheck = alt.get(
                                    "requires_safety_recheck", False
                                )
                                break

                    if alternative_info:
                        barriers.append(alternative_info)
                        if requires_safety_recheck:
                            monitoring_notes.append(
                                "Alternative requires safety recheck before prescribing"
                            )

        # ── Patient-reported barriers from conversation ─────────────────
        if patient_reported_barriers:
            for prb in patient_reported_barriers:
                barriers.append(f"Patient reports: {prb}")

        # ── Social barrier checks ────────────────────────────────────────
        if lives_alone:
            social_notes.append(
                "Patient lives alone, recommend more frequent check ins"
            )

        if works_nights:
            social_notes.append(
                "Patient works nights, adjust dosing schedule to accommodate"
            )

        if health_literacy == "low":
            social_notes.append(
                "Patient has low health literacy, use simplified instructions"
            )

        if pharmacy_distance > 5:
            social_notes.append(
                f"Pharmacy is {pharmacy_distance} miles away, consider mail order pharmacy"
            )

        # ── Combine barriers and social notes ────────────────────────────
        all_barriers = barriers + social_notes

        if all_barriers:
            barrier_decision = "barrier_identified"
            reason = ". ".join(all_barriers)
            if not monitoring_notes:
                monitoring_notes.append(
                    "Follow up in 2 weeks to assess barrier resolution and medication adherence"
                )
        else:
            barrier_decision = "feasible"
            reason = f"No cost or social barriers identified for {drug_name or 'proposed change'}"
            monitoring_notes.append("Standard follow up per protocol")

        monitoring_str = ". ".join(monitoring_notes)

        results.append(create_action_packet(
            tool_name=TOOL_NAME,
            decision=barrier_decision,
            reason=reason,
            guideline=GUIDELINE,
            confidence="moderate",
            risk_of_inaction=(
                "Unaddressed barriers may lead to medication non adherence "
                "and clinical deterioration"
            ),
            inputs_used={
                "drug": drug_name,
                "proposed_decision": decision,
                "insurance_tier": insurance_tier,
                "income_bracket": income_bracket,
                "cost_threshold": cost_threshold,
                "has_cost_barrier": has_cost_barrier,
                "alternative_suggested": alternative_info,
                "requires_safety_recheck": requires_safety_recheck,
                "social_barriers": social_notes if social_notes else [],
            },
            drug=drug_name,
            current_dose_mg=packet.get("current_dose_mg"),
            new_dose_mg=packet.get("new_dose_mg"),
            monitoring=monitoring_str,
        ))

    return results
