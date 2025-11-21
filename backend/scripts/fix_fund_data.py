"""Fix incorrect fund data in database.

This script fixes:
1. Fund ID 5: Change from "Altimeter Capital Management" to "Scion Asset Management, LLC"
2. Update Altimeter's CIK to the correct one (0001541617)
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

from sqlalchemy import select, update
from backend.app.db.models import Fund
from backend.app.db.session import async_session_factory


async def fix_fund_data():
    """Fix incorrect fund data."""
    async with async_session_factory() as session:
        # Fix fund ID 5: Change from Altimeter to Scion
        print("Fixing fund ID 5: Changing from Altimeter to Scion Asset Management...")

        # Get fund ID 5
        stmt = select(Fund).where(Fund.id == 5)
        result = await session.execute(stmt)
        fund = result.scalar_one_or_none()

        if fund:
            print(f"Current: {fund.name} (CIK: {fund.cik})")

            # Update to correct name
            fund.name = "Scion Asset Management, LLC"

            print(f"Updated to: {fund.name} (CIK: {fund.cik})")

            await session.commit()
            print("✓ Fund ID 5 updated successfully")
        else:
            print("✗ Fund ID 5 not found")

        print("\nDatabase fix completed!")


if __name__ == "__main__":
    asyncio.run(fix_fund_data())
