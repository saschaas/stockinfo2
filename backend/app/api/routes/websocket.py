"""WebSocket routes for real-time updates."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Connect a client to a channel."""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info("WebSocket connected", channel=channel)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Disconnect a client from a channel."""
        if channel in self.active_connections:
            self.active_connections[channel].remove(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]
        logger.info("WebSocket disconnected", channel=channel)

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """Send a message to a specific client."""
        await websocket.send_json(message)

    async def broadcast(self, message: dict, channel: str) -> None:
        """Broadcast a message to all clients in a channel."""
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to send message", error=str(e))

    async def broadcast_all(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        for channel, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to send message", error=str(e))


# Global connection manager
manager = ConnectionManager()


@router.websocket("/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for tracking job progress.

    Clients connect to receive real-time updates about research job progress.
    """
    channel = f"job:{job_id}"
    await manager.connect(websocket, channel)

    try:
        while True:
            # Wait for messages from client (ping/pong or commands)
            data = await websocket.receive_text()

            if data == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
            elif data == "status":
                # Send current job status
                # TODO: Get actual job status from database/Celery
                await manager.send_personal_message(
                    {
                        "type": "status",
                        "job_id": job_id,
                        "status": "running",
                        "progress": 50,
                        "current_step": "Fetching stock data",
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


@router.websocket("/market")
async def websocket_market(websocket: WebSocket) -> None:
    """WebSocket endpoint for market updates.

    Clients receive real-time market sentiment updates.
    """
    channel = "market"
    await manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket) -> None:
    """WebSocket endpoint for system notifications.

    Clients receive notifications about:
    - New 13F filings detected
    - Market sentiment updates
    - Job completions
    - Errors
    """
    channel = "notifications"
    await manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


# Utility functions for sending updates from other parts of the application
async def send_job_progress(
    job_id: str,
    progress: int,
    current_step: str,
    status: str = "running",
) -> None:
    """Send job progress update to connected clients."""
    await manager.broadcast(
        {
            "type": "progress",
            "job_id": job_id,
            "progress": progress,
            "current_step": current_step,
            "status": status,
        },
        f"job:{job_id}",
    )


async def send_job_complete(
    job_id: str,
    result: dict[str, Any],
) -> None:
    """Send job completion notification."""
    await manager.broadcast(
        {
            "type": "complete",
            "job_id": job_id,
            "result": result,
        },
        f"job:{job_id}",
    )


async def send_job_error(
    job_id: str,
    error: str,
    suggestion: str | None = None,
) -> None:
    """Send job error notification."""
    await manager.broadcast(
        {
            "type": "error",
            "job_id": job_id,
            "error": error,
            "suggestion": suggestion,
        },
        f"job:{job_id}",
    )


async def send_notification(
    message: str,
    notification_type: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """Send system notification to all connected clients."""
    await manager.broadcast(
        {
            "type": "notification",
            "notification_type": notification_type,
            "message": message,
            "data": data or {},
        },
        "notifications",
    )
