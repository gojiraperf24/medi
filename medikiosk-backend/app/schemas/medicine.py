from datetime import datetime
from pydantic import BaseModel


class JanAushadhiAlternative(BaseModel):
    generic_name: str
    compound: str
    estimated_price_inr: float
    pack_size: str | None = None


class MedicineScanOut(BaseModel):
    id: str
    detected_brand_name: str | None
    detected_compound: str | None
    ocr_raw_text: str | None
    confidence: float
    jan_aushadhi_alternatives: list[JanAushadhiAlternative]
    created_at: datetime

    class Config:
        from_attributes = True
