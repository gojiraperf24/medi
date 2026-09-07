from pydantic import BaseModel


class SttRequest(BaseModel):
    """Audio comes as base64 in a real integration; kept as a ref/string here
    since MOCK_BHASHINI short-circuits before any audio decoding happens."""
    patient_id: str | None = None
    language: str = "hi"
    audio_base64: str | None = None
    audio_ref: str | None = None


class SttResponse(BaseModel):
    transcript: str
    language: str
    confidence: float


class TtsRequest(BaseModel):
    patient_id: str | None = None
    language: str = "hi"
    text: str


class TtsResponse(BaseModel):
    audio_ref: str
    language: str
    text: str


class GuidedQuestionRequest(BaseModel):
    """Drives the low-literacy voice-guided intake flow: given the current
    step, return the next question, translated + ready for TTS."""
    patient_id: str
    language: str = "hi"
    current_step: str | None = None
    last_answer_transcript: str | None = None


class GuidedQuestionResponse(BaseModel):
    step_id: str
    question_text: str
    question_audio_ref: str
    input_type: str  # "yes_no" | "free_text" | "choice" | "vitals_prompt"
    choices: list[str] | None = None
    is_final_step: bool = False
