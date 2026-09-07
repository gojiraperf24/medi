"""
Mock of Bhashini (India's public STT/TTS/translation API, bhashini.gov.in)
used to voice-guide low-literacy patients through intake in their own
language.

Real integration reference: Bhashini exposes ASR (speech->text), NMT
(translation) and TTS (text->speech) as separate pipeline stages behind a
single /pipeline endpoint, keyed by a pipeline ID from your Bhashini
Sahyogi (My Scheme) API key.

Why mocked: real ASR needs actual recorded audio in the target language and
a live API key; for the demo, canned responses let the intake flow, triage,
and FHIR export be demoed end-to-end without depending on network audio
processing working live on stage.
"""
from abc import ABC, abstractmethod

from app.db.models import VoiceInteractionLog
from sqlalchemy.orm import Session

# Minimal guided-intake script. In the real system this would be driven by
# your existing `interview.py` state machine — this mirrors that shape so
# the two can be merged later.
GUIDED_INTAKE_STEPS: dict[str, dict] = {
    "greeting": {
        "text": {
            "hi": "नमस्ते! मैं आपकी स्वास्थ्य जांच में मदद करूंगा। क्या आप शुरू करने के लिए तैयार हैं?",
            "en": "Hello! I'll help with your health check-in. Are you ready to begin?",
        },
        "input_type": "yes_no",
        "next": "chief_complaint",
    },
    "chief_complaint": {
        "text": {
            "hi": "आपको आज क्या तकलीफ है?",
            "en": "What is bothering you today?",
        },
        "input_type": "free_text",
        "next": "duration",
    },
    "duration": {
        "text": {
            "hi": "यह तकलीफ कब से है?",
            "en": "How long have you had this problem?",
        },
        "input_type": "choice",
        "choices": {
            "hi": ["आज से", "इस हफ्ते से", "इस महीने से", "लंबे समय से"],
            "en": ["Since today", "This week", "This month", "Longer"],
        },
        "next": "vitals_prompt",
    },
    "vitals_prompt": {
        "text": {
            "hi": "अब कृपया अपनी उंगली मशीन में रखें ताकि हम आपकी नब्ज़ और ऑक्सीजन माप सकें।",
            "en": "Now please place your finger in the device so we can measure your pulse and oxygen.",
        },
        "input_type": "vitals_prompt",
        "next": None,
    },
}


class VoiceClient(ABC):
    @abstractmethod
    def speech_to_text(self, audio_ref: str | None, language: str) -> tuple[str, float]:
        ...

    @abstractmethod
    def text_to_speech(self, text: str, language: str) -> str:
        ...


class MockVoiceClient(VoiceClient):
    def speech_to_text(self, audio_ref: str | None, language: str) -> tuple[str, float]:
        # No real ASR model wired up — return a clearly-marked canned transcript
        # so the demo flow can proceed and downstream steps (interview logic,
        # triage) can be exercised with realistic-shaped input.
        canned = {
            "hi": "मुझे सिर दर्द और बुखार है",
            "en": "I have a headache and fever",
        }
        return canned.get(language, canned["en"]), 0.92

    def text_to_speech(self, text: str, language: str) -> str:
        # Real Bhashini TTS returns base64 audio; we return a fake storage
        # ref so the API contract (audio_ref field) matches what the real
        # integration will return.
        slug = "".join(c for c in text[:24] if c.isalnum() or c == " ").strip().replace(" ", "_")
        return f"mock-audio://{language}/{slug or 'clip'}.wav"


def get_voice_client() -> VoiceClient:
    return MockVoiceClient()


def log_voice_interaction(db: Session, patient_id: str | None, language: str, direction: str, text: str, input_ref: str | None = None):
    entry = VoiceInteractionLog(
        patient_id=patient_id, language=language, direction=direction, text=text, input_ref=input_ref
    )
    db.add(entry)
    db.commit()
    return entry
