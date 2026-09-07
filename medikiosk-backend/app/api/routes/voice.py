from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import voice as schemas
from app.services.bhashini_mock import (
    get_voice_client, log_voice_interaction, GUIDED_INTAKE_STEPS,
)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/stt", response_model=schemas.SttResponse)
def speech_to_text(payload: schemas.SttRequest, db: Session = Depends(get_db)):
    client = get_voice_client()
    transcript, confidence = client.speech_to_text(payload.audio_ref, payload.language)
    log_voice_interaction(db, payload.patient_id, payload.language, "stt", transcript, payload.audio_ref)
    return schemas.SttResponse(transcript=transcript, language=payload.language, confidence=confidence)


@router.post("/tts", response_model=schemas.TtsResponse)
def text_to_speech(payload: schemas.TtsRequest, db: Session = Depends(get_db)):
    client = get_voice_client()
    audio_ref = client.text_to_speech(payload.text, payload.language)
    log_voice_interaction(db, payload.patient_id, payload.language, "tts", payload.text, audio_ref)
    return schemas.TtsResponse(audio_ref=audio_ref, language=payload.language, text=payload.text)


@router.post("/guided-intake/next", response_model=schemas.GuidedQuestionResponse)
def next_guided_question(payload: schemas.GuidedQuestionRequest, db: Session = Depends(get_db)):
    """
    Drives the low-literacy voice-guided intake flow one step at a time.
    Mirrors the shape of the existing `interview.py` state machine so the
    two can eventually be merged — this endpoint currently runs its own
    small script (see GUIDED_INTAKE_STEPS) rather than calling into it.
    """
    step_id = payload.current_step or "greeting"
    step = GUIDED_INTAKE_STEPS.get(step_id, GUIDED_INTAKE_STEPS["greeting"])

    lang = payload.language
    question_text = step["text"].get(lang, step["text"]["en"])
    client = get_voice_client()
    audio_ref = client.text_to_speech(question_text, lang)
    log_voice_interaction(db, payload.patient_id, lang, "tts", question_text, audio_ref)

    choices = step.get("choices", {}).get(lang) if step.get("choices") else None
    next_step = step.get("next")

    return schemas.GuidedQuestionResponse(
        step_id=step_id,
        question_text=question_text,
        question_audio_ref=audio_ref,
        input_type=step["input_type"],
        choices=choices,
        is_final_step=next_step is None,
    )
