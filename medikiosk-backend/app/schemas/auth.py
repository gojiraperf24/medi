from datetime import datetime
from pydantic import BaseModel, Field


class OtpRequest(BaseModel):
    identifier: str = Field(..., description="Phone number or ABHA number/address to send OTP to")
    purpose: str = Field("login", pattern="^(login|link_abha)$")


class OtpRequestResponse(BaseModel):
    session_id: str
    expires_in_seconds: int
    # Only present because MOCK_ABHA=True — a real integration would never echo the OTP back.
    debug_otp: str | None = None


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp_code: str


class AbhaProfile(BaseModel):
    abha_id: str
    abha_address: str
    full_name: str
    gender: str | None = None
    dob: str | None = None
    mobile: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    patient_id: str
    abha: AbhaProfile | None = None


class QrLoginRequest(BaseModel):
    qr_payload: str = Field(..., description="Raw string encoded in the patient's ABHA QR card")
