"""
Real WebSocket connection management for streaming live vitals from a kiosk
to a doctor-portal viewer during a consultation (eSanjeevani-style). The
transport/fan-out here is real; only the "doctor portal" on the far end is
out of scope (MOCK_TELEMEDICINE just means there's no actual eSanjeevani
account wired up — any WebSocket client, including a curl/websocat test,
can play that role).

One room per consultation_id. Kiosk-side connects and pushes vitals frames;
doctor-side connects read-only and receives them. Both directions also get
a lightweight chat/event channel for consult status messages.
"""
import json
from collections import defaultdict

from fastapi import WebSocket


class TelemedicineConnectionManager:
    def __init__(self):
        # consultation_id -> set of (websocket, role)
        self._rooms: dict[str, list[tuple[WebSocket, str]]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, consultation_id: str, role: str):
        await websocket.accept()
        self._rooms[consultation_id].append((websocket, role))

    def disconnect(self, websocket: WebSocket, consultation_id: str):
        self._rooms[consultation_id] = [
            (ws, r) for (ws, r) in self._rooms.get(consultation_id, []) if ws is not websocket
        ]
        if not self._rooms[consultation_id]:
            self._rooms.pop(consultation_id, None)

    async def broadcast(self, consultation_id: str, message: dict, exclude: WebSocket | None = None):
        payload = json.dumps(message)
        stale = []
        for ws, _role in self._rooms.get(consultation_id, []):
            if ws is exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws, consultation_id)

    def room_size(self, consultation_id: str) -> int:
        return len(self._rooms.get(consultation_id, []))


manager = TelemedicineConnectionManager()
