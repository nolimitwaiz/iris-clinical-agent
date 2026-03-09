"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    patient_id: str
    message: str | None = None
    audio_data: str | None = None  # base64 encoded audio
    audio_mime_type: str | None = None  # e.g. "audio/webm"
    image_data: str | None = None  # base64 encoded image
    image_mime_type: str | None = None  # e.g. "image/jpeg"
    conversation_history: list[dict] | None = None  # [{role, content}]
    generate_audio: bool = False  # request TTS for text messages


class InitialVitals(BaseModel):
    """Optional initial vital signs from onboarding."""

    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    heart_rate: float | None = None


class InitialLabs(BaseModel):
    """Optional initial lab values from onboarding."""

    potassium: float | None = None
    creatinine: float | None = None
    egfr: float | None = None


class PatientCreateRequest(BaseModel):
    """Request body for POST /api/patients (onboarding)."""

    name: str
    age: int
    sex: str
    ejection_fraction: float = 0.0
    nyha_class: int = 2
    weight_kg: float = 70.0
    height_cm: float = 170.0
    medical_history: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[dict] = Field(default_factory=list)
    insurance_tier: str = "tier1_generic"
    initial_vitals: InitialVitals | None = None
    initial_labs: InitialLabs | None = None


class ActionPacketResponse(BaseModel):
    """A single Action Packet in the API response."""

    tool_name: str
    timestamp: str | None = None
    inputs_used: dict | None = None
    decision: str
    drug: str | None = None
    current_dose_mg: float | None = None
    new_dose_mg: float | None = None
    reason: str
    guideline: str
    monitoring: str | None = None
    confidence: str
    risk_of_inaction: str
    data_quality: str | None = None


class ValidationResult(BaseModel):
    """Validation result from the response validator."""

    approved: bool
    violations: list[str] = Field(default_factory=list)


class SignalsResponse(BaseModel):
    """Extracted signals from patient message."""

    symptoms: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    adherence_signals: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    barriers_mentioned: list[str] = Field(default_factory=list)
    mood: str = ""


class PillarScore(BaseModel):
    """Score for a single GDMT pillar in the MOS calculation."""

    name: str
    drug: str | None = None
    current_dose_mg: float | None = None
    target_dose_mg: float | None = None
    score: int
    max_score: int
    status: str


class MOSResponse(BaseModel):
    """Medication Optimization Score response."""

    mos_score: int
    pillars: list[PillarScore]


class RiskComponent(BaseModel):
    """A single component of the composite risk score."""

    score: float
    weight: float
    contribution: float
    detail: str


class RiskScore(BaseModel):
    """Composite decompensation risk score."""

    composite: int
    tier: str
    components: dict[str, RiskComponent]


class ChatResponse(BaseModel):
    """Response body for POST /api/chat."""

    response_text: str
    audio_response: str | None = None  # base64 encoded TTS audio
    action_packets: list[ActionPacketResponse]
    validation: ValidationResult
    signals: SignalsResponse
    transcript: str | None = None  # transcribed text if audio input was used
    conversation_history: list[dict] | None = None  # persisted history
    mos: MOSResponse | None = None  # Medication Optimization Score


class TTSRequest(BaseModel):
    """Request body for POST /api/chat/tts."""

    text: str


class TTSResponse(BaseModel):
    """Response body for POST /api/chat/tts."""

    audio: str | None = None  # base64 encoded WAV audio


class MedicationSummary(BaseModel):
    """Summary of a patient's current medication."""

    drug: str
    dose_mg: float
    frequency_per_day: int
    route: str


class LabValue(BaseModel):
    """A single lab value with date."""

    value: float
    date: str


class PatientSummary(BaseModel):
    """Summary patient info for the patient list."""

    patient_id: str
    name: str
    age: int
    sex: str
    ejection_fraction: float
    nyha_class: int


class PatientDetail(BaseModel):
    """Full patient detail for the clinician view."""

    patient_id: str
    name: str
    age: int
    sex: str
    height_cm: float
    weight_kg: float
    ejection_fraction: float
    nyha_class: int
    medical_history: list[str]
    allergies: list[str]
    medications: list[dict]
    labs: dict
    vitals: dict
    social_factors: dict
    adherence: dict
    conversation_history: list[dict] = Field(default_factory=list)
