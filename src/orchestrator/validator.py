"""Response Validator — checks LLM output against Action Packets for hallucinations."""

import re

# Known drug names for detection in text. Comprehensive list for heart failure.
KNOWN_DRUG_NAMES = [
    "furosemide", "lasix", "bumetanide", "bumex", "torsemide", "demadex",
    "carvedilol", "coreg", "metoprolol", "toprol", "metoprolol succinate",
    "lisinopril", "zestril", "prinivil", "enalapril", "vasotec",
    "ramipril", "altace",
    "losartan", "cozaar", "valsartan", "diovan",
    "sacubitril", "valsartan", "entresto", "sacubitril/valsartan",
    "spironolactone", "aldactone", "eplerenone", "inspra",
    "dapagliflozin", "farxiga", "empagliflozin", "jardiance",
    "potassium chloride", "potassium",
    "hydralazine", "isosorbide", "isosorbide dinitrate", "bidil",
    "digoxin", "lanoxin",
    "metolazone", "zaroxolyn",
    "amlodipine", "norvasc",
    "ivabradine", "corlanor",
    "warfarin", "coumadin",
    "aspirin",
    "vericiguat", "verquvo",
]


def _extract_drug_names_from_text(text: str) -> set[str]:
    """Find all known drug names mentioned in the text."""
    text_lower = text.lower()
    found = set()
    for drug in KNOWN_DRUG_NAMES:
        # Use word boundary matching
        pattern = r'\b' + re.escape(drug.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.add(drug.lower())
    return found


def _extract_doses_from_text(text: str) -> list[dict]:
    """Find all dose mentions in the text (e.g. '40mg', '40 mg', '3.125 mg')."""
    # Match patterns like: 40mg, 40 mg, 3.125mg, 3.125 mg
    pattern = r'(\d+(?:\.\d+)?)\s*mg'
    matches = re.finditer(pattern, text.lower())
    doses = []
    for m in matches:
        doses.append({
            "value": float(m.group(1)),
            "text": m.group(0),
        })
    return doses


def _build_allowed_set(packets: list[dict]) -> dict:
    """Build the set of allowed drug names and doses from Action Packets.

    Returns a dict with:
        - drug_names: set of allowed drug name strings (lowercase)
        - doses: set of allowed dose floats
        - drug_dose_pairs: set of (drug_name, dose) tuples
    """
    drug_names = set()
    doses = set()
    drug_dose_pairs = set()

    for packet in packets:
        drug = packet.get("drug")
        if drug:
            drug_lower = drug.lower()
            drug_names.add(drug_lower)
            # Also add common brand/generic aliases
            # The drug name from the packet is the primary reference

        current_dose = packet.get("current_dose_mg")
        new_dose = packet.get("new_dose_mg")

        if current_dose is not None:
            doses.add(float(current_dose))
            if drug:
                drug_dose_pairs.add((drug.lower(), float(current_dose)))
        if new_dose is not None:
            doses.add(float(new_dose))
            if drug:
                drug_dose_pairs.add((drug.lower(), float(new_dose)))

    return {
        "drug_names": drug_names,
        "doses": doses,
        "drug_dose_pairs": drug_dose_pairs,
    }


def _check_for_hyphens(text: str) -> list[str]:
    """Check for hyphens in text that should use spaces instead.

    Excludes hyphens that are part of drug names (e.g., sacubitril/valsartan)
    or common acceptable uses.
    """
    violations = []
    # Look for word-hyphen-word patterns (not drug names)
    hyphen_pattern = r'\b(\w+)-(\w+)\b'
    matches = re.finditer(hyphen_pattern, text)

    # Known acceptable hyphenated terms
    acceptable = {
        "sacubitril-valsartan",  # drug name variant
        "non-adherent",  # but we should use "non adherent" per rules
        "follow-up",  # should be "follow up"
        "long-term",  # should be "long term"
        "short-term",  # should be "short term"
    }

    for m in matches:
        full = m.group(0).lower()
        if full not in acceptable:
            violations.append(f"Hyphen found: '{m.group(0)}' — use spaces instead")

    # Actually per CLAUDE.md ALL hyphens in patient text should be spaces
    if '-' in text:
        # Find all hyphenated words
        all_hyphenated = re.findall(r'\b\w+-\w+\b', text)
        if all_hyphenated:
            violations = [
                f"Hyphen found: '{word}' — use spaces instead"
                for word in all_hyphenated
            ]

    return violations


def validate_response(
    draft: str,
    packets: list[dict],
    drug_db: list[dict] | None = None,
) -> dict:
    """Validate an LLM-generated response against Action Packets.

    Checks:
    1. Every drug name in the response exists in the Action Packets
    2. Every dose in the response exists in the Action Packets
    3. No hyphens in the text (use spaces instead)

    Args:
        draft: The LLM-generated response text.
        packets: List of Action Packets from the pipeline.
        drug_db: Optional drug database for additional name matching.

    Returns:
        A dict with:
            - approved: bool (True if response passes all checks)
            - response: str (the response text, possibly the draft or a note about rejection)
            - violations: list[str] (list of violation descriptions)
    """
    violations: list[str] = []

    allowed = _build_allowed_set(packets)

    # Check drug names
    mentioned_drugs = _extract_drug_names_from_text(draft)
    for drug in mentioned_drugs:
        if drug not in allowed["drug_names"]:
            # Check if it's a brand name for an allowed generic
            # Simple check: see if any allowed drug name contains this name
            is_related = False
            for allowed_drug in allowed["drug_names"]:
                if drug in allowed_drug or allowed_drug in drug:
                    is_related = True
                    break
            if not is_related:
                violations.append(
                    f"Drug '{drug}' mentioned in response but not found in Action Packets"
                )

    # Check doses
    mentioned_doses = _extract_doses_from_text(draft)
    for dose_info in mentioned_doses:
        dose_val = dose_info["value"]
        if dose_val not in allowed["doses"]:
            violations.append(
                f"Dose '{dose_info['text']}' mentioned in response but not found in Action Packets"
            )

    # Check for hyphens
    hyphen_violations = _check_for_hyphens(draft)
    violations.extend(hyphen_violations)

    approved = len(violations) == 0

    return {
        "approved": approved,
        "response": draft if approved else draft,
        "violations": violations,
    }


def validate_live_transcript(
    transcript: str,
    allowed_drugs: set[str] | None = None,
) -> dict:
    """Validate a Gemini Live transcript for hallucinated clinical content.

    Used on the Live voice path where the model may generate text without
    the pipeline running first. Checks that any drug/dose mentions are in
    the allowed set (from prior Action Packets). If no allowed set is given,
    any drug mention is flagged.

    Returns:
        A dict with:
            - clean: bool (True if no hallucination detected)
            - violations: list[str]
            - correction_message: str | None (user-friendly correction if needed)
    """
    violations: list[str] = []

    mentioned_drugs = _extract_drug_names_from_text(transcript)
    mentioned_doses = _extract_doses_from_text(transcript)

    if allowed_drugs is None:
        allowed_drugs = set()

    for drug in mentioned_drugs:
        if drug not in allowed_drugs:
            violations.append(f"Unverified drug mentioned: '{drug}'")

    if mentioned_doses and not allowed_drugs:
        for dose in mentioned_doses:
            violations.append(f"Unverified dose mentioned: '{dose['text']}'")

    clean = len(violations) == 0
    correction_message = None
    if not clean:
        correction_message = (
            "I may have misspoken. Please rely only on the information "
            "your care team has confirmed with you."
        )

    return {
        "clean": clean,
        "violations": violations,
        "correction_message": correction_message,
    }


def get_strict_regeneration_prompt(
    packets: list[dict],
    message: str,
    patient_name: str,
    literacy: str,
    violations: list[str],
) -> str:
    """Build a stricter prompt for regeneration after validation failure.

    Args:
        packets: Action Packets from the pipeline.
        message: Patient's original message.
        patient_name: Patient's first name.
        literacy: Health literacy level.
        violations: List of violations from the failed validation.

    Returns:
        A prompt string for Gemini regeneration.
    """
    import json

    allowed = _build_allowed_set(packets)

    packets_summary = json.dumps(
        [{"decision": p.get("decision"), "drug": p.get("drug"), "reason": p.get("reason"), "monitoring": p.get("monitoring")} for p in packets],
        indent=2,
    )

    return f"""You are a heart failure care assistant. Your previous response was rejected because it contained information not found in the clinical Action Packets. Generate a new response following these STRICT rules:

ALLOWED MEDICATIONS (ONLY mention these): {', '.join(sorted(allowed['drug_names'])) if allowed['drug_names'] else 'None'}
ALLOWED DOSES (ONLY use these numbers): {', '.join(str(d) + 'mg' for d in sorted(allowed['doses'])) if allowed['doses'] else 'None'}

VIOLATIONS FROM PREVIOUS ATTEMPT:
{chr(10).join('- ' + v for v in violations)}

RULES:
- Do NOT add ANY medication, dose, or clinical fact not listed above
- Do NOT use hyphens, use spaces instead (e.g. "follow up" not "follow-up")
- Be warm and empathetic
- Keep it concise (3 to 5 short paragraphs)
- Address the patient as {patient_name}

Action Packets: {packets_summary}
Patient message: {message}
Health literacy: {literacy}"""
