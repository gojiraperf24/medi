from datetime import datetime
from pydantic import BaseModel


class TriageRequest(BaseModel):
    patient_id: str
    vitals_reading_id: str | None = None
    # Allow triage to run inline on a fresh reading that hasn't been stored yet.
    inline_vitals: dict | None = None


class TriageOut(BaseModel):
    id: str
    patient_id: str
    vitals_reading_id: str | None
    risk_level: str
    flags: list[str]
    rationale: list[str]
    recommended_action: str
    engine_version: str
    created_at: datetime

    class Config:
        from_attributes = True
