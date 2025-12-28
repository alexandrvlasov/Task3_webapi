from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New WebSocket connection. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        for ws in list(self.active_connections):
            try:
                await ws.send_json(data)
            except Exception:
                await self.disconnect(ws)

    async def handle(self, data, websocket: WebSocket):
            await self.broadcast({"type": "echo", "message": data})

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        await websocket.close()
        print(f"WebSocket disconnected. Total: {len(self.active_connections)}")
