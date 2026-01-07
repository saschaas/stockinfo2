"""Database management schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TableStats(BaseModel):
    """Statistics for a single database table."""

    name: str = Field(..., description="Table name")
    row_count: int = Field(..., description="Number of rows in the table")
    size_bytes: int = Field(..., description="Table size in bytes")
    size_formatted: str = Field(..., description="Human-readable size (e.g., '1.2 MB')")
    category: str = Field(..., description="Table category: 'user_data' or 'cache'")


class DatabaseStats(BaseModel):
    """Overall database statistics."""

    total_size_bytes: int = Field(..., description="Total database size in bytes")
    total_size_formatted: str = Field(..., description="Human-readable total size")
    table_count: int = Field(..., description="Number of tables")
    total_rows: int = Field(..., description="Total rows across all tables")
    tables: list[TableStats] = Field(default_factory=list, description="Per-table statistics")


class ExportResponse(BaseModel):
    """Response from database export operation."""

    filename: str = Field(..., description="Export filename")
    size_bytes: int = Field(..., description="Export file size in bytes")
    size_formatted: str = Field(..., description="Human-readable file size")
    tables_exported: list[str] = Field(default_factory=list, description="List of exported tables")
    row_counts: dict[str, int] = Field(default_factory=dict, description="Row count per table")
    exported_at: datetime = Field(..., description="Export timestamp")


class ImportResponse(BaseModel):
    """Response from database import operation."""

    success: bool = Field(..., description="Whether import was successful")
    tables_imported: list[str] = Field(default_factory=list, description="List of imported tables")
    row_counts: dict[str, int] = Field(default_factory=dict, description="Row count per imported table")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: list[str] = Field(default_factory=list, description="Any warnings")
