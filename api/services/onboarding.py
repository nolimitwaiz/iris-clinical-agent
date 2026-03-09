"""Conversational onboarding state machine.

Guides new patients through structured data collection via natural conversation.
Each step has a prompt template and extraction schema.
Uses Gemini to extract structured data from natural speech.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

ONBOARDING_STEPS = [
    {
        "step": "greeting",
        "prompt": "Welcome the patient warmly. Tell them you are Iris, their heart failure care assistant, and you would like to get to know them. Ask for their first and last name.",
        "extract_key": None,
        "confirm": None,
    },
    {
        "step": "name",
        "prompt": "The patient just told you their name. Confirm it and ask how old they are.",
        "extract_key": "name",
        "confirm": "I heard your name is {value}, is that right?",
    },
    {
        "step": "age",
        "prompt": "The patient told you their age. Confirm it and ask about their sex (male or female) for medical records.",
        "extract_key": "age",
        "confirm": "Got it, you are {value} years old. ",
    },
    {
        "step": "sex",
        "prompt": "The patient told you their sex. Confirm and ask if they have been diagnosed with any heart conditions or other medical conditions.",
        "extract_key": "sex",
        "confirm": None,
    },
    {
        "step": "conditions",
        "prompt": "The patient described their conditions. Acknowledge them compassionately and ask what medications they are currently taking.",
        "extract_key": "conditions",
        "confirm": None,
    },
    {
        "step": "medications",
        "prompt": "The patient listed their medications. Confirm what you heard and ask if they have any known drug allergies.",
        "extract_key": "medications",
        "confirm": None,
    },
    {
        "step": "allergies",
        "prompt": "The patient told you about allergies. Acknowledge and ask about their insurance situation (do they have insurance, and if so what kind).",
        "extract_key": "allergies",
        "confirm": None,
    },
    {
        "step": "insurance",
        "prompt": "The patient described their insurance. Thank them for sharing all of this. Let them know their profile is being set up and they can start chatting with you about their health.",
        "extract_key": "insurance",
        "confirm": None,
    },
]

# Extraction prompts for Gemini
EXTRACTION_SCHEMAS = {
    "name": {
        "prompt": "Extract the patient's full name from their message. Return JSON: {\"name\": \"First Last\"}",
        "type": "string",
    },
    "age": {
        "prompt": "Extract the patient's age from their message. Return JSON: {\"age\": <integer>}",
        "type": "int",
    },
    "sex": {
        "prompt": "Extract the patient's sex from their message (M or F). Return JSON: {\"sex\": \"M\" or \"F\"}",
        "type": "string",
    },
    "conditions": {
        "prompt": "Extract medical conditions from their message. Return JSON: {\"conditions\": [\"condition1\", \"condition2\"]}",
        "type": "list",
    },
    "medications": {
        "prompt": "Extract medications from their message. Return JSON: {\"medications\": [\"medication1\", \"medication2\"]}",
        "type": "list",
    },
    "allergies": {
        "prompt": "Extract drug allergies from their message. Return JSON: {\"allergies\": [\"allergy1\"]} or {\"allergies\": []} if none.",
        "type": "list",
    },
    "insurance": {
        "prompt": "Extract insurance tier from their message. Return JSON: {\"insurance\": \"tier1_generic\" or \"tier2_preferred\" or \"tier3_nonpreferred\" or \"uninsured\"}. Map descriptions: employer/good insurance=tier1, some coverage=tier2, limited=tier3, no insurance=uninsured.",
        "type": "string",
    },
}


class OnboardingSession:
    """Manages a single patient onboarding conversation."""

    def __init__(self):
        self.current_step = 0
        self.collected_data: dict[str, Any] = {}
        self.complete = False

    @property
    def step_name(self) -> str:
        if self.current_step >= len(ONBOARDING_STEPS):
            return "complete"
        return ONBOARDING_STEPS[self.current_step]["step"]

    @property
    def progress(self) -> dict:
        return {
            "current_step": self.current_step,
            "total_steps": len(ONBOARDING_STEPS),
            "step_name": self.step_name,
            "complete": self.complete,
        }

    def get_system_instruction(self) -> str:
        """Get the system instruction for the current onboarding step."""
        if self.current_step >= len(ONBOARDING_STEPS):
            return "Onboarding is complete. Greet the patient and let them know they can ask you anything about their heart health."

        step = ONBOARDING_STEPS[self.current_step]
        return (
            "You are Iris, a warm and compassionate heart failure care assistant. "
            "You are onboarding a new patient. Be conversational and kind. "
            "Do not use hyphens, use spaces instead. "
            f"Current step: {step['prompt']}"
        )

    def extract_data_v2(self, message: str, client: Any) -> dict | None:
        """Extract structured data using the new google.genai Client SDK."""
        if self.current_step >= len(ONBOARDING_STEPS):
            return None

        step = ONBOARDING_STEPS[self.current_step]
        key = step.get("extract_key")
        if not key:
            return None

        schema = EXTRACTION_SCHEMAS.get(key)
        if not schema:
            return None

        try:
            prompt = f"{schema['prompt']}\n\nPatient message: \"{message}\"\n\nReturn ONLY the JSON, nothing else."
            response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt])
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            data = json.loads(text)
            self.collected_data[key] = data.get(key, data.get(list(data.keys())[0]))
            return data
        except Exception as e:
            logger.warning(f"Gemini v2 extraction failed for {key}: {e}")
            return self._simple_extract(key, message)

    def extract_data(self, message: str, genai_model: Any = None) -> dict | None:
        """Extract structured data from the patient's message for the current step.

        Uses Gemini for extraction if available, falls back to simple parsing.
        """
        if self.current_step >= len(ONBOARDING_STEPS):
            return None

        step = ONBOARDING_STEPS[self.current_step]
        key = step.get("extract_key")

        if not key:
            return None

        schema = EXTRACTION_SCHEMAS.get(key)
        if not schema:
            return None

        # Try Gemini extraction
        if genai_model:
            try:
                prompt = f"{schema['prompt']}\n\nPatient message: \"{message}\"\n\nReturn ONLY the JSON, nothing else."
                response = genai_model.generate_content(prompt)
                text = response.text.strip()
                # Strip markdown code fences
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()
                data = json.loads(text)
                self.collected_data[key] = data.get(key, data.get(list(data.keys())[0]))
                return data
            except Exception as e:
                logger.warning(f"Gemini extraction failed for {key}: {e}")

        # Simple fallback extraction
        return self._simple_extract(key, message)

    def _simple_extract(self, key: str, message: str) -> dict | None:
        """Simple regex/heuristic extraction fallback."""
        msg = message.strip()

        if key == "name":
            # Take the whole message as name (common for "My name is X" or just "X")
            name = msg.replace("my name is ", "").replace("I'm ", "").replace("I am ", "").strip()
            name = name.rstrip(".")
            if name:
                self.collected_data["name"] = name.title()
                return {"name": name.title()}

        elif key == "age":
            import re
            match = re.search(r"(\d{1,3})", msg)
            if match:
                age = int(match.group(1))
                if 0 < age < 150:
                    self.collected_data["age"] = age
                    return {"age": age}

        elif key == "sex":
            lower = msg.lower()
            if "female" in lower or "woman" in lower or lower.strip() == "f":
                self.collected_data["sex"] = "F"
                return {"sex": "F"}
            elif "male" in lower or "man" in lower or lower.strip() == "m":
                self.collected_data["sex"] = "M"
                return {"sex": "M"}

        elif key in ("conditions", "medications", "allergies"):
            items = [s.strip() for s in msg.replace(" and ", ",").split(",") if s.strip()]
            if not items:
                items = [msg] if msg.lower() not in ("none", "no", "nothing", "n/a", "na") else []
            self.collected_data[key] = items
            return {key: items}

        elif key == "insurance":
            lower = msg.lower()
            if any(w in lower for w in ("no insurance", "uninsured", "none", "don't have")):
                tier = "uninsured"
            elif any(w in lower for w in ("employer", "good", "full", "blue cross", "aetna", "united")):
                tier = "tier1_generic"
            elif any(w in lower for w in ("some", "partial", "medicaid")):
                tier = "tier2_preferred"
            else:
                tier = "tier1_generic"
            self.collected_data["insurance"] = tier
            return {"insurance": tier}

        return None

    def advance(self) -> bool:
        """Move to the next onboarding step. Returns True if onboarding is complete."""
        self.current_step += 1
        if self.current_step >= len(ONBOARDING_STEPS):
            self.complete = True
        return self.complete

    def build_patient_data(self) -> dict:
        """Build the patient data dict from collected information.

        Validates the collected data and clamps/sanitizes any out of range
        values. Warnings from validation are logged.
        """
        from src.utils.data_loader import validate_onboarding_data

        data = self.collected_data

        # Run validation on collected data
        validated, warnings = validate_onboarding_data(data)
        for w in warnings:
            logger.warning(f"Onboarding validation: {w}")

        return {
            "name": validated.get("name", "New Patient"),
            "age": validated.get("age", 0),
            "sex": validated.get("sex", "U"),
            "medical_history": validated.get("conditions", []),
            "medications": [],  # Will be structured later
            "allergies": validated.get("allergies", []),
            "insurance_tier": validated.get("insurance", "tier1_generic"),
        }


# In-memory session store (single-user prototype)
_sessions: dict[str, OnboardingSession] = {}


def get_or_create_session(patient_id: str) -> OnboardingSession:
    """Get or create an onboarding session for a patient."""
    if patient_id not in _sessions:
        _sessions[patient_id] = OnboardingSession()
    return _sessions[patient_id]


def remove_session(patient_id: str):
    """Remove an onboarding session after completion."""
    _sessions.pop(patient_id, None)
