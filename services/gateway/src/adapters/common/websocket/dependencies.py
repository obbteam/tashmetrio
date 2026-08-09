from fastapi import WebSocket, WebSocketException

from src.adapters.common.websocket.snapshot import Snapshot
from src.adapters.common.websocket.update import Update


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_snapshot(self, snapshot: Snapshot, websocket: WebSocket):
        await websocket.send_json(snapshot.model_dump(mode="json"))

    async def broadcast_update(self, update: Update):
        for connection in self.active_connections:
            try:
                await connection.send_json(update.model_dump(mode="json"))
            except WebSocketException:
                self.disconnect(websocket=connection)


manager = ConnectionManager()


def get_websocket_manager() -> ConnectionManager:
    return manager
