from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.database import get_db
from app.db import models
from app.schemas import auth as schemas
from app.services.abha_mock import get_abha_client

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/otp/request", response_model=schemas.OtpRequestResponse)
def request_otp(payload: schemas.OtpRequest, db: Session = Depends(get_db)):
    """
    Sends an OTP to a phone number or ABHA identifier.
    MOCK_ABHA=True: no SMS is actually sent — the OTP is stored server-side
    and echoed back in `debug_otp` so the kiosk UI can auto-fill it for demo
    purposes. Remove `debug_otp` the moment a real SMS gateway is wired up.
    """
    client = get_abha_client()
    session_id, otp_code, ttl = client.send_otp(payload.identifier, payload.purpose)

    session = models.AbhaOtpSession(
        id=session_id,
        identifier=payload.identifier,
        otp_code=otp_code,
        purpose=payload.purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
    )
    db.add(session)
    db.commit()

    return schemas.OtpRequestResponse(
        session_id=session_id,
        expires_in_seconds=ttl,
        debug_otp=otp_code if settings.MOCK_ABHA else None,
    )


@router.post("/otp/verify", response_model=schemas.TokenResponse)
def verify_otp(payload: schemas.OtpVerifyRequest, db: Session = Depends(get_db)):
    client = get_abha_client()
    try:
        session = client.verify_otp(db, payload.session_id, payload.otp_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    abha_profile = client.fetch_profile(session.identifier)

    # Find-or-create the patient by phone (or ABHA id, whichever the OTP was for).
    patient = (
        db.query(models.Patient)
        .filter(
            (models.Patient.phone == session.identifier)
            | (models.Patient.abha_id == abha_profile["abha_id"])
        )
        .first()
    )
    if patient is None:
        patient = models.Patient(
            full_name=abha_profile["full_name"] or "Unnamed Patient",
            phone=session.identifier if session.identifier.isdigit() else "",
            abha_id=abha_profile["abha_id"],
            abha_address=abha_profile["abha_address"],
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    token = create_access_token(patient.id)
    return schemas.TokenResponse(
        access_token=token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        patient_id=patient.id,
        abha=schemas.AbhaProfile(
            abha_id=abha_profile["abha_id"],
            abha_address=abha_profile["abha_address"],
            full_name=patient.full_name,
            gender=abha_profile.get("gender"),
            dob=abha_profile.get("dob"),
            mobile=abha_profile.get("mobile"),
        ),
    )


@router.post("/qr", response_model=schemas.TokenResponse)
def login_via_qr(payload: schemas.QrLoginRequest, db: Session = Depends(get_db)):
    """
    Login by scanning a patient's ABHA QR card at the kiosk. MOCK_ABHA=True:
    treats the raw QR payload as the identifier directly rather than
    decoding a real ABDM QR schema.
    """
    client = get_abha_client()
    abha_profile = client.fetch_profile(payload.qr_payload)

    patient = db.query(models.Patient).filter(models.Patient.abha_id == abha_profile["abha_id"]).first()
    if patient is None:
        patient = models.Patient(full_name="Unnamed Patient", phone="", abha_id=abha_profile["abha_id"], abha_address=abha_profile["abha_address"])
        db.add(patient)
        db.commit()
        db.refresh(patient)

    token = create_access_token(patient.id)
    return schemas.TokenResponse(
        access_token=token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        patient_id=patient.id,
        abha=schemas.AbhaProfile(
            abha_id=abha_profile["abha_id"],
            abha_address=abha_profile["abha_address"],
            full_name=patient.full_name,
        ),
    )
