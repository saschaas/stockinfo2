"""WebSocket routes for real-time updates."""

import asyncio
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
        # Send immediate acknowledgment with current job status
        job_status = await get_job_progress_from_redis(job_id)
        last_progress = job_status.get("progress", 0)
        last_status = job_status.get("status", "queued")

        await manager.send_personal_message(
            {
                "type": "connected",
                "job_id": job_id,
                "status": last_status,
                "progress": last_progress,
                "current_step": job_status.get("current_step", "Initializing..."),
            },
            websocket,
        )

        # Poll for updates every 500ms
        while True:
            await asyncio.sleep(0.5)

            # Check for progress updates from Redis
            job_status = await get_job_progress_from_redis(job_id)
            current_progress = job_status.get("progress", 0)
            current_status = job_status.get("status", "queued")

            # Send update if progress changed
            if current_progress != last_progress or current_status != last_status:
                if current_status == "completed":
                    # Fetch and send results
                    result = await get_job_result(job_id)
                    await manager.send_personal_message(
                        {
                            "type": "complete",
                            "job_id": job_id,
                            "result": result,
                        },
                        websocket,
                    )
                    break
                elif current_status == "failed":
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "job_id": job_id,
                            "error": job_status.get("current_step", "Research failed"),
                        },
                        websocket,
                    )
                    break
                else:
                    await manager.send_personal_message(
                        {
                            "type": "progress",
                            "job_id": job_id,
                            "status": current_status,
                            "progress": current_progress,
                            "current_step": job_status.get("current_step", ""),
                        },
                        websocket,
                    )

                last_progress = current_progress
                last_status = current_status

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


async def get_job_progress_from_redis(job_id: str) -> dict:
    """Get job progress from Redis cache."""
    from backend.app.services.cache import get_job_progress

    progress = await get_job_progress(job_id)
    if progress:
        return progress

    # Fallback to database
    return await get_job_status(job_id)


async def get_job_status(job_id: str) -> dict:
    """Get current job status from database."""
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ResearchJob

    try:
        async with async_session_factory() as session:
            stmt = select(ResearchJob).where(ResearchJob.job_id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if job:
                return {
                    "status": job.status,
                    "progress": job.progress,
                    "current_step": job.current_step,
                }
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))

    return {"status": "queued", "progress": 0, "current_step": "Waiting to start..."}


async def get_job_result(job_id: str) -> dict:
    """Get job result (analysis) from database."""
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ResearchJob, StockAnalysis

    try:
        async with async_session_factory() as session:
            # Get job to find ticker
            job_stmt = select(ResearchJob).where(ResearchJob.job_id == job_id)
            job_result = await session.execute(job_stmt)
            job = job_result.scalar_one_or_none()

            if not job or not job.input_data:
                return {}

            ticker = job.input_data.get("ticker")
            if not ticker:
                return {}

            # Get latest analysis for this ticker
            analysis_stmt = (
                select(StockAnalysis)
                .where(StockAnalysis.ticker == ticker)
                .order_by(StockAnalysis.analysis_date.desc())
                .limit(1)
            )
            analysis_result = await session.execute(analysis_stmt)
            analysis = analysis_result.scalar_one_or_none()

            if analysis:
                # Helper to convert Decimal to float
                def to_float(val):
                    if val is None:
                        return None
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return None

                result = {
                    "ticker": analysis.ticker,
                    "company_name": analysis.company_name,
                    "sector": analysis.sector,
                    "industry": analysis.industry,
                    "current_price": to_float(analysis.current_price),
                    "market_cap": analysis.market_cap,
                    "pe_ratio": str(analysis.pe_ratio) if analysis.pe_ratio else None,
                    "recommendation": analysis.recommendation,
                    "confidence_score": to_float(analysis.confidence_score),
                    "recommendation_reasoning": analysis.recommendation_reasoning,
                    "risks": analysis.risks,
                    "opportunities": analysis.opportunities,
                    "rsi": to_float(analysis.rsi),
                    "sma_20": to_float(analysis.sma_20),
                    "sma_50": to_float(analysis.sma_50),
                    "data_sources": analysis.data_sources,
                    # Growth Analysis fields
                    "portfolio_allocation": to_float(analysis.portfolio_allocation),
                    "price_target_base": to_float(analysis.price_target_base),
                    "price_target_optimistic": to_float(analysis.price_target_optimistic),
                    "price_target_pessimistic": to_float(analysis.price_target_pessimistic),
                    "upside_potential": to_float(analysis.upside_potential),
                    "composite_score": to_float(analysis.composite_score),
                    "fundamental_score": to_float(analysis.fundamental_score),
                    "sentiment_score": to_float(analysis.sentiment_score),
                    "technical_score": to_float(analysis.technical_score),
                    "competitive_score": to_float(analysis.competitive_score),
                    "risk_score": to_float(analysis.risk_score),
                    "risk_level": analysis.risk_level,
                    "key_strengths": analysis.key_strengths,
                    "key_risks": analysis.key_risks,
                    "catalyst_points": analysis.catalyst_points,
                    "monitoring_points": analysis.monitoring_points,
                    "data_completeness_score": to_float(analysis.data_completeness_score),
                    "missing_data_categories": analysis.missing_data_categories,
                    "ai_summary": analysis.ai_summary,
                    "ai_reasoning": analysis.ai_reasoning,
                    # Technical Analysis
                    "technical_analysis": analysis.technical_analysis,
                }

                # Add sector comparison if sector is available
                if analysis.sector:
                    try:
                        from backend.app.services.sector_comparison import get_sector_comparison_service
                        sector_service = get_sector_comparison_service()
                        sector_comp = await sector_service.compare_stock_to_sector(
                            ticker=analysis.ticker,
                            sector=analysis.sector,
                            lookback_days=180
                        )
                        result["sector_comparison"] = sector_comp
                        logger.debug("Added sector comparison to job result", ticker=analysis.ticker)
                    except Exception as e:
                        logger.warning("Failed to add sector comparison to job result", ticker=analysis.ticker, error=str(e))
                        result["sector_comparison"] = None

                return result
    except Exception as e:
        logger.error("Failed to get job result", job_id=job_id, error=str(e))

    return {}


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
