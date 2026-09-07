"""
Sensor ingestion endpoint.

This is a REAL, working REST endpoint that accepts device readings in the
shape a kiosk's local hardware driver would produce. Actual Bluetooth/USB
pairing with physical pulse oximeters, BP cuffs, glucometers etc. is NOT
implemented here (that lives on the kiosk device/firmware side, e.g. an
ESP32 or the kiosk tablet's BLE stack) — this endpoint is what that driver
calls once it has a reading, whether it gets there over plain HTTPS or a
kiosk-local MQTT broker bridges it here.

A minimal Mosquitto-compatible subscriber that forwards MQTT messages to
this same endpoint is sketched in `app/services/mqtt_bridge.py` for when
real hardware is available to test against.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas.vitals import DeviceIngestPayload, VitalsOut

router = APIRouter(prefix="/devices", tags=["devices"])

# Maps a raw device reading's keys onto VitalsReading columns, per device type.
# Extend this as new device drivers/models are added.
_DEVICE_FIELD_MAP: dict[str, dict[str, str]] = {
    "pulse_oximeter": {"spo2": "spo2_percent", "pulse": "heart_rate_bpm"},
    "bp_cuff": {"systolic": "systolic_bp", "diastolic": "diastolic_bp", "pulse": "heart_rate_bpm"},
    "glucometer": {"glucose": "glucose_mg_dl", "context": "glucose_context"},
    "scale": {"weight": "weight_kg"},
    "thermometer": {"temp_c": "temperature_c"},
}


@router.post("/ingest", response_model=VitalsOut, status_code=201)
def ingest_device_reading(payload: DeviceIngestPayload, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter_by(id=payload.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    field_map = _DEVICE_FIELD_MAP.get(payload.device_type)
    if field_map is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown device_type '{payload.device_type}'. Known types: {list(_DEVICE_FIELD_MAP)}",
        )

    mapped_fields = {}
    for raw_key, model_field in field_map.items():
        if raw_key in payload.reading:
            mapped_fields[model_field] = payload.reading[raw_key]

    if payload.client_reading_id:
        existing = db.query(models.VitalsReading).filter_by(client_reading_id=payload.client_reading_id).first()
        if existing:
            return existing

    reading = models.VitalsReading(
        patient_id=payload.patient_id,
        source="device",
        device_type=payload.device_type,
        client_reading_id=payload.client_reading_id,
        recorded_at=payload.recorded_at or datetime.now(timezone.utc),
        **mapped_fields,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading
