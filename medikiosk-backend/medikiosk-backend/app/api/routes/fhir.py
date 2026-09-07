from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.services.fhir_builder import build_bundle

router = APIRouter(prefix="/fhir", tags=["fhir"])


@router.post("/patient/{patient_id}/bundle")
def generate_bundle(patient_id: str, persist: bool = True, db: Session = Depends(get_db)):
    """
    Generates a FHIR R4 Bundle covering this patient's demographics, vitals
    (as Observations), triage results (as RiskAssessments), and
    consultations (as Encounters). Set `persist=false` to preview without
    writing an audit-trail row.

    NOTE: this covers the vitals/triage/encounter side only. If your
    existing `summary.py` produces intake/Condition resources, merge them
    in by passing them through `extra_resources` in
    services/fhir_builder.build_bundle — that hook exists for exactly this.
    """
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    vitals_list = db.query(models.VitalsReading).filter_by(patient_id=patient_id).all()
    triage_list = db.query(models.TriageResult).filter_by(patient_id=patient_id).all()
    consultations = db.query(models.ConsultationSession).filter_by(patient_id=patient_id).all()
    document_scans = db.query(models.MedicalDocumentScan).filter_by(patient_id=patient_id).all()

    bundle = build_bundle(patient, vitals_list, triage_list, consultations, document_scans)

    if persist:
        record = models.FHIRBundleRecord(patient_id=patient_id, bundle_json=bundle)
        db.add(record)
        db.commit()

    return bundle


@router.get("/patient/{patient_id}/bundles")
def list_stored_bundles(patient_id: str, db: Session = Depends(get_db)):
    records = (
        db.query(models.FHIRBundleRecord)
        .filter_by(patient_id=patient_id)
        .order_by(models.FHIRBundleRecord.created_at.desc())
        .all()
    )
    return [{"id": r.id, "created_at": r.created_at, "bundle": r.bundle_json} for r in records]
