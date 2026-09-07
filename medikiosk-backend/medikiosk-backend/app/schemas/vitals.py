from datetime import datetime
from pydantic import BaseModel, Field


class VitalsIn(BaseModel):
    """Generic vitals payload — used by manual entry, device ingestion, and offline sync."""
    patient_id: str
    source: str = Field("manual", pattern="^(manual|device|offline_sync)$")
    device_type: str | None = Field(
        None, description="pulse_oximeter | bp_cuff | glucometer | scale | thermometer"
    )

    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    heart_rate_bpm: float | None = None
    spo2_percent: float | None = None
    temperature_c: float | None = None
    glucose_mg_dl: float | None = None
    glucose_context: str | None = Field(None, pattern="^(fasting|random|postprandial)$")
    weight_kg: float | None = None
    height_cm: float | None = None

    client_reading_id: str | None = Field(
        None, description="Client-generated idempotency key (e.g. UUID from kiosk's local queue)"
    )
    recorded_at: datetime | None = None


class VitalsOut(BaseModel):
    id: str
    patient_id: str
    source: str
    device_type: str | None
    systolic_bp: float | None
    diastolic_bp: float | None
    heart_rate_bpm: float | None
    spo2_percent: float | None
    temperature_c: float | None
    glucose_mg_dl: float | None
    glucose_context: str | None
    weight_kg: float | None
    height_cm: float | None
    recorded_at: datetime
    synced_at: datetime

    class Config:
        from_attributes = True


class DeviceIngestPayload(BaseModel):
    """Payload shape for the MQTT-style sensor ingestion endpoint (also used over plain HTTP as a fallback)."""
    kiosk_id: str
    patient_id: str
    device_type: str
    reading: dict = Field(..., description="Raw key/value reading from the device driver, e.g. {'spo2': 97, 'pulse': 78}")
    recorded_at: datetime | None = None
    client_reading_id: str | None = None


class OfflineSyncBatch(BaseModel):
    """Batch of queued vitals pushed by a kiosk once connectivity returns."""
    kiosk_id: str
    readings: list[VitalsIn]


class OfflineSyncResult(BaseModel):
    accepted: int
    duplicates_skipped: int
    reading_ids: list[str]
