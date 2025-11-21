"""Pydantic schemas for fund tracking."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class FundInfo(BaseModel):
    """Fund information."""

    id: int
    name: str
    ticker: str | None = None
    cik: str | None = None
    category: str
    priority: int


class FundListResponse(BaseModel):
    """Response schema for fund list."""

    total: int
    funds: list[dict[str, Any]]


class HoldingData(BaseModel):
    """Single holding data."""

    ticker: str
    company_name: str | None = None
    shares: int
    value: float
    percentage: float | None = None
    change_type: str | None = None
    shares_change: int | None = None
    fund_count: int | None = None


class FundHoldingsResponse(BaseModel):
    """Response schema for fund holdings."""

    fund_id: int
    fund_name: str
    filing_date: date | None = None
    holdings: list[dict[str, Any]]
    total_value: float


class ChangeData(BaseModel):
    """Change data for a holding."""

    ticker: str
    company_name: str | None = None
    shares: int
    value: float
    shares_change: int | None = None
    fund_count: int | None = None


class FundChangesResponse(BaseModel):
    """Response schema for fund holdings changes."""

    fund_id: int
    fund_name: str
    filing_date: date | None = None
    new_positions: list[dict[str, Any]]
    increased: list[dict[str, Any]]
    decreased: list[dict[str, Any]]
    sold: list[dict[str, Any]]
