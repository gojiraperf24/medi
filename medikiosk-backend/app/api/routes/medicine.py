from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas.medicine import MedicineScanOut
from app.services.medicine_recognition import recognize_medicine_image, find_jan_aushadhi_alternatives

router = APIRouter(prefix="/medicine", tags=["medicine"])


@router.post("/scan", response_model=MedicineScanOut, status_code=201)
async def scan_medicine(
    image: UploadFile = File(...),
    patient_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Accepts a photo of medicine packaging. The recognition step itself is
    mocked (see services/medicine_recognition.py) — we don't run a real
    OpenCV/OCR pipeline on the uploaded bytes — but the upload handling,
    storage reference, and Jan Aushadhi generic-alternative lookup are real.
    """
    # In production this would upload to S3 and store the returned key;
    # here we just record the filename as the reference.
    image_ref = f"uploads/{image.filename}"

    recognition = recognize_medicine_image(image_ref)
    alternatives = find_jan_aushadhi_alternatives(recognition["_compound_key"])

    scan = models.MedicineScan(
        patient_id=patient_id,
        image_ref=image_ref,
        detected_brand_name=recognition["detected_brand_name"],
        detected_compound=recognition["detected_compound"],
        ocr_raw_text=recognition["ocr_raw_text"],
        confidence=recognition["confidence"],
        jan_aushadhi_alternatives=alternatives,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/lookup", response_model=list[dict])
def lookup_generic_alternatives(compound: str):
    """Direct lookup by compound name — useful for testing without an image upload."""
    return find_jan_aushadhi_alternatives(compound)
