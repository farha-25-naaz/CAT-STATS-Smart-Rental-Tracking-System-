"""Phase 3 — shared WebSocket connection manager.

A single module-level ``manager`` instance is imported by both main.py and
ingest_routes.py so every request broadcasts through the same connection pool.
"""

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001 - client vanished mid-send
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


# Singleton — import THIS object, do not construct your own.
manager = ConnectionManager()
