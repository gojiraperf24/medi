# MediKiosk Backend (SIH26047)

FastAPI backend for the AI-powered clinical intake kiosk. Built to demo
end-to-end; core clinical logic is real, government/telemedicine
integrations are mocked behind swappable interfaces (see below).

## What's real vs. mocked

| Module | Status | Notes |
|---|---|---|
| Patient registration & lookup | **Real** | `app/api/routes/patients.py` |
| OTP login / session tokens | **Real** | JWT issuing is real; OTP delivery is mocked (see Auth below) |
| Vitals recording, history, offline-sync batching | **Real** | idempotent via `client_reading_id` |
| Device sensor ingestion endpoint | **Real endpoint**, no real hardware paired | `/devices/ingest`; `services/mqtt_bridge.py` is ready-to-run scaffolding for when real MQTT hardware exists |
| Rule-based triage engine | **Real** | deterministic thresholds in `core/config.py`, logic in `services/triage_engine.py` — no LLM involved. Now also context-aware of known conditions from scanned documents. |
| Old document scan (prescriptions/reports) | **Mocked OCR, real extraction** | `services/document_ocr.py` — OCR text is canned, but the keyword-based condition/medication extraction is real and feeds triage + FHIR |
| FHIR R4 bundle export | **Real** | `services/fhir_builder.py` — Patient, Observation, RiskAssessment, Encounter, and now Condition resources from document history |
| Telemedicine WebSocket streaming | **Real transport**, no real doctor-portal account | `app/ws/`, `/telemedicine/consultations/{id}/stream` |
| ABHA/ABDM identity | **Mocked** | `services/abha_mock.py` — same interface a real ABDM sandbox client would implement |
| Bhashini voice (STT/TTS/guided intake) | **Mocked** | `services/bhashini_mock.py` — canned transcripts/audio refs, real script structure |
| Medicine packaging recognition (OCR/compound ID) | **Mocked** | `services/medicine_recognition.py` — recognition is fake, the Jan Aushadhi price lookup table is real |

Every mock module has a docstring explaining exactly what a real
integration would need and where to plug it in.

## Quickstart

```bash
python -m venv venv && source venv/bin/activate   # or your usual workflow
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Server comes up on `http://localhost:8000`. Interactive API docs at
`http://localhost:8000/docs` (Swagger) — every endpoint below is there.

Run the full patient journey against it:
```bash
python demo_flow.py
```

## Project layout

```
app/
  main.py                  FastAPI app, router wiring, CORS, startup table creation
  core/
    config.py               Settings (.env-driven) + triage thresholds
    security.py              JWT issuing/verification
  db/
    database.py              SQLAlchemy engine/session
    models.py                 ORM models (Patient, VitalsReading, TriageResult, ...)
  schemas/                  Pydantic request/response models, one file per domain
  services/
    abha_mock.py              ABHA/ABDM identity (mocked, swappable interface)
    bhashini_mock.py          Voice STT/TTS + guided-intake script (mocked)
    triage_engine.py          Real rule-based risk scoring
    fhir_builder.py           Real FHIR R4 resource/bundle construction
    medicine_recognition.py   Mocked OCR + real Jan Aushadhi lookup table
    mqtt_bridge.py            Standalone MQTT->REST bridge (run separately, needs real broker)
  ws/
    telemedicine_manager.py   WebSocket room/connection manager
  api/routes/                One router per domain, all included in main.py
demo_flow.py                 Scripted walk through every module
requirements.txt
.env.example
```

## API surface

- `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/qr` — login
- `POST /patients`, `GET /patients/{id}`, `GET /patients?phone=` — registration/lookup
- `POST /vitals`, `GET /vitals/patient/{id}`, `POST /vitals/sync-batch` — vitals + offline sync
- `POST /devices/ingest` — sensor readings from kiosk hardware drivers
- `POST /triage/run`, `GET /triage/patient/{id}` — risk scoring
- `POST /medicine/scan`, `GET /medicine/lookup` — medicine recognition + generics
- `POST /documents/scan`, `GET /documents/patient/{id}`, `GET /documents/patient/{id}/history` — old prescription/report OCR + rolled-up history
- `POST /voice/stt`, `POST /voice/tts`, `POST /voice/guided-intake/next` — multilingual voice flow
- `POST /fhir/patient/{id}/bundle`, `GET /fhir/patient/{id}/bundles` — FHIR export
- `POST /telemedicine/consultations` (+ `/start`, `/end`), `WS /telemedicine/consultations/{id}/stream`

## Integrating with your existing `ontology.py` / `interview.py` / `summary.py`

This backend was built as a standalone project since those files weren't
available to build against directly. Two integration points are ready:

1. **Guided intake**: `app/services/bhashini_mock.py`'s `GUIDED_INTAKE_STEPS`
   mirrors what a state-machine-driven interview script looks like — swap
   it for calls into your existing `interview.py` state machine so voice
   guidance and the deterministic interview logic share one source of truth.
2. **FHIR export**: `services/fhir_builder.build_bundle()` takes an
   `extra_resources` list specifically so your `summary.py` export (likely
   producing Condition/QuestionnaireResponse resources from the interview
   side) can be merged into the same Bundle as the vitals/triage/encounter
   resources this backend produces.

## Moving from mocked to real integrations

- **ABHA**: get ABDM sandbox credentials + facility registration, then
  implement `AbhaClient` in `abha_mock.py` against the real
  `/v3/enrollment`, `/v3/profile` endpoints; flip `MOCK_ABHA=false`.
- **Bhashini**: get a Bhashini API key, implement `VoiceClient` against the
  real `/pipeline` endpoint; flip `MOCK_BHASHINI=false`.
- **Telemedicine**: point `doctor_id` at a real eSanjeevani/doctor-portal
  identity and have that portal connect to the same WebSocket URL with
  `role=doctor` — no code change needed on this side, the transport is
  already real.
- **Device hardware**: either POST straight to `/devices/ingest` from your
  kiosk's BLE/USB driver code, or run `services/mqtt_bridge.py` next to a
  Mosquitto broker if you're bridging from MQTT-publishing firmware.
