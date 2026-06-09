from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Diccionario: incident_id -> lista de WebSockets activos (cliente + mecánico)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, incident_id: str):
        await websocket.accept()
        if incident_id not in self.active_connections:
            self.active_connections[incident_id] = []
        self.active_connections[incident_id].append(websocket)
        print(f"✅ Conexión WS establecida para incidente {incident_id}. Total en sala: {len(self.active_connections[incident_id])}")

    def disconnect(self, websocket: WebSocket, incident_id: str):
        if incident_id in self.active_connections:
            if websocket in self.active_connections[incident_id]:
                self.active_connections[incident_id].remove(websocket)
            if not self.active_connections[incident_id]:
                del self.active_connections[incident_id]
        print(f"❌ Conexión WS cerrada para incidente {incident_id}")

    async def broadcast(self, message: str, incident_id: str):
        """Envía el mensaje a todos los clientes conectados a este incidente."""
        if incident_id in self.active_connections:
            for connection in self.active_connections[incident_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"⚠️ Error enviando WS: {e}")

manager = ConnectionManager()

@router.websocket("/{incident_id}")
async def websocket_endpoint(websocket: WebSocket, incident_id: str):
    """
    Endpoint WebSocket. 
    El mecánico se conecta aquí y envía {"lat": x, "lng": y}.
    El servidor lo retransmite al cliente que está en esta misma sala (incident_id).
    """
    await manager.connect(websocket, incident_id)
    try:
        while True:
            data = await websocket.receive_text()
            
            # Imprimimos en consola solo para desarrollo (el script)
            # print(f"📍 GPS Recibido [{incident_id}]: {data}")
            
            # Retransmitir a los que estén escuchando (el cliente)
            await manager.broadcast(data, incident_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, incident_id)
