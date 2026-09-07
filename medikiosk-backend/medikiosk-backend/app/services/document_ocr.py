"""
Reads a patient's OLD medical documents — a paper prescription, a lab
report printout, a discharge summary — the paper trail most rural patients
actually carry instead of a digital record. This is distinct from
medicine_recognition.py, which reads a CURRENT medicine's packaging.

The OCR step itself (turning a photo into raw text) is MOCKED — no real
Tesseract/vision model is wired up, same reasoning as medicine_recognition.py:
a hackathon demo can't depend on a live OCR model reading an arbitrary
photo correctly on stage. What IS real: the extraction logic that turns raw
OCR text into structured conditions/medications, using plain keyword
matching — no LLM, fully deterministic and auditable, same design
philosophy as triage_engine.py.

Swap `mock_ocr_extract_text` for a real Tesseract/PaddleOCR/vision-model
call without touching `extract_medical_history` at all — it only cares
about the text, not where it came from.
"""
import random
import re

# A handful of realistic canned OCR outputs, standing in for a real vision
# model reading an uploaded photo. Varied so a demo doesn't look scripted.
_MOCK_DOCUMENTS = [
    {
        "document_type": "prescription",
        "text": (
            "Dr. R. Sharma, MBBS MD\n"
            "Date: 12/03/2025\n"
            "Patient c/o fever, cough since 3 days\n"
            "Dx: Type 2 Diabetes Mellitus (known case), Hypertension\n"
            "Rx:\n"
            "1. Tab Metformin 500mg BD\n"
            "2. Tab Amlodipine 5mg OD\n"
            "3. Tab Paracetamol 500mg SOS for fever\n"
            "Advice: Low salt diet, follow up in 2 weeks"
        ),
    },
    {
        "document_type": "lab_report",
        "text": (
            "XYZ Diagnostic Centre\n"
            "Report Date: 04-11-2024\n"
            "Fasting Blood Glucose: 168 mg/dL (High)\n"
            "HbA1c: 8.1% (High)\n"
            "Impression: Findings consistent with Diabetes Mellitus\n"
            "Blood Pressure recorded: 148/94 mmHg — Hypertension noted"
        ),
    },
    {
        "document_type": "discharge_summary",
        "text": (
            "District Hospital — Discharge Summary\n"
            "Admission: 20/01/2025  Discharge: 25/01/2025\n"
            "Final Diagnosis: Bronchial Asthma exacerbation, Anemia\n"
            "Medications on discharge:\n"
            "- Tab Cetirizine 10mg OD\n"
            "- Iron + Folic Acid tablets OD\n"
            "- Salbutamol inhaler SOS\n"
            "Follow up with pulmonologist in 1 week"
        ),
    },
]

# Keyword -> normalized condition name. Deliberately simple substring
# matching (lowercased) rather than NLP/NER — auditable and good enough for
# structured clinical documents which use fairly standard terminology.
_CONDITION_KEYWORDS: dict[str, str] = {
    "diabetes": "Diabetes",
    "diabetic": "Diabetes",
    "hypertension": "Hypertension",
    "high blood pressure": "Hypertension",
    "asthma": "Asthma",
    "bronchial": "Asthma",
    "anemia": "Anemia",
    "anaemia": "Anemia",
    "thyroid": "Thyroid disorder",
    "tuberculosis": "Tuberculosis",
    " tb ": "Tuberculosis",
    "kidney disease": "Chronic kidney disease",
    "ckd": "Chronic kidney disease",
    "cardiac": "Cardiac condition",
    "heart disease": "Cardiac condition",
    "allergy": "Known allergy",
    "allergic": "Known allergy",
}

# Medications worth flagging as "currently/recently prescribed" — reuses
# the compound vocabulary from medicine_recognition.py plus a few more
# common ones that show up in Indian prescriptions.
_MEDICATION_KEYWORDS: list[str] = [
    "paracetamol", "azithromycin", "metformin", "amlodipine", "omeprazole",
    "cetirizine", "amoxicillin", "insulin", "aspirin", "atorvastatin",
    "losartan", "salbutamol", "folic acid",
]

_DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")


def aggregate_patient_history(db, patient_id: str) -> dict:
    """
    Rolls up every scanned document for a patient into one deduplicated
    view: all conditions ever detected, all medications ever detected.
    Used by the triage route (to reword rationale for known conditions)
    and the FHIR export (to emit Condition resources).
    """
    from app.db import models  # local import avoids a circular import with models.py

    scans = db.query(models.MedicalDocumentScan).filter_by(patient_id=patient_id).all()
    conditions: set[str] = set()
    medications: set[str] = set()
    for scan in scans:
        conditions.update(scan.extracted_conditions or [])
        medications.update(scan.extracted_medications or [])
    return {
        "known_conditions": sorted(conditions),
        "known_medications": sorted(medications),
        "document_count": len(scans),
    }


def mock_ocr_extract_text(image_ref: str | None) -> dict:
    """MOCKED — returns a randomly chosen canned OCR result. Swap this
    function body for a real OCR call; `extract_medical_history` below
    doesn't need to change."""
    doc = random.choice(_MOCK_DOCUMENTS)
    return {
        "document_type": doc["document_type"],
        "ocr_raw_text": doc["text"],
        "confidence": round(random.uniform(0.75, 0.95), 2),
    }


def extract_medical_history(raw_text: str) -> dict:
    """
    REAL, deterministic keyword extraction over OCR'd text. No LLM, no
    guessing — every match is a literal substring hit, so results are
    fully explainable (same principle as the triage engine).
    """
    lowered = f" {raw_text.lower()} "

    conditions = sorted({
        normalized
        for keyword, normalized in _CONDITION_KEYWORDS.items()
        if keyword in lowered
    })
    medications = sorted({
        med.capitalize()
        for med in _MEDICATION_KEYWORDS
        if med in lowered
    })
    date_match = _DATE_PATTERN.search(raw_text)

    return {
        "conditions": conditions,
        "medications": medications,
        "document_date_text": date_match.group(0) if date_match else None,
    }
