"""CUSIP to Ticker Symbol Mapper.

This service provides mapping between CUSIP identifiers and stock ticker symbols.
"""

# Common CUSIP to Ticker mapping for major stocks
# This is a subset - in production, you'd want a complete database or API lookup
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


def cusip_to_ticker(cusip: str) -> str | None:
    """Convert CUSIP to ticker symbol.

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


def get_ticker_or_cusip(identifier: str) -> str:
    """Get ticker symbol from identifier, or return original if not CUSIP.

    Args:
        identifier: CUSIP or ticker symbol

    Returns:
        Ticker symbol if CUSIP found in mapping, otherwise original identifier
    """
    if is_cusip(identifier):
        ticker = cusip_to_ticker(identifier)
        return ticker if ticker else identifier
    return identifier
