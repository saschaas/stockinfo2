"""CUSIP to Ticker Symbol Mapper.

This service provides mapping between CUSIP identifiers and stock ticker symbols
using the OpenFIGI API with Redis caching.
"""

import asyncio
from typing import Any

import httpx
import structlog

from backend.app.services.cache import CacheService, cache

logger = structlog.get_logger(__name__)

# Common CUSIP to Ticker mapping for major stocks (fallback/quick lookup)
CUSIP_TO_TICKER = {
    "88160R101": "TSLA",      # Tesla Inc
    "67066G104": "NVDA",      # NVIDIA Corporation
    "594918104": "MSFT",      # Microsoft Corp
    "02079K305": "GOOGL",     # Alphabet Inc Class A
    "02079K107": "GOOG",      # Alphabet Inc Class C
    "30303M102": "META",      # Meta Platforms Inc
    "037833100": "AAPL",      # Apple Inc
    "023135106": "AMZN",      # Amazon.com Inc
    "674599105": "OXY",       # Occidental Petroleum Corp
    "69608A108": "PLTR",      # Palantir Technologies Inc
    "H1467J104": "CB",        # Chubb Limited
    "91324P102": "UNH",       # UnitedHealth Group Inc
    "500754106": "KHC",       # Kraft Heinz Co
    "64110L106": "NFLX",      # Netflix Inc
    "11135F101": "AVGO",      # Broadcom Inc
    "007903107": "AMD",       # Advanced Micro Devices Inc
    "874039100": "TSM",       # Taiwan Semiconductor Manufacturing
    "92826C839": "V",         # Visa Inc
    "615369105": "MCO",       # Moody's Corp
    "770700102": "HOOD",      # Robinhood Markets Inc
    "81141R100": "SE",        # Sea Ltd
    "46625H100": "JPM",       # JPMorgan Chase & Co
    "92343E102": "VRSN",      # VeriSign Inc
    "90353T100": "UBER",      # Uber Technologies Inc
    "00724F101": "ADBE",      # Adobe Inc
    "68389X105": "ORCL",      # Oracle Corp
    "38141G104": "GS",        # Goldman Sachs Group Inc
    "19260Q107": "COIN",      # Coinbase Global Inc
    "532457108": "LLY",       # Eli Lilly & Co
    "57636Q104": "MA",        # Mastercard Incorporated
    "01609W102": "BABA",      # Alibaba Group Holding Ltd
    "36828A101": "GEV",       # GE Vernova Inc
    "595112103": "MU",        # Micron Technology Inc
    "L8681T102": "SPOT",      # Spotify Technology SA
    "771049103": "RBLX",      # Roblox Corp
    "458140100": "INTC",      # Intel Corp
    "097023105": "BA",        # Boeing Co
    "75734B100": "RDDT",      # Reddit Inc
    "22788C105": "CRWD",      # CrowdStrike Holdings Inc
    "09857L108": "BKNG",      # Booking Holdings Inc
    "03831W108": "APP",       # AppLovin Corp
}

# Cache for negative lookups (CUSIPs that don't map to US tickers)
_negative_cache: set[str] = set()

# OpenFIGI API configuration
OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
OPENFIGI_BATCH_SIZE = 100  # OpenFIGI allows up to 100 items per request


def cusip_to_ticker(cusip: str) -> str | None:
    """Convert CUSIP to ticker symbol (sync, uses static mapping only).

    Args:
        cusip: CUSIP identifier

    Returns:
        Ticker symbol if found, None otherwise
    """
    return CUSIP_TO_TICKER.get(cusip)


def is_cusip(identifier: str) -> bool:
    """Check if string looks like a CUSIP (9 alphanumeric characters).

    Args:
        identifier: String to check

    Returns:
        True if looks like CUSIP, False otherwise
    """
    if not identifier:
        return False
    # CUSIPs are typically 9 characters
    return len(identifier) == 9 and identifier.isalnum()


async def lookup_cusip_openfigi(cusip: str) -> str | None:
    """Look up a single CUSIP using OpenFIGI API.

    Args:
        cusip: CUSIP identifier

    Returns:
        Ticker symbol if found, None otherwise
    """
    cache_key = f"cusip:ticker:{cusip}"

    # Check cache first
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached if cached != "" else None

    # Check negative cache
    if cusip in _negative_cache:
        return None

    # Check static mapping
    if cusip in CUSIP_TO_TICKER:
        ticker = CUSIP_TO_TICKER[cusip]
        await cache.set(cache_key, ticker, CacheService.TTL_LONG)
        return ticker

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENFIGI_URL,
                headers={"Content-Type": "application/json"},
                json=[{"idType": "ID_CUSIP", "idValue": cusip}],
            )
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0 and "data" in data[0]:
                # Find US exchange ticker (prefer US, UN, UA, UQ exchanges)
                us_exchanges = {"US", "UN", "UA", "UQ", "UW", "UM", "UP", "UB", "UD", "UF", "UX"}
                for item in data[0]["data"]:
                    exch = item.get("exchCode", "")
                    if exch in us_exchanges:
                        ticker = item.get("ticker")
                        if ticker and len(ticker) <= 5:  # Valid US ticker
                            # Cache the result
                            await cache.set(cache_key, ticker, CacheService.TTL_LONG)
                            # Also add to static mapping for future sync lookups
                            CUSIP_TO_TICKER[cusip] = ticker
                            logger.debug("OpenFIGI lookup success", cusip=cusip, ticker=ticker)
                            return ticker

            # No valid US ticker found - cache negative result
            await cache.set(cache_key, "", CacheService.TTL_LONG)
            _negative_cache.add(cusip)
            logger.debug("OpenFIGI lookup no US ticker", cusip=cusip)
            return None

    except Exception as e:
        logger.warning("OpenFIGI lookup failed", cusip=cusip, error=str(e))
        return None


async def lookup_cusips_batch(cusips: list[str]) -> dict[str, str | None]:
    """Look up multiple CUSIPs using OpenFIGI API (batched).

    Args:
        cusips: List of CUSIP identifiers

    Returns:
        Dictionary mapping CUSIP to ticker (or None if not found)
    """
    results: dict[str, str | None] = {}
    to_lookup: list[str] = []

    # Check cache and static mapping first
    for cusip in cusips:
        cache_key = f"cusip:ticker:{cusip}"
        cached = await cache.get(cache_key)

        if cached is not None:
            results[cusip] = cached if cached != "" else None
        elif cusip in _negative_cache:
            results[cusip] = None
        elif cusip in CUSIP_TO_TICKER:
            results[cusip] = CUSIP_TO_TICKER[cusip]
        else:
            to_lookup.append(cusip)

    if not to_lookup:
        return results

    # Batch lookup via OpenFIGI - process each batch independently
    us_exchanges = {"US", "UN", "UA", "UQ", "UW", "UM", "UP", "UB", "UD", "UF", "UX"}
    batches_processed = 0
    batches_failed = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Process in batches of OPENFIGI_BATCH_SIZE
        for i in range(0, len(to_lookup), OPENFIGI_BATCH_SIZE):
            batch = to_lookup[i:i + OPENFIGI_BATCH_SIZE]

            try:
                request_data = [{"idType": "ID_CUSIP", "idValue": c} for c in batch]

                response = await client.post(
                    OPENFIGI_URL,
                    headers={"Content-Type": "application/json"},
                    json=request_data,
                )
                response.raise_for_status()
                data = response.json()

                # Process results
                for idx, cusip in enumerate(batch):
                    cache_key = f"cusip:ticker:{cusip}"
                    ticker = None

                    if idx < len(data) and "data" in data[idx]:
                        for item in data[idx]["data"]:
                            exch = item.get("exchCode", "")
                            if exch in us_exchanges:
                                t = item.get("ticker")
                                if t and len(t) <= 5:
                                    ticker = t
                                    break

                    results[cusip] = ticker

                    # Cache result
                    if ticker:
                        await cache.set(cache_key, ticker, CacheService.TTL_LONG)
                        CUSIP_TO_TICKER[cusip] = ticker
                    else:
                        await cache.set(cache_key, "", CacheService.TTL_LONG)
                        _negative_cache.add(cusip)

                batches_processed += 1

            except Exception as e:
                logger.warning("OpenFIGI batch failed", batch_start=i, error=str(e))
                batches_failed += 1
                # Mark this batch as None (not found) but continue with other batches
                for cusip in batch:
                    if cusip not in results:
                        results[cusip] = None

            # Small delay between batches to be respectful
            if i + OPENFIGI_BATCH_SIZE < len(to_lookup):
                await asyncio.sleep(0.5)

    logger.info(
        "OpenFIGI batch lookup complete",
        total=len(cusips),
        looked_up=len(to_lookup),
        batches_processed=batches_processed,
        batches_failed=batches_failed,
    )

    return results


def get_ticker_or_cusip(identifier: str) -> str | None:
    """Get ticker symbol from identifier (sync version, static mapping only).

    For async lookups with OpenFIGI, use get_ticker_or_cusip_async.

    Args:
        identifier: CUSIP or ticker symbol

    Returns:
        Ticker symbol if CUSIP found in mapping, None if CUSIP not found,
        or original identifier if it's already a ticker symbol
    """
    if is_cusip(identifier):
        # If it's a CUSIP, only return the ticker if found in mapping
        # Return None if CUSIP is not mapped (don't return the CUSIP itself)
        ticker = cusip_to_ticker(identifier)
        return ticker
    # If not a CUSIP, assume it's already a ticker symbol
    return identifier


async def get_ticker_or_cusip_async(identifier: str) -> str | None:
    """Get ticker symbol from identifier (async version with OpenFIGI lookup).

    Args:
        identifier: CUSIP or ticker symbol

    Returns:
        Ticker symbol if found, None if not found,
        or original identifier if it's already a ticker symbol
    """
    if is_cusip(identifier):
        # First check static mapping
        ticker = cusip_to_ticker(identifier)
        if ticker:
            return ticker
        # Fall back to OpenFIGI lookup
        return await lookup_cusip_openfigi(identifier)
    # If not a CUSIP, assume it's already a ticker symbol
    return identifier
