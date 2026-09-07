from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas.documents import DocumentScanOut, PatientHistorySummary
from app.services.document_ocr import mock_ocr_extract_text, extract_medical_history, aggregate_patient_history

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/scan", response_model=DocumentScanOut, status_code=201)
async def scan_document(
    patient_id: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Scans an old prescription / lab report / discharge summary. OCR itself
    is mocked (see services/document_ocr.py); the keyword extraction that
    turns the OCR text into structured conditions/medications is real.
    """
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    image_ref = f"uploads/{image.filename}"
    ocr_result = mock_ocr_extract_text(image_ref)
    extraction = extract_medical_history(ocr_result["ocr_raw_text"])

    scan = models.MedicalDocumentScan(
        patient_id=patient_id,
        image_ref=image_ref,
        document_type=ocr_result["document_type"],
        ocr_raw_text=ocr_result["ocr_raw_text"],
        document_date_text=extraction["document_date_text"],
        extracted_conditions=extraction["conditions"],
        extracted_medications=extraction["medications"],
        confidence=ocr_result["confidence"],
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/patient/{patient_id}", response_model=list[DocumentScanOut])
def list_patient_documents(patient_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.MedicalDocumentScan)
        .filter_by(patient_id=patient_id)
        .order_by(models.MedicalDocumentScan.created_at.desc())
        .all()
    )


@router.get("/patient/{patient_id}/history", response_model=PatientHistorySummary)
def get_patient_history_summary(patient_id: str, db: Session = Depends(get_db)):
    """The rolled-up view triage and FHIR export actually use."""
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    summary = aggregate_patient_history(db, patient_id)
    return PatientHistorySummary(patient_id=patient_id, **summary)
