from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas import patient as schemas

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=schemas.PatientOut, status_code=201)
def create_patient(payload: schemas.PatientCreate, db: Session = Depends(get_db)):
    """Manual patient registration — used when staff enroll a walk-in patient
    without going through the ABHA OTP/QR login flow."""
    patient = models.Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=schemas.PatientOut)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("", response_model=list[schemas.PatientOut])
def search_patients(phone: str | None = None, abha_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Patient)
    if phone:
        query = query.filter(models.Patient.phone == phone)
    if abha_id:
        query = query.filter(models.Patient.abha_id == abha_id)
    return query.order_by(models.Patient.created_at.desc()).limit(50).all()
