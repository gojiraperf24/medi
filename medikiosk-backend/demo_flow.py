"""
Walks the full patient journey against a running server, hitting every
module once. Useful both as a smoke test and as a scripted demo for judges.

Run the server first:  uvicorn app.main:app --reload
Then:                   python demo_flow.py
"""
import time
import requests

BASE = "http://localhost:8000"


def step(label, fn):
    print(f"\n--- {label} ---")
    result = fn()
    print(result)
    return result


def main():
    # 1. ABHA-style OTP login (mocked)
    otp_req = step("Request OTP", lambda: requests.post(
        f"{BASE}/auth/otp/request", json={"identifier": "9876543210", "purpose": "login"}
    ).json())
    otp_verify = step("Verify OTP", lambda: requests.post(
        f"{BASE}/auth/otp/verify",
        json={"session_id": otp_req["session_id"], "otp_code": otp_req["debug_otp"]},
    ).json())
    patient_id = otp_verify["patient_id"]
    token = otp_verify["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Fill in patient details (registration completes profile)
    step("Fetch patient", lambda: requests.get(f"{BASE}/patients/{patient_id}", headers=headers).json())

    # 3. Voice-guided intake (mocked Bhashini)
    step("Guided intake: greeting", lambda: requests.post(
        f"{BASE}/voice/guided-intake/next",
        json={"patient_id": patient_id, "language": "hi"},
    ).json())
    step("STT of patient's spoken answer", lambda: requests.post(
        f"{BASE}/voice/stt", json={"patient_id": patient_id, "language": "hi"}
    ).json())

    # 4. Old medical documents (mocked OCR, real keyword extraction)
    with open(__file__, "rb") as fake_image:  # any file works — content isn't actually read as an image
        history = step("Scan an old prescription/report", lambda: requests.post(
            f"{BASE}/documents/scan",
            data={"patient_id": patient_id},
            files={"image": ("prescription.jpg", fake_image, "image/jpeg")},
        ).json())
    print(f"  => detected conditions: {history['extracted_conditions']}, medications: {history['extracted_medications']}")

    # 5. Device vitals ingestion (real endpoint, simulated device payloads)
    step("Ingest pulse oximeter reading", lambda: requests.post(
        f"{BASE}/devices/ingest",
        json={
            "kiosk_id": "kiosk-001", "patient_id": patient_id, "device_type": "pulse_oximeter",
            "reading": {"spo2": 91, "pulse": 102},
        },
    ).json())
    vitals = step("Ingest BP cuff reading", lambda: requests.post(
        f"{BASE}/devices/ingest",
        json={
            "kiosk_id": "kiosk-001", "patient_id": patient_id, "device_type": "bp_cuff",
            "reading": {"systolic": 148, "diastolic": 95, "pulse": 100},
        },
    ).json())

    # 5. Real rule-based triage over the latest reading
    triage = step("Run triage", lambda: requests.post(
        f"{BASE}/triage/run", json={"patient_id": patient_id, "vitals_reading_id": vitals["id"]}
    ).json())
    print(f"  => risk level: {triage['risk_level']}, flags: {triage['flags']}")

    # 6. Medicine scan (mocked recognition, real Jan Aushadhi lookup)
    step("Lookup generic alternative", lambda: requests.get(
        f"{BASE}/medicine/lookup", params={"compound": "paracetamol"}
    ).json())

    # 7. Telemedicine consultation session (REST side; WS stream tested separately)
    consult = step("Create consultation", lambda: requests.post(
        f"{BASE}/telemedicine/consultations",
        json={"patient_id": patient_id, "kiosk_id": "kiosk-001"},
    ).json())
    step("Start consultation", lambda: requests.post(
        f"{BASE}/telemedicine/consultations/{consult['id']}/start"
    ).json())

    # 8. FHIR export tying it all together
    bundle = step("Generate FHIR bundle", lambda: requests.post(
        f"{BASE}/fhir/patient/{patient_id}/bundle"
    ).json())
    print(f"  => bundle has {len(bundle['entry'])} resources")


if __name__ == "__main__":
    main()
