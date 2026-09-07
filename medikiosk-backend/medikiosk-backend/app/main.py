from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import Base, engine
from app.db import models  # noqa: F401 - ensures models are registered on Base before create_all
from app.api.routes import auth, patients, vitals, devices, triage, medicine, voice, fhir, telemedicine, documents

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "MediKiosk backend — AI-powered clinical intake kiosk (SIH26047). "
        "Core intake/vitals/triage/FHIR modules are fully implemented; "
        "ABHA, Bhashini voice, and telemedicine doctor-side are mocked "
        "behind interfaces designed to be swapped for real integrations "
        "(see MOCK_ABHA / MOCK_BHASHINI / MOCK_TELEMEDICINE in core/config.py)."
    ),
    version="0.1.0",
)

# Wide-open CORS for kiosk/demo use. Tighten to specific kiosk/doctor-portal
# origins before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # For the hackathon build this creates tables directly from the models.
    # Switch to Alembic migrations before this schema needs to evolve
    # without dropping data.
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health_check():
    return {
        "status": "ok",
        "mock_abha": settings.MOCK_ABHA,
        "mock_bhashini": settings.MOCK_BHASHINI,
        "mock_telemedicine": settings.MOCK_TELEMEDICINE,
    }


app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(vitals.router)
app.include_router(devices.router)
app.include_router(triage.router)
app.include_router(medicine.router)
app.include_router(voice.router)
app.include_router(fhir.router)
app.include_router(telemedicine.router)
app.include_router(documents.router)
