"""
Mock of the ABDM (Ayushman Bharat Digital Mission) ABHA identity flow.

Real integration reference (for when sandbox credentials arrive):
  https://sandbox.abdm.gov.in  — ABHA number/address creation, OTP via
  Aadhaar-linked mobile, profile fetch (POST /v3/enrollment/*, /v3/profile/*).

Why mocked: the real sandbox requires a registered ABDM facility ID and
approval turnaround that doesn't fit a hackathon timeline. This module
keeps the exact request/response *shape* of a real integration so swapping
it out later is a one-file change (see `AbhaClient` below — swap
`MockAbhaClient` for a real HTTP client implementing the same interface).
"""
import random
import string
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models


class AbhaClient(ABC):
    """Interface a real ABDM sandbox/production client must implement."""

    @abstractmethod
    def send_otp(self, identifier: str, purpose: str) -> tuple[str, str, int]:
        """Returns (session_id, otp_code_or_empty, expires_in_seconds)."""

    @abstractmethod
    def verify_otp(self, db: Session, session_id: str, otp_code: str) -> models.AbhaOtpSession:
        ...

    @abstractmethod
    def fetch_profile(self, identifier: str) -> dict:
        """Returns an ABHA profile dict: abha_id, abha_address, full_name, gender, dob, mobile."""


class MockAbhaClient(AbhaClient):
    OTP_TTL_SECONDS = 300

    def send_otp(self, identifier: str, purpose: str) -> tuple[str, str, int]:
        otp = "".join(random.choices(string.digits, k=6))
        session_id = "otp_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
        return session_id, otp, self.OTP_TTL_SECONDS

    def verify_otp(self, db: Session, session_id: str, otp_code: str) -> models.AbhaOtpSession:
        session = db.query(models.AbhaOtpSession).filter_by(id=session_id).first()
        if session is None:
            raise ValueError("Unknown or expired OTP session")

        # SQLite doesn't actually preserve timezone info on round-trip, so a
        # value written as tz-aware can come back naive. Normalize both
        # sides to aware-UTC before comparing to avoid a TypeError.
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("OTP expired")
        if session.attempts >= 5:
            raise ValueError("Too many attempts, request a new OTP")

        session.attempts += 1
        if session.otp_code != otp_code:
            db.commit()
            raise ValueError("Incorrect OTP")

        session.verified = True
        db.commit()
        db.refresh(session)
        return session

    def fetch_profile(self, identifier: str) -> dict:
        """
        Deterministically synthesizes a plausible-looking ABHA profile from
        the identifier so demos are repeatable. Never a real government record.
        """
        digest = abs(hash(identifier)) % 10**14
        abha_id = f"{digest:014d}"
        abha_id_fmt = f"{abha_id[0:2]}-{abha_id[2:6]}-{abha_id[6:10]}-{abha_id[10:14]}"
        return {
            "abha_id": abha_id_fmt,
            "abha_address": f"patient{digest % 100000}@abdm",
            "full_name": "",  # left blank — collected at kiosk if not resolvable
            "gender": None,
            "dob": None,
            "mobile": identifier if identifier.isdigit() else None,
        }


def get_abha_client() -> AbhaClient:
    # Swap for a real client here once ABDM sandbox credentials are available:
    #   if not settings.MOCK_ABHA: return RealAbhaClient(...)
    return MockAbhaClient()
