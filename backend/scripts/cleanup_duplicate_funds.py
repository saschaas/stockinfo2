#!/usr/bin/env python3
"""Clean up duplicate funds in the database.

This script removes duplicate fund entries with the same CIK,
keeping only the first (oldest) entry for each unique CIK.
"""

import asyncio
import sys
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.config import settings

logger = structlog.get_logger(__name__)


async def cleanup_duplicate_funds(session: AsyncSession) -> int:
    """Remove duplicate funds, keeping only the oldest entry per CIK."""

    # Find duplicate CIKs and their counts
    result = await session.execute(text("""
        SELECT cik, COUNT(*) as count
        FROM funds
        GROUP BY cik
        HAVING COUNT(*) > 1
    """))

    duplicates = result.fetchall()

    if not duplicates:
        logger.info("No duplicate funds found")
        return 0

    logger.info(f"Found {len(duplicates)} CIKs with duplicates")

    total_deleted = 0

    for cik, count in duplicates:
        # Get all IDs for this CIK, ordered by ID (oldest first)
        result = await session.execute(
            text("SELECT id FROM funds WHERE cik = :cik ORDER BY id ASC"),
            {"cik": cik}
        )
        ids = [row[0] for row in result.fetchall()]

        # Keep the first ID, delete the rest
        keep_id = ids[0]
        delete_ids = ids[1:]

        logger.info(
            f"CIK {cik}: keeping ID {keep_id}, deleting {len(delete_ids)} duplicates",
            keep_id=keep_id,
            delete_ids=delete_ids
        )

        # Delete duplicate entries
        await session.execute(
            text("DELETE FROM funds WHERE id = ANY(:ids)"),
            {"ids": delete_ids}
        )

        total_deleted += len(delete_ids)

    await session.commit()
    logger.info(f"Cleanup complete: deleted {total_deleted} duplicate funds")

    return total_deleted


async def main() -> int:
    """Main cleanup function."""
    logger.info("Starting duplicate funds cleanup...")

    # Create engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )

    # Create session
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        deleted_count = await cleanup_duplicate_funds(session)

    # Close engine
    await engine.dispose()

    logger.info("Cleanup complete", deleted_count=deleted_count)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
