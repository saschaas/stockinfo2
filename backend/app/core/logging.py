"""Logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from backend.app.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""

    # Determine log level
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Shared processors for both structlog and stdlib
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Development: colored console output
    # Production: JSON output
    if settings.debug:
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name."""
    return structlog.get_logger(name)


class RequestLogger:
    """Middleware for logging HTTP requests."""

    def __init__(self) -> None:
        self.logger = get_logger("http")

    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str | None = None,
        user_agent: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Log an HTTP request."""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        if client_ip:
            log_data["client_ip"] = client_ip
        if user_agent:
            log_data["user_agent"] = user_agent
        if extra:
            log_data.update(extra)

        if status_code >= 500:
            self.logger.error("request_error", **log_data)
        elif status_code >= 400:
            self.logger.warning("request_client_error", **log_data)
        else:
            self.logger.info("request", **log_data)


class TaskLogger:
    """Logger for Celery tasks."""

    def __init__(self, task_name: str) -> None:
        self.logger = get_logger(f"task.{task_name}")
        self.task_name = task_name

    def started(self, task_id: str, **kwargs: Any) -> None:
        """Log task start."""
        self.logger.info("task_started", task_id=task_id, **kwargs)

    def completed(self, task_id: str, duration_s: float, **kwargs: Any) -> None:
        """Log task completion."""
        self.logger.info(
            "task_completed",
            task_id=task_id,
            duration_s=round(duration_s, 2),
            **kwargs,
        )

    def failed(self, task_id: str, error: str, **kwargs: Any) -> None:
        """Log task failure."""
        self.logger.error(
            "task_failed",
            task_id=task_id,
            error=error,
            **kwargs,
        )

    def progress(self, task_id: str, progress: int, message: str, **kwargs: Any) -> None:
        """Log task progress."""
        self.logger.debug(
            "task_progress",
            task_id=task_id,
            progress=progress,
            message=message,
            **kwargs,
        )


class AgentLogger:
    """Logger for AI agents."""

    def __init__(self, agent_name: str) -> None:
        self.logger = get_logger(f"agent.{agent_name}")
        self.agent_name = agent_name

    def invoked(self, **kwargs: Any) -> None:
        """Log agent invocation."""
        self.logger.info("agent_invoked", **kwargs)

    def completed(self, duration_s: float, **kwargs: Any) -> None:
        """Log agent completion."""
        self.logger.info(
            "agent_completed",
            duration_s=round(duration_s, 2),
            **kwargs,
        )

    def error(self, error: str, **kwargs: Any) -> None:
        """Log agent error."""
        self.logger.error("agent_error", error=error, **kwargs)

    def llm_call(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        duration_ms: float,
        **kwargs: Any,
    ) -> None:
        """Log LLM API call."""
        self.logger.debug(
            "llm_call",
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )


class DataSourceLogger:
    """Logger for external data source calls."""

    def __init__(self, source_name: str) -> None:
        self.logger = get_logger(f"datasource.{source_name}")
        self.source_name = source_name

    def request(self, endpoint: str, **kwargs: Any) -> None:
        """Log API request."""
        self.logger.debug("api_request", endpoint=endpoint, **kwargs)

    def response(
        self,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        cached: bool = False,
        **kwargs: Any,
    ) -> None:
        """Log API response."""
        self.logger.info(
            "api_response",
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            cached=cached,
            **kwargs,
        )

    def error(self, endpoint: str, error: str, **kwargs: Any) -> None:
        """Log API error."""
        self.logger.error(
            "api_error",
            endpoint=endpoint,
            error=error,
            **kwargs,
        )

    def rate_limited(self, endpoint: str, retry_after: int, **kwargs: Any) -> None:
        """Log rate limit hit."""
        self.logger.warning(
            "rate_limited",
            endpoint=endpoint,
            retry_after=retry_after,
            **kwargs,
        )
