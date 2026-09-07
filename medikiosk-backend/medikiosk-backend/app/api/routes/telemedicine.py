from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.db import models
from app.ws.telemedicine_manager import manager

router = APIRouter(prefix="/telemedicine", tags=["telemedicine"])


class ConsultationCreate(BaseModel):
    patient_id: str
    kiosk_id: str | None = None
    doctor_id: str | None = None


class ConsultationOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str | None
    kiosk_id: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None

    class Config:
        from_attributes = True


@router.post("/consultations", response_model=ConsultationOut, status_code=201)
def create_consultation(payload: ConsultationCreate, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter_by(id=payload.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    consultation = models.ConsultationSession(
        patient_id=payload.patient_id, kiosk_id=payload.kiosk_id, doctor_id=payload.doctor_id,
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.post("/consultations/{consultation_id}/start", response_model=ConsultationOut)
def start_consultation(consultation_id: str, db: Session = Depends(get_db)):
    consultation = db.query(models.ConsultationSession).filter_by(id=consultation_id).first()
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    consultation.status = models.ConsultationStatus.live
    consultation.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.post("/consultations/{consultation_id}/end", response_model=ConsultationOut)
def end_consultation(consultation_id: str, db: Session = Depends(get_db)):
    consultation = db.query(models.ConsultationSession).filter_by(id=consultation_id).first()
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    consultation.status = models.ConsultationStatus.completed
    consultation.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.websocket("/consultations/{consultation_id}/stream")
async def consultation_stream(websocket: WebSocket, consultation_id: str, role: str = "kiosk"):
    """
    Real-time WebSocket channel for a consultation room.

    Connect from the kiosk side with role=kiosk and push frames like:
        {"type": "vitals", "data": {"spo2_percent": 97, "heart_rate_bpm": 78}}
    Connect from the doctor-portal side with role=doctor to receive them.
    Any client in the room can also send:
        {"type": "chat", "text": "..."}

    MOCK_TELEMEDICINE=True just means there's no real eSanjeevani doctor
    account behind role=doctor in this build — the socket transport and
    fan-out below are fully real and testable with two plain WebSocket
    clients (e.g. websocat) in the same room.
    """
    await manager.connect(websocket, consultation_id, role)
    await manager.broadcast(
        consultation_id, {"type": "presence", "role": role, "event": "joined", "room_size": manager.room_size(consultation_id)},
        exclude=websocket,
    )
    try:
        while True:
            message = await websocket.receive_json()
            message.setdefault("type", "vitals")
            message["role"] = role

            # Persist vitals frames pushed over the socket so they show up
            # in the patient's normal vitals history / FHIR export too.
            if message["type"] == "vitals" and isinstance(message.get("data"), dict):
                db = SessionLocal()
                try:
                    consultation = db.query(models.ConsultationSession).filter_by(id=consultation_id).first()
                    if consultation:
                        reading = models.VitalsReading(
                            patient_id=consultation.patient_id,
                            source="device",
                            device_type="telemedicine_stream",
                            **{k: v for k, v in message["data"].items() if hasattr(models.VitalsReading, k)},
                        )
                        db.add(reading)
                        db.commit()
                finally:
                    db.close()

            await manager.broadcast(consultation_id, message, exclude=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, consultation_id)
        await manager.broadcast(
            consultation_id, {"type": "presence", "role": role, "event": "left", "room_size": manager.room_size(consultation_id)},
        )
