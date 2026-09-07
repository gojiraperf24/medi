"""
ORM models. Kept intentionally flat (one table per concern) so the mapping
to FHIR resources in services/fhir_builder.py stays straightforward:
Patient -> Patient, VitalsReading -> Observation, TriageResult -> RiskAssessment,
ConsultationSession -> Encounter.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Enum, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class RiskLevel(str, enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class ConsultationStatus(str, enum.Enum):
    queued = "queued"
    live = "live"
    completed = "completed"
    cancelled = "cancelled"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # ABHA (Ayushman Bharat Digital Mission) linkage — mocked until sandbox
    # credentials exist. See services/abha_mock.py.
    abha_id: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    abha_address: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. name@abdm

    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(15), index=True)
    dob: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    gender: Mapped[Gender] = mapped_column(Enum(Gender), default=Gender.unknown)
    preferred_language: Mapped[str] = mapped_column(String(10), default="hi")  # ISO code, Bhashini-compatible

    village_or_kiosk_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    vitals: Mapped[list["VitalsReading"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    triage_results: Mapped[list["TriageResult"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    consultations: Mapped[list["ConsultationSession"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    document_scans: Mapped[list["MedicalDocumentScan"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class AbhaOtpSession(Base):
    """Short-lived OTP challenge for ABHA / phone login. Mocked end-to-end."""
    __tablename__ = "abha_otp_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    identifier: Mapped[str] = mapped_column(String(64), index=True)  # phone, Aadhaar-ref, or ABHA number
    otp_code: Mapped[str] = mapped_column(String(6))
    purpose: Mapped[str] = mapped_column(String(20), default="login")  # login | link_abha
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class VitalsReading(Base):
    __tablename__ = "vitals_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)

    # "device" = came through the sensor-ingestion endpoint (real or MQTT-style push),
    # "manual" = staff/kiosk UI typed it in, "offline_sync" = batched up from a kiosk
    # that was offline and is now flushing its local queue.
    source: Mapped[str] = mapped_column(String(20), default="manual")
    device_type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # pulse_oximeter, bp_cuff, glucometer, scale, thermometer

    systolic_bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic_bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    glucose_mg_dl: Mapped[float | None] = mapped_column(Float, nullable=True)
    glucose_context: Mapped[str | None] = mapped_column(String(10), nullable=True)  # fasting | random | postprandial
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Idempotency key so an offline kiosk can safely retry a batch sync
    # without creating duplicate readings.
    client_reading_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)  # when actually taken
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)     # when server received it

    patient: Mapped["Patient"] = relationship(back_populates="vitals")


class TriageResult(Base):
    __tablename__ = "triage_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    vitals_reading_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vitals_readings.id"), nullable=True)

    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.low)
    flags: Mapped[list] = mapped_column(JSON, default=list)       # e.g. ["hypertension_stage2", "hypoxia"]
    rationale: Mapped[list] = mapped_column(JSON, default=list)   # human-readable reasons, one per flag
    recommended_action: Mapped[str] = mapped_column(Text, default="")

    engine_version: Mapped[str] = mapped_column(String(20), default="rule-based-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    patient: Mapped["Patient"] = relationship(back_populates="triage_results")


class MedicineScan(Base):
    """Result of scanning medicine packaging for active compound + generic alternative."""
    __tablename__ = "medicine_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patients.id"), nullable=True)

    image_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # storage key / path
    detected_brand_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    detected_compound: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    jan_aushadhi_alternatives: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ConsultationSession(Base):
    """A telemedicine session (eSanjeevani-style) — real-time vitals stream to a doctor."""
    __tablename__ = "consultation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # external doctor-portal identifier

    status: Mapped[ConsultationStatus] = mapped_column(Enum(ConsultationStatus), default=ConsultationStatus.queued)
    kiosk_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    patient: Mapped["Patient"] = relationship(back_populates="consultations")


class FHIRBundleRecord(Base):
    """Stored snapshot of a generated FHIR R4 bundle (audit trail / re-export)."""
    __tablename__ = "fhir_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    bundle_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MedicalDocumentScan(Base):
    """
    A scanned prescription, lab report, or discharge summary — the patient's
    PAST medical history, as opposed to MedicineScan which is about
    identifying a CURRENT medicine's generic alternative. Extracted
    conditions/medications feed into triage context and the FHIR bundle.
    """
    __tablename__ = "medical_document_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)

    image_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_type: Mapped[str] = mapped_column(String(30), default="unknown")  # prescription | lab_report | discharge_summary | unknown
    ocr_raw_text: Mapped[str] = mapped_column(Text, default="")
    document_date_text: Mapped[str | None] = mapped_column(String(40), nullable=True)  # as found in the document, unparsed

    extracted_conditions: Mapped[list] = mapped_column(JSON, default=list)   # e.g. ["diabetes", "hypertension"]
    extracted_medications: Mapped[list] = mapped_column(JSON, default=list)  # e.g. ["Metformin", "Amlodipine"]
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    patient: Mapped["Patient"] = relationship(back_populates="document_scans")


class VoiceInteractionLog(Base):
    """Log of STT/TTS turns during a voice-guided intake, for debugging + the multilingual demo."""
    __tablename__ = "voice_interaction_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patients.id"), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="hi")
    direction: Mapped[str] = mapped_column(String(4))  # "stt" or "tts"
    input_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # audio blob ref, if any
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
