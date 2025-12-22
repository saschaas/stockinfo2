"""Pydantic schemas for ETF tracking."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ETFCreate(BaseModel):
    """Schema for creating a new ETF."""

    name: str = Field(..., min_length=1, max_length=200)
    ticker: str = Field(..., min_length=1, max_length=20)
    url: str = Field(..., min_length=1, max_length=500)
    agent_command: str = Field(..., min_length=1)
    description: str | None = None
    category: str = Field(default="general", max_length=50)


class ETFUpdate(BaseModel):
    """Schema for updating an ETF."""

    name: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    agent_command: str | None = None
    description: str | None = None
    category: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class ETFInfo(BaseModel):
    """ETF information."""

    id: int
    name: str
    ticker: str
    url: str
    agent_command: str
    description: str | None = None
    category: str
    priority: int
    is_active: bool
    last_scrape_at: datetime | None = None
    last_scrape_success: bool | None = None
    last_scrape_error: str | None = None
    created_at: datetime
    updated_at: datetime


class ETFListResponse(BaseModel):
    """Response schema for ETF list."""

    total: int
    etfs: list[dict[str, Any]]


class ETFHoldingData(BaseModel):
    """Single ETF holding data."""

    ticker: str
    company_name: str | None = None
    cusip: str | None = None
    shares: int | None = None
    market_value: float | None = None
    weight_pct: float | None = None
    shares_change: int | None = None
    weight_change: float | None = None
    change_type: str | None = None
    etf_count: int | None = None
    etf_names: list[str] | None = None


class ETFHoldingsResponse(BaseModel):
    """Response schema for ETF holdings."""

    etf_id: int
    etf_name: str
    holding_date: date | None = None
    holdings: list[dict[str, Any]]
    total_value: float


class ETFChangeData(BaseModel):
    """Change data for an ETF holding."""

    ticker: str
    company_name: str | None = None
    shares: int | None = None
    market_value: float | None = None
    weight_pct: float | None = None
    shares_change: int | None = None
    weight_change: float | None = None
    etf_count: int | None = None
    etf_names: list[str] | None = None


class ETFChangesResponse(BaseModel):
    """Response schema for ETF holdings changes."""

    etf_id: int
    etf_name: str
    holding_date: date | None = None
    new_positions: list[dict[str, Any]]
    increased: list[dict[str, Any]]
    decreased: list[dict[str, Any]]
    sold: list[dict[str, Any]]


class ETFUpdateInfo(BaseModel):
    """Information about an ETF's update status."""

    etf_id: int
    etf_name: str
    ticker: str
    latest_holding_date: str | None = None
    last_data_update: str | None = None
    has_new_data: bool


class ETFUpdatesResponse(BaseModel):
    """Response for ETF updates check."""

    etfs: list[ETFUpdateInfo]
    has_any_updates: bool
    checked_at: str


class ETFRefreshResponse(BaseModel):
    """Response for ETF refresh operation."""

    message: str
    etfs_queued: int


class ETFSingleRefreshResponse(BaseModel):
    """Response for single ETF refresh operation."""

    etf_id: int
    etf_name: str
    message: str
    success: bool
    holdings_count: int | None = None
    holding_date: str | None = None
    error: str | None = None
