from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas import triage as schemas
from app.services.triage_engine import run_triage
from app.services.document_ocr import aggregate_patient_history

router = APIRouter(prefix="/triage", tags=["triage"])


def _vitals_dict(vitals: models.VitalsReading) -> dict:
    return {
        "systolic_bp": vitals.systolic_bp,
        "diastolic_bp": vitals.diastolic_bp,
        "heart_rate_bpm": vitals.heart_rate_bpm,
        "spo2_percent": vitals.spo2_percent,
        "temperature_c": vitals.temperature_c,
        "glucose_mg_dl": vitals.glucose_mg_dl,
        "glucose_context": vitals.glucose_context,
    }


@router.post("/run", response_model=schemas.TriageOut, status_code=201)
def run_triage_for_patient(payload: schemas.TriageRequest, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter_by(id=payload.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if payload.inline_vitals is not None:
        vitals_dict = payload.inline_vitals
        vitals_reading_id = payload.vitals_reading_id
    elif payload.vitals_reading_id:
        vitals = db.query(models.VitalsReading).filter_by(id=payload.vitals_reading_id).first()
        if vitals is None:
            raise HTTPException(status_code=404, detail="Vitals reading not found")
        vitals_dict = _vitals_dict(vitals)
        vitals_reading_id = vitals.id
    else:
        latest = (
            db.query(models.VitalsReading)
            .filter_by(patient_id=payload.patient_id)
            .order_by(models.VitalsReading.recorded_at.desc())
            .first()
        )
        if latest is None:
            raise HTTPException(status_code=400, detail="No vitals available for this patient — record vitals first")
        vitals_dict = _vitals_dict(latest)
        vitals_reading_id = latest.id

    outcome = run_triage(vitals_dict, known_conditions=aggregate_patient_history(db, payload.patient_id)["known_conditions"])

    result = models.TriageResult(
        patient_id=payload.patient_id,
        vitals_reading_id=vitals_reading_id,
        risk_level=outcome.risk_level,
        flags=outcome.flags,
        rationale=outcome.rationale,
        recommended_action=outcome.recommended_action,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.get("/patient/{patient_id}", response_model=list[schemas.TriageOut])
def get_patient_triage_history(patient_id: str, limit: int = 10, db: Session = Depends(get_db)):
    return (
        db.query(models.TriageResult)
        .filter_by(patient_id=patient_id)
        .order_by(models.TriageResult.created_at.desc())
        .limit(limit)
        .all()
    )
