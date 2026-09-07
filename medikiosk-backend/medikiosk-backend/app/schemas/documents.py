from datetime import datetime
from pydantic import BaseModel


class DocumentScanOut(BaseModel):
    id: str
    patient_id: str
    document_type: str
    ocr_raw_text: str
    document_date_text: str | None
    extracted_conditions: list[str]
    extracted_medications: list[str]
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class PatientHistorySummary(BaseModel):
    """Aggregated view across all of a patient's scanned documents —
    what triage and the FHIR export actually consume."""
    patient_id: str
    known_conditions: list[str]
    known_medications: list[str]
    document_count: int
