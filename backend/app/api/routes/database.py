"""Database management API routes."""

import json
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    UserConfig,
    WatchlistItem,
)
from backend.app.db.session import get_db
from backend.app.schemas.database import (
    DatabaseStats,
    ExportResponse,
    ImportResponse,
    TableStats,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

# Tables to export (user data needed for continuity)
USER_DATA_TABLES = [
    "watchlist_items",
    "user_configs",
]

# Tables that are cache/system data (not exported)
CACHE_TABLES = [
    "stock_prices",
    "market_sentiment",
    "web_scraped_market_data",
    "scraped_category_data",
    "research_jobs",
    "data_sources",
    "stock_analyses",  # Research history - can be regenerated
    "scraped_websites",  # Needs daily updates anyway
    "funds",  # Loaded daily from config
    "fund_holdings",  # Loaded daily from SEC
    "etfs",  # Loaded daily from config
    "etf_holdings",  # Loaded daily from ETF providers
]

# Directory for export files
EXPORT_DIR = Path(tempfile.gettempdir()) / "stockinfo_exports"
EXPORT_DIR.mkdir(exist_ok=True)


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for SQLAlchemy objects and special types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, "__dict__"):
        # SQLAlchemy model - convert to dict
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                result[key] = json_serializer(value)
        return result
    elif isinstance(obj, list):
        return [json_serializer(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: json_serializer(v) for k, v in obj.items()}
    return obj


@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats(
    db: AsyncSession = Depends(get_db),
) -> DatabaseStats:
    """Get database statistics including table sizes and row counts."""
    try:
        # Get table sizes from system catalog
        size_query = text("""
            SELECT
                relname as table_name,
                pg_table_size(relid) as size_bytes
            FROM pg_stat_user_tables
            ORDER BY pg_table_size(relid) DESC
        """)
        size_result = await db.execute(size_query)
        size_rows = size_result.fetchall()

        tables = []
        total_size = 0
        total_rows = 0

        for row in size_rows:
            table_name = row.table_name
            size_bytes = row.size_bytes or 0

            # Get actual row count with COUNT(*)
            try:
                count_result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = count_result.scalar() or 0
            except Exception:
                row_count = 0

            # Determine category
            if table_name in USER_DATA_TABLES:
                category = "user_data"
            elif table_name in CACHE_TABLES:
                category = "cache"
            else:
                category = "system"

            tables.append(
                TableStats(
                    name=table_name,
                    row_count=row_count,
                    size_bytes=size_bytes,
                    size_formatted=format_size(size_bytes),
                    category=category,
                )
            )
            total_size += size_bytes
            total_rows += row_count

        return DatabaseStats(
            total_size_bytes=total_size,
            total_size_formatted=format_size(total_size),
            table_count=len(tables),
            total_rows=total_rows,
            tables=tables,
        )
    except Exception as e:
        logger.error("Failed to get database stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")


@router.post("/export", response_model=ExportResponse)
async def export_database(
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Export all user data tables to a JSON file."""
    try:
        export_data: dict[str, Any] = {
            "version": "1.0",
            "app_name": "stockinfo",
            "exported_at": datetime.utcnow().isoformat(),
            "tables": {},
            "metadata": {"row_counts": {}},
        }

        row_counts: dict[str, int] = {}

        # Export user data tables (only watchlist and user configs)
        # Funds/ETFs are loaded daily from external sources

        # 1. user_configs
        configs = (await db.execute(text("SELECT * FROM user_configs"))).fetchall()
        export_data["tables"]["user_configs"] = [dict(row._mapping) for row in configs]
        row_counts["user_configs"] = len(configs)

        # 2. watchlist_items
        watchlist = (await db.execute(text("SELECT * FROM watchlist_items"))).fetchall()
        export_data["tables"]["watchlist_items"] = [dict(row._mapping) for row in watchlist]
        row_counts["watchlist_items"] = len(watchlist)

        export_data["metadata"]["row_counts"] = row_counts

        # Serialize with custom handler
        export_json = json.dumps(export_data, default=json_serializer, indent=2)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"stockinfo_export_{timestamp}.json"
        filepath = EXPORT_DIR / filename

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(export_json)

        file_size = os.path.getsize(filepath)

        logger.info(
            "Database export completed",
            filename=filename,
            size_bytes=file_size,
            tables_exported=list(row_counts.keys()),
        )

        return ExportResponse(
            filename=filename,
            size_bytes=file_size,
            size_formatted=format_size(file_size),
            tables_exported=list(row_counts.keys()),
            row_counts=row_counts,
            exported_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.error("Failed to export database", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to export database: {str(e)}")


@router.get("/export/{filename}")
async def download_export(filename: str) -> FileResponse:
    """Download an export file."""
    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = EXPORT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ImportResponse)
async def import_database(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportResponse:
    """Import data from an export file. Replaces existing data."""
    errors: list[str] = []
    warnings: list[str] = []
    row_counts: dict[str, int] = {}
    tables_imported: list[str] = []

    try:
        # Read and parse the uploaded file
        content = await file.read()
        try:
            import_data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")

        # Validate structure
        if "version" not in import_data:
            raise HTTPException(status_code=400, detail="Missing version field")
        if "tables" not in import_data:
            raise HTTPException(status_code=400, detail="Missing tables field")

        version = import_data.get("version", "")
        if not version.startswith("1."):
            warnings.append(f"Unknown version: {version}")

        tables = import_data.get("tables", {})

        # Delete existing data (only user data tables)
        delete_order = [
            "watchlist_items",
            "user_configs",
        ]

        for table_name in delete_order:
            if table_name in tables:
                try:
                    await db.execute(text(f"DELETE FROM {table_name}"))
                    logger.info(f"Cleared table {table_name}")
                except Exception as e:
                    errors.append(f"Failed to clear {table_name}: {str(e)}")

        # Import data (only user data tables)
        import_order = [
            ("user_configs", UserConfig),
            ("watchlist_items", WatchlistItem),
        ]

        for table_name, model_class in import_order:
            if table_name not in tables:
                warnings.append(f"Table {table_name} not found in import file")
                continue

            table_data = tables[table_name]
            if not table_data:
                row_counts[table_name] = 0
                tables_imported.append(table_name)
                continue

            try:
                count = 0
                for row_data in table_data:
                    # Convert date/datetime strings back to objects
                    processed_data = _process_import_row(row_data, model_class)

                    # Create model instance
                    obj = model_class(**processed_data)
                    db.add(obj)
                    count += 1

                await db.flush()
                row_counts[table_name] = count
                tables_imported.append(table_name)
                logger.info(f"Imported {count} rows into {table_name}")
            except Exception as e:
                errors.append(f"Failed to import {table_name}: {str(e)}")
                logger.error(f"Failed to import {table_name}", error=str(e))

        # Commit all changes
        await db.commit()

        success = len(errors) == 0

        logger.info(
            "Database import completed",
            success=success,
            tables_imported=tables_imported,
            row_counts=row_counts,
            errors=errors,
        )

        return ImportResponse(
            success=success,
            tables_imported=tables_imported,
            row_counts=row_counts,
            errors=errors,
            warnings=warnings,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to import database", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to import database: {str(e)}")


def _process_import_row(row_data: dict, model_class: type) -> dict:
    """Process a row for import, converting types as needed."""
    from datetime import date as date_type
    from datetime import datetime as datetime_type

    processed = {}

    # Get column types from model
    mapper = model_class.__mapper__
    columns = {c.key: c for c in mapper.columns}

    for key, value in row_data.items():
        if key.startswith("_") or key not in columns:
            continue

        if value is None:
            processed[key] = None
            continue

        column = columns[key]
        column_type = str(column.type)

        # Convert string dates/datetimes
        if "DATETIME" in column_type or "TIMESTAMP" in column_type:
            if isinstance(value, str):
                try:
                    # Handle various datetime formats
                    if "T" in value:
                        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    else:
                        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
        elif "DATE" in column_type:
            if isinstance(value, str):
                try:
                    value = date.fromisoformat(value)
                except ValueError:
                    pass
        elif "NUMERIC" in column_type or "DECIMAL" in column_type:
            if isinstance(value, (int, float, str)):
                value = Decimal(str(value))

        processed[key] = value

    return processed
