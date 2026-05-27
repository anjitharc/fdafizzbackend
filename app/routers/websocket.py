from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # order_id -> list of WebSocket connections
        self.order_connections: Dict[int, List[WebSocket]] = {}
        # staff_id -> list of WebSocket connections (for location tracking)
        self.location_connections: Dict[int, List[WebSocket]] = {}

    async def connect_order(self, websocket: WebSocket, order_id: int):
        """Connect a client to order updates."""
        await websocket.accept()
        if order_id not in self.order_connections:
            self.order_connections[order_id] = []
        self.order_connections[order_id].append(websocket)

    async def connect_location(self, websocket: WebSocket, staff_id: int):
        """Connect a client to delivery staff location updates."""
        await websocket.accept()
        if staff_id not in self.location_connections:
            self.location_connections[staff_id] = []
        self.location_connections[staff_id].append(websocket)

    def disconnect_order(self, websocket: WebSocket, order_id: int):
        """Disconnect a client from order updates."""
        if order_id in self.order_connections:
            self.order_connections[order_id] = [
                ws for ws in self.order_connections[order_id] if ws != websocket
            ]
            if not self.order_connections[order_id]:
                del self.order_connections[order_id]

    def disconnect_location(self, websocket: WebSocket, staff_id: int):
        """Disconnect a client from location updates."""
        if staff_id in self.location_connections:
            self.location_connections[staff_id] = [
                ws for ws in self.location_connections[staff_id] if ws != websocket
            ]
            if not self.location_connections[staff_id]:
                del self.location_connections[staff_id]

    async def broadcast_order_update(self, order_id: int, data: dict):
        """Broadcast order status update to all connected clients."""
        if order_id in self.order_connections:
            message = json.dumps({"type": "order_update", "order_id": order_id, **data})
            disconnected = []
            for websocket in self.order_connections[order_id]:
                try:
                    await websocket.send_text(message)
                except Exception:
                    disconnected.append(websocket)
            # Clean up disconnected
            for ws in disconnected:
                self.disconnect_order(ws, order_id)

    async def broadcast_location_update(self, staff_id: int, data: dict):
        """Broadcast delivery staff location update to all connected clients."""
        if staff_id in self.location_connections:
            message = json.dumps({"type": "location_update", "staff_id": staff_id, **data})
            disconnected = []
            for websocket in self.location_connections[staff_id]:
                try:
                    await websocket.send_text(message)
                except Exception:
                    disconnected.append(websocket)
            # Clean up disconnected
            for ws in disconnected:
                self.disconnect_location(ws, staff_id)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/order/{order_id}")
async def websocket_order(websocket: WebSocket, order_id: int):
    """WebSocket endpoint for real-time order status updates."""
    await manager.connect_order(websocket, order_id)
    try:
        while True:
            # Keep connection alive, listen for any client messages
            data = await websocket.receive_text()
            # Client can send ping messages to keep alive
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect_order(websocket, order_id)


@router.websocket("/delivery/{staff_id}/location")
async def websocket_delivery_location(websocket: WebSocket, staff_id: int):
    """WebSocket endpoint for real-time delivery staff location tracking."""
    await manager.connect_location(websocket, staff_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect_location(websocket, staff_id)
