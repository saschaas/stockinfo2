"""Test SEC EDGAR search directly."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.sec_edgar import get_sec_edgar_client


async def test_search():
    """Test searching for Duquesne Family Office."""
    client = await get_sec_edgar_client()

    print("Testing search for 'Duquesne Family Office'...")
    results = await client.search_companies("Duquesne Family Office", limit=5)

    print(f"\nFound {len(results)} results:")
    for result in results:
        print(f"  - {result['name']} (CIK: {result['cik']})")

    print("\n\nTesting search for 'Duquesne'...")
    results = await client.search_companies("Duquesne", limit=5)

    print(f"\nFound {len(results)} results:")
    for result in results:
        print(f"  - {result['name']} (CIK: {result['cik']})")


if __name__ == "__main__":
    asyncio.run(test_search())
