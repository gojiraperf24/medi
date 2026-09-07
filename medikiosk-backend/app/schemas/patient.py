from datetime import datetime
from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    full_name: str
    phone: str = Field(..., min_length=10, max_length=15)
    dob: str | None = None
    gender: str = "unknown"
    preferred_language: str = "hi"
    village_or_kiosk_id: str | None = None
    abha_id: str | None = None
    abha_address: str | None = None


class PatientOut(BaseModel):
    id: str
    full_name: str
    phone: str
    dob: str | None
    gender: str
    preferred_language: str
    abha_id: str | None
    abha_address: str | None
    village_or_kiosk_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True
