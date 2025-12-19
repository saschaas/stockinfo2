"""
Peer Multiples Service for Relative Valuation.

Provides peer comparison data and sector-average multiples
for relative valuation methods.
"""

import structlog

logger = structlog.get_logger(__name__)


class PeerMultiplesService:
    """
    Fetches and provides peer comparison multiples for relative valuation.

    Uses sector defaults when peer data is unavailable.
    """

    # Industry-average multiples by sector
    # Based on historical sector averages
    SECTOR_MULTIPLES: dict[str, dict[str, dict[str, float]]] = {
        "technology": {
            "pe": {"median": 28.0, "low": 18.0, "high": 40.0},
            "pb": {"median": 6.0, "low": 3.0, "high": 12.0},
            "ps": {"median": 6.0, "low": 3.0, "high": 12.0},
            "ev_ebitda": {"median": 18.0, "low": 12.0, "high": 28.0},
            "ev_revenue": {"median": 6.0, "low": 3.0, "high": 12.0},
        },
        "financial services": {
            "pe": {"median": 12.0, "low": 8.0, "high": 18.0},
            "pb": {"median": 1.2, "low": 0.7, "high": 2.0},
            "ev_ebitda": {"median": 8.0, "low": 5.0, "high": 12.0},
        },
        "healthcare": {
            "pe": {"median": 24.0, "low": 16.0, "high": 35.0},
            "pb": {"median": 4.0, "low": 2.0, "high": 8.0},
            "ev_ebitda": {"median": 15.0, "low": 10.0, "high": 22.0},
            "ev_revenue": {"median": 4.0, "low": 2.0, "high": 8.0},
        },
        "consumer cyclical": {
            "pe": {"median": 20.0, "low": 12.0, "high": 28.0},
            "pb": {"median": 3.5, "low": 1.5, "high": 6.0},
            "ev_ebitda": {"median": 12.0, "low": 8.0, "high": 18.0},
            "ev_revenue": {"median": 1.5, "low": 0.8, "high": 3.0},
        },
        "consumer defensive": {
            "pe": {"median": 22.0, "low": 16.0, "high": 28.0},
            "pb": {"median": 4.5, "low": 2.5, "high": 7.0},
            "ev_ebitda": {"median": 14.0, "low": 10.0, "high": 18.0},
            "ev_revenue": {"median": 2.0, "low": 1.2, "high": 3.5},
        },
        "industrials": {
            "pe": {"median": 20.0, "low": 12.0, "high": 28.0},
            "pb": {"median": 3.5, "low": 2.0, "high": 6.0},
            "ev_ebitda": {"median": 12.0, "low": 8.0, "high": 18.0},
            "ev_revenue": {"median": 1.8, "low": 1.0, "high": 3.0},
        },
        "energy": {
            "pe": {"median": 14.0, "low": 6.0, "high": 22.0},
            "pb": {"median": 1.5, "low": 0.8, "high": 2.5},
            "ev_ebitda": {"median": 6.0, "low": 3.5, "high": 10.0},
            "ev_revenue": {"median": 1.2, "low": 0.6, "high": 2.5},
        },
        "utilities": {
            "pe": {"median": 18.0, "low": 14.0, "high": 24.0},
            "pb": {"median": 1.8, "low": 1.2, "high": 2.5},
            "ev_ebitda": {"median": 12.0, "low": 9.0, "high": 16.0},
            "ev_revenue": {"median": 3.0, "low": 2.0, "high": 4.5},
        },
        "real estate": {
            "pe": {"median": 35.0, "low": 20.0, "high": 50.0},
            "pb": {"median": 1.8, "low": 1.0, "high": 3.0},
            "ev_ebitda": {"median": 18.0, "low": 12.0, "high": 25.0},
        },
        "basic materials": {
            "pe": {"median": 16.0, "low": 8.0, "high": 24.0},
            "pb": {"median": 2.0, "low": 1.0, "high": 3.5},
            "ev_ebitda": {"median": 8.0, "low": 5.0, "high": 12.0},
            "ev_revenue": {"median": 1.5, "low": 0.8, "high": 2.5},
        },
        "communication services": {
            "pe": {"median": 22.0, "low": 14.0, "high": 32.0},
            "pb": {"median": 3.0, "low": 1.5, "high": 5.0},
            "ev_ebitda": {"median": 10.0, "low": 6.0, "high": 16.0},
            "ev_revenue": {"median": 3.0, "low": 1.5, "high": 5.0},
        },
    }

    # Default multiples when sector is unknown
    DEFAULT_MULTIPLES: dict[str, dict[str, float]] = {
        "pe": {"median": 20.0, "low": 12.0, "high": 30.0},
        "pb": {"median": 3.0, "low": 1.5, "high": 5.0},
        "ps": {"median": 2.5, "low": 1.0, "high": 5.0},
        "ev_ebitda": {"median": 12.0, "low": 8.0, "high": 18.0},
        "ev_revenue": {"median": 2.5, "low": 1.0, "high": 5.0},
    }

    def get_peer_multiples(
        self,
        sector: str,
        industry: str | None = None,
    ) -> dict[str, dict[str, float]]:
        """
        Get peer multiples for a given sector.

        Args:
            sector: Company sector
            industry: Company industry (optional, for future refinement)

        Returns:
            Dict with multiples (pe, pb, ev_ebitda, etc.)
            Each multiple has median, low, high values
        """
        sector_key = sector.lower() if sector else ""

        # Try to find exact match
        multiples = self.SECTOR_MULTIPLES.get(sector_key)

        if multiples:
            logger.debug("Found sector multiples", sector=sector_key)
            return multiples

        # Try partial match
        for key, data in self.SECTOR_MULTIPLES.items():
            if key in sector_key or sector_key in key:
                logger.debug("Found partial sector match", sector=sector_key, match=key)
                return data

        # Return defaults
        logger.debug("Using default multiples", sector=sector_key)
        return self.DEFAULT_MULTIPLES

    def get_multiple(
        self,
        sector: str,
        multiple_type: str,
    ) -> tuple[float, float, float]:
        """
        Get a specific multiple for a sector.

        Args:
            sector: Company sector
            multiple_type: Type of multiple (pe, pb, ev_ebitda, etc.)

        Returns:
            Tuple of (median, low, high)
        """
        multiples = self.get_peer_multiples(sector)

        if multiple_type in multiples:
            data = multiples[multiple_type]
            return data["median"], data["low"], data["high"]

        # Try default multiples
        if multiple_type in self.DEFAULT_MULTIPLES:
            data = self.DEFAULT_MULTIPLES[multiple_type]
            return data["median"], data["low"], data["high"]

        # Ultimate fallback
        return 15.0, 10.0, 20.0

    def adjust_multiple_for_growth(
        self,
        base_multiple: float,
        company_growth: float,
        sector_average_growth: float = 0.10,
    ) -> float:
        """
        Adjust multiple based on growth differential.

        Higher growth companies deserve higher multiples.

        Args:
            base_multiple: Base sector multiple
            company_growth: Company's growth rate
            sector_average_growth: Average sector growth rate

        Returns:
            Growth-adjusted multiple
        """
        if sector_average_growth <= 0:
            sector_average_growth = 0.10

        # Calculate growth differential
        growth_diff = company_growth - sector_average_growth

        # Adjust multiple (roughly 1:1 relationship)
        # Every 10% above average = 10-15% higher multiple
        if growth_diff > 0:
            adjustment = 1 + (growth_diff * 1.2)
            adjustment = min(1.5, adjustment)  # Cap at 50% premium
        else:
            adjustment = 1 + (growth_diff * 0.8)
            adjustment = max(0.6, adjustment)  # Floor at 40% discount

        return base_multiple * adjustment

    def adjust_multiple_for_profitability(
        self,
        base_multiple: float,
        company_margin: float,
        sector_average_margin: float = 0.15,
    ) -> float:
        """
        Adjust multiple based on profitability differential.

        More profitable companies deserve higher multiples.

        Args:
            base_multiple: Base sector multiple
            company_margin: Company's profit margin
            sector_average_margin: Average sector margin

        Returns:
            Margin-adjusted multiple
        """
        if sector_average_margin <= 0:
            sector_average_margin = 0.15

        margin_diff = company_margin - sector_average_margin

        # Adjust multiple
        if margin_diff > 0:
            adjustment = 1 + (margin_diff * 0.8)
            adjustment = min(1.3, adjustment)  # Cap at 30% premium
        else:
            adjustment = 1 + (margin_diff * 0.5)
            adjustment = max(0.7, adjustment)  # Floor at 30% discount

        return base_multiple * adjustment

    def get_cap_rate_for_reit(self, property_type: str = "diversified") -> float:
        """
        Get typical cap rate for REIT property types.

        Args:
            property_type: Type of REIT properties

        Returns:
            Capitalization rate as decimal
        """
        cap_rates = {
            "residential": 0.045,  # 4.5%
            "office": 0.065,  # 6.5%
            "retail": 0.06,  # 6.0%
            "industrial": 0.05,  # 5.0%
            "healthcare": 0.055,  # 5.5%
            "hotel": 0.08,  # 8.0%
            "diversified": 0.055,  # 5.5%
            "data_center": 0.045,  # 4.5%
            "cell_tower": 0.04,  # 4.0%
        }

        return cap_rates.get(property_type.lower(), 0.055)
