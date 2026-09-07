"""
Central configuration for the MediKiosk backend.
Reads from environment variables (.env) with sane local-dev defaults.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    APP_NAME: str = "MediKiosk Backend"
    ENV: str = "development"
    DEBUG: bool = True

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero setup.
    # Point DATABASE_URL at Postgres for anything beyond local dev / demo.
    DATABASE_URL: str = "sqlite:///./medikiosk.db"

    # --- Auth / Security ---
    JWT_SECRET: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours, kiosk sessions are long

    # --- Mock integration toggles ---
    # These stay True until real government / third-party credentials exist.
    MOCK_ABHA: bool = True
    MOCK_BHASHINI: bool = True
    MOCK_TELEMEDICINE: bool = True

    # --- Mock external endpoints (used only for realism in mock responses) ---
    ABHA_SANDBOX_BASE_URL: str = "https://abhasbx.abdm.gov.in/abha/api/v3"
    BHASHINI_BASE_URL: str = "https://bhashini.gov.in/api"

    # --- Triage thresholds (rule-based, deterministic — see services/triage_engine.py) ---
    TRIAGE_THRESHOLDS: dict = {
        "systolic_bp_high": 140,
        "diastolic_bp_high": 90,
        "systolic_bp_crisis": 180,
        "diastolic_bp_crisis": 120,
        "spo2_low": 94,
        "spo2_critical": 90,
        "heart_rate_low": 50,
        "heart_rate_high": 100,
        "temp_fever_c": 38.0,
        "temp_high_fever_c": 39.5,
        "glucose_fasting_high": 126,   # mg/dL
        "glucose_random_high": 200,    # mg/dL
        "glucose_low": 70,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
