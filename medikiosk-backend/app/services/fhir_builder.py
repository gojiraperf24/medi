"""
Deterministic FHIR R4 resource construction — real code, no LLM involved.

Designed to compose with the existing `summary.py` FHIR export: that module
already assembles the intake-interview side of the record (Condition /
QuestionnaireResponse style resources presumably); this module covers the
vitals/triage/encounter side (Observation, RiskAssessment, Encounter) so the
two can be merged into one Bundle. Keep resource `id` values patient- and
reading-scoped (not random) so re-generating a bundle for the same
patient/reading is idempotent.

Reference: https://hl7.org/fhir/R4/
"""
from datetime import datetime, timezone

from app.db import models

FHIR_VERSION = "4.0.1"

# LOINC codes for each vital sign — standard, not invented.
LOINC = {
    "systolic_bp": ("8480-6", "Systolic blood pressure"),
    "diastolic_bp": ("8462-4", "Diastolic blood pressure"),
    "heart_rate_bpm": ("8867-4", "Heart rate"),
    "spo2_percent": ("59408-5", "Oxygen saturation in Arterial blood by Pulse oximetry"),
    "temperature_c": ("8310-5", "Body temperature"),
    "glucose_mg_dl": ("2339-0", "Glucose [Mass/volume] in Blood"),
    "weight_kg": ("29463-7", "Body weight"),
    "height_cm": ("8302-2", "Body height"),
}

UCUM_UNITS = {
    "systolic_bp": "mm[Hg]",
    "diastolic_bp": "mm[Hg]",
    "heart_rate_bpm": "/min",
    "spo2_percent": "%",
    "temperature_c": "Cel",
    "glucose_mg_dl": "mg/dL",
    "weight_kg": "kg",
    "height_cm": "cm",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_patient_resource(patient: models.Patient) -> dict:
    resource = {
        "resourceType": "Patient",
        "id": patient.id,
        "identifier": [],
        "name": [{"text": patient.full_name}],
        "gender": patient.gender.value if hasattr(patient.gender, "value") else str(patient.gender),
        "telecom": [{"system": "phone", "value": patient.phone}],
    }
    if patient.dob:
        resource["birthDate"] = patient.dob
    if patient.abha_id:
        resource["identifier"].append({
            "system": "https://healthid.ndhm.gov.in",
            "value": patient.abha_id,
            "type": {"text": "ABHA Number"},
        })
    if patient.abha_address:
        resource["identifier"].append({
            "system": "https://healthid.ndhm.gov.in/address",
            "value": patient.abha_address,
            "type": {"text": "ABHA Address"},
        })
    return resource


def build_observations(patient_id: str, vitals: models.VitalsReading) -> list[dict]:
    observations = []
    recorded_at = vitals.recorded_at.isoformat() if vitals.recorded_at else _now_iso()

    for field_name, (code, display) in LOINC.items():
        value = getattr(vitals, field_name, None)
        if value is None:
            continue
        observations.append({
            "resourceType": "Observation",
            "id": f"{vitals.id}-{field_name}",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs",
                }]
            }],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": code, "display": display}],
                "text": display,
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": recorded_at,
            "valueQuantity": {
                "value": value,
                "unit": UCUM_UNITS[field_name],
                "system": "http://unitsofmeasure.org",
                "code": UCUM_UNITS[field_name],
            },
            "device": {"display": vitals.device_type} if vitals.device_type else None,
        })
    # Blood pressure is conventionally reported as ONE observation with two
    # components rather than two separate ones — add that too, since a lot
    # of downstream FHIR consumers (and eSanjeevani-style viewers) expect it.
    if vitals.systolic_bp is not None and vitals.diastolic_bp is not None:
        observations.append({
            "resourceType": "Observation",
            "id": f"{vitals.id}-bp-panel",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                }]
            }],
            "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": recorded_at,
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic"}]},
                    "valueQuantity": {"value": vitals.systolic_bp, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic"}]},
                    "valueQuantity": {"value": vitals.diastolic_bp, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
                },
            ],
        })

    return [o for o in observations if o is not None]


def build_risk_assessment(patient_id: str, triage: models.TriageResult) -> dict:
    return {
        "resourceType": "RiskAssessment",
        "id": triage.id,
        "status": "final",
        "subject": {"reference": f"Patient/{patient_id}"},
        "occurrenceDateTime": triage.created_at.isoformat() if triage.created_at else _now_iso(),
        "basis": (
            [{"reference": f"Observation/{triage.vitals_reading_id}"}]
            if triage.vitals_reading_id else []
        ),
        "prediction": [
            {"outcome": {"text": flag}, "qualitativeRisk": {"text": triage.risk_level.value if hasattr(triage.risk_level, "value") else str(triage.risk_level)}}
            for flag in (triage.flags or [{"text": "no significant risk flags"}])
        ] if triage.flags else [{
            "qualitativeRisk": {"text": triage.risk_level.value if hasattr(triage.risk_level, "value") else str(triage.risk_level)}
        }],
        "note": [{"text": r} for r in (triage.rationale or [])] + (
            [{"text": f"Recommended action: {triage.recommended_action}"}] if triage.recommended_action else []
        ),
        "method": {"text": f"Rule-based triage engine ({triage.engine_version})"},
    }


def build_encounter(patient_id: str, consultation: models.ConsultationSession) -> dict:
    status_map = {"queued": "planned", "live": "in-progress", "completed": "finished", "cancelled": "cancelled"}
    status = consultation.status.value if hasattr(consultation.status, "value") else str(consultation.status)
    return {
        "resourceType": "Encounter",
        "id": consultation.id,
        "status": status_map.get(status, "unknown"),
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "VR",
            "display": "virtual",
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "participant": (
            [{"individual": {"display": consultation.doctor_id}}] if consultation.doctor_id else []
        ),
        "period": {
            k: v for k, v in {
                "start": consultation.started_at.isoformat() if consultation.started_at else None,
                "end": consultation.ended_at.isoformat() if consultation.ended_at else None,
            }.items() if v
        },
        "serviceType": {"text": "Telemedicine consultation (eSanjeevani-style)"},
    }


def build_conditions(patient_id: str, document_scans: list[models.MedicalDocumentScan]) -> list[dict]:
    """
    One Condition resource per distinct condition name ever extracted from
    the patient's scanned documents (see services/document_ocr.py). This is
    the piece that turns "we scanned some old papers" into an actual part
    of the patient's structured medical record.
    """
    seen: dict[str, dict] = {}
    for scan in document_scans:
        for condition_name in (scan.extracted_conditions or []):
            if condition_name in seen:
                continue
            seen[condition_name] = {
                "resourceType": "Condition",
                "id": f"{scan.id}-{condition_name.lower().replace(' ', '-')}",
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                    }]
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "code": {"text": condition_name},
                "recordedDate": scan.created_at.isoformat() if scan.created_at else _now_iso(),
                "note": [{
                    "text": (
                        f"Extracted from a scanned {scan.document_type.replace('_', ' ')} "
                        f"(confidence {scan.confidence:.2f}). Not independently verified by a clinician."
                    )
                }],
            }
    return list(seen.values())


def build_bundle(
    patient: models.Patient,
    vitals_list: list[models.VitalsReading],
    triage_list: list[models.TriageResult],
    consultations: list[models.ConsultationSession] | None = None,
    document_scans: list[models.MedicalDocumentScan] | None = None,
    extra_resources: list[dict] | None = None,
) -> dict:
    """
    Assembles a `collection`-type Bundle. Swap to `document` or `transaction`
    type if this feeds directly into a health information exchange rather
    than being downloaded/printed.
    """
    entries = [{"resource": build_patient_resource(patient)}]

    for vitals in vitals_list:
        for obs in build_observations(patient.id, vitals):
            entries.append({"resource": obs})

    for triage in triage_list:
        entries.append({"resource": build_risk_assessment(patient.id, triage)})

    for consultation in (consultations or []):
        entries.append({"resource": build_encounter(patient.id, consultation)})

    for condition in build_conditions(patient.id, document_scans or []):
        entries.append({"resource": condition})

    # Slot for resources built elsewhere (e.g. summary.py's intake/Condition
    # resources) so a single combined bundle can be produced by the caller.
    for resource in (extra_resources or []):
        entries.append({"resource": resource})

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": _now_iso(),
        "meta": {"profile": [f"http://hl7.org/fhir/{FHIR_VERSION}/StructureDefinition/Bundle"]},
        "entry": entries,
    }
