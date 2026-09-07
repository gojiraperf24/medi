"""
Standalone MQTT -> REST bridge. Run this as a separate process on the kiosk
(or a machine on the same LAN as the Mosquitto broker) if/when real hardware
publishing over MQTT is available. It is NOT imported by the FastAPI app —
run it directly: `python -m app.services.mqtt_bridge`.

Expected topic convention (adjust to match your firmware):
    kiosk/<kiosk_id>/<device_type>/reading
Payload: JSON matching DeviceIngestPayload's `reading` field, e.g.
    {"spo2": 97, "pulse": 78}

Requires `paho-mqtt` (see requirements.txt) and a running Mosquitto broker
— neither is assumed to exist in this environment, so this file is provided
as ready-to-run scaffolding rather than something exercised by the API tests.
"""
import json
import os

import requests

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - optional dependency, only needed to actually run the bridge
    mqtt = None

BACKEND_INGEST_URL = os.environ.get("MEDIKIOSK_INGEST_URL", "http://localhost:8000/devices/ingest")
MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_FILTER = "kiosk/+/+/reading"


def _on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[mqtt_bridge] connected (reason_code={reason_code}), subscribing to {MQTT_TOPIC_FILTER}")
    client.subscribe(MQTT_TOPIC_FILTER)


def _on_message(client, userdata, msg):
    try:
        _, kiosk_id, device_type, _ = msg.topic.split("/")
        reading = json.loads(msg.payload.decode("utf-8"))
        patient_id = reading.pop("patient_id", None)
        if not patient_id:
            print(f"[mqtt_bridge] dropped message on {msg.topic}: no patient_id in payload")
            return

        response = requests.post(
            BACKEND_INGEST_URL,
            json={
                "kiosk_id": kiosk_id,
                "patient_id": patient_id,
                "device_type": device_type,
                "reading": reading,
            },
            timeout=5,
        )
        response.raise_for_status()
        print(f"[mqtt_bridge] forwarded {device_type} reading for patient {patient_id}: {response.status_code}")
    except Exception as exc:  # noqa: BLE001 - bridge should never crash on a bad message
        print(f"[mqtt_bridge] error handling message on {msg.topic}: {exc}")


def run():
    if mqtt is None:
        raise RuntimeError("paho-mqtt is not installed. `pip install paho-mqtt` to run this bridge.")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    run()
