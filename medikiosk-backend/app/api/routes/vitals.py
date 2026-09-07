from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas import vitals as schemas

router = APIRouter(prefix="/vitals", tags=["vitals"])


def _create_reading(db: Session, payload: schemas.VitalsIn) -> models.VitalsReading:
    # Idempotency: if this exact client_reading_id was already stored
    # (e.g. an offline kiosk retried a sync batch), return the existing row
    # instead of creating a duplicate.
    if payload.client_reading_id:
        existing = (
            db.query(models.VitalsReading)
            .filter_by(client_reading_id=payload.client_reading_id)
            .first()
        )
        if existing:
            return existing

    reading = models.VitalsReading(
        **payload.model_dump(exclude={"recorded_at"}),
        recorded_at=payload.recorded_at or datetime.now(timezone.utc),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.post("", response_model=schemas.VitalsOut, status_code=201)
def record_vitals(payload: schemas.VitalsIn, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter_by(id=payload.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _create_reading(db, payload)


@router.get("/patient/{patient_id}", response_model=list[schemas.VitalsOut])
def get_patient_vitals(patient_id: str, limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(models.VitalsReading)
        .filter_by(patient_id=patient_id)
        .order_by(models.VitalsReading.recorded_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{reading_id}", response_model=schemas.VitalsOut)
def get_reading(reading_id: str, db: Session = Depends(get_db)):
    reading = db.query(models.VitalsReading).filter_by(id=reading_id).first()
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading


@router.post("/sync-batch", response_model=schemas.OfflineSyncResult)
def sync_offline_batch(payload: schemas.OfflineSyncBatch, db: Session = Depends(get_db)):
    """
    Offline-first sync: a kiosk that queued readings locally (SQLite/PouchDB)
    while offline calls this once connectivity returns, pushing everything
    at once. Each reading's `client_reading_id` makes retries safe.
    """
    accepted_ids: list[str] = []
    duplicates = 0

    for reading_payload in payload.readings:
        before_count = db.query(models.VitalsReading).count()
        reading = _create_reading(db, reading_payload)
        after_count = db.query(models.VitalsReading).count()
        if after_count == before_count:
            duplicates += 1
        accepted_ids.append(reading.id)

    return schemas.OfflineSyncResult(
        accepted=len(accepted_ids) - duplicates,
        duplicates_skipped=duplicates,
        reading_ids=accepted_ids,
    )
