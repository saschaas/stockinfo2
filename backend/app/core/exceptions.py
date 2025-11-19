"""Custom exceptions for Stock Research Tool."""

from typing import Any


class StockResearchException(Exception):
    """Base exception for Stock Research Tool."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        suggestion: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.suggestion = suggestion
        self.details = details or {}
        super().__init__(self.message)


class DataSourceException(StockResearchException):
    """Exception for data source errors."""

    def __init__(
        self,
        message: str,
        source: str,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="DATA_SOURCE_ERROR",
            suggestion=suggestion or f"The {source} data source is unavailable. Try again later or use a different source.",
        )
        self.source = source


class RateLimitException(StockResearchException):
    """Exception for rate limit errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        suggestion = "Please wait before making more requests."
        if retry_after:
            suggestion = f"Please wait {retry_after} seconds before retrying."

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            suggestion=suggestion,
        )
        self.retry_after = retry_after


class ValidationException(StockResearchException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            suggestion="Please check your input and try again.",
        )
        self.field = field


class NotFoundException(StockResearchException):
    """Exception for resource not found errors."""

    def __init__(
        self,
        resource: str,
        identifier: str,
    ) -> None:
        super().__init__(
            message=f"{resource} with identifier '{identifier}' not found",
            status_code=404,
            error_code="NOT_FOUND",
            suggestion=f"Verify the {resource.lower()} identifier is correct.",
        )
        self.resource = resource
        self.identifier = identifier


class AnalysisException(StockResearchException):
    """Exception for analysis errors."""

    def __init__(
        self,
        message: str,
        ticker: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="ANALYSIS_ERROR",
            suggestion=suggestion or "The analysis could not be completed. Check the stock ticker and try again.",
        )
        self.ticker = ticker


class AIAgentException(StockResearchException):
    """Exception for AI agent errors."""

    def __init__(
        self,
        message: str,
        agent: str,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="AI_AGENT_ERROR",
            suggestion=suggestion or f"The {agent} agent encountered an error. Check Ollama is running and try again.",
        )
        self.agent = agent


class ConfigurationException(StockResearchException):
    """Exception for configuration errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            suggestion="Check application configuration and environment variables.",
        )
        self.config_key = config_key
