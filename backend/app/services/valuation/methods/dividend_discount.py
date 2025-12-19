"""
Dividend Discount Model (DDM) Valuation Methods.

Implements:
- Gordon Growth Model (single-stage DDM)
- Two-Stage DDM (high growth + stable growth)
- H-Model (linearly declining growth)
"""

import structlog

from ..models import DataQuality, MethodResult, ValuationMethod

logger = structlog.get_logger(__name__)


class DividendDiscountValuation:
    """
    Dividend Discount Model valuation methods.

    Best suited for:
    - Mature dividend-paying companies
    - Utilities, REITs, and stable financials
    - Companies with consistent dividend history
    """

    def gordon_growth(
        self,
        current_dividend: float,
        dividend_growth: float,
        cost_of_equity: float,
    ) -> MethodResult:
        """
        Gordon Growth Model (Constant Growth DDM).

        Formula: P = D1 / (re - g)
        where D1 = D0 * (1 + g)

        Args:
            current_dividend: Current annual dividend per share (D0)
            dividend_growth: Expected perpetual dividend growth rate
            cost_of_equity: Required return on equity

        Returns:
            MethodResult with fair value
        """
        warnings = []

        # Validate inputs
        if current_dividend <= 0:
            return self._create_error_result(
                ValuationMethod.DDM_GORDON,
                "Company must pay dividends for DDM valuation",
            )

        if cost_of_equity <= dividend_growth:
            warnings.append(
                f"Cost of equity ({cost_of_equity:.2%}) must exceed dividend growth "
                f"({dividend_growth:.2%}). Adjusted growth rate."
            )
            dividend_growth = cost_of_equity - 0.03  # Force 3% spread

        if dividend_growth > 0.10:
            warnings.append(f"High dividend growth ({dividend_growth:.2%}) may not be sustainable")

        if dividend_growth < 0:
            warnings.append("Negative dividend growth indicates declining dividends")

        # Calculate D1 (next year's dividend)
        d1 = current_dividend * (1 + dividend_growth)

        # Gordon Growth formula
        fair_value = d1 / (cost_of_equity - dividend_growth)

        # Calculate range with different growth scenarios
        low_growth = max(0, dividend_growth - 0.02)
        high_growth = dividend_growth + 0.01
        low_estimate = (current_dividend * (1 + low_growth)) / (cost_of_equity - low_growth)
        if cost_of_equity > high_growth:
            high_estimate = (current_dividend * (1 + high_growth)) / (cost_of_equity - high_growth)
        else:
            high_estimate = fair_value * 1.25

        # Confidence based on assumptions
        confidence = self._calculate_confidence(dividend_growth, cost_of_equity)

        logger.debug(
            "Gordon Growth DDM complete",
            fair_value=fair_value,
            d1=d1,
            growth=dividend_growth,
        )

        return MethodResult(
            method=ValuationMethod.DDM_GORDON,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.HIGH if not warnings else DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "current_dividend": round(current_dividend, 4),
                "dividend_growth": round(dividend_growth, 4),
                "cost_of_equity": round(cost_of_equity, 4),
            },
            calculation_details={
                "d0": current_dividend,
                "d1": d1,
                "spread": cost_of_equity - dividend_growth,
            },
            warnings=warnings,
        )

    def two_stage_ddm(
        self,
        current_dividend: float,
        high_growth_rate: float,
        high_growth_years: int,
        terminal_growth: float,
        cost_of_equity: float,
    ) -> MethodResult:
        """
        Two-Stage DDM for companies with high near-term growth.

        Stage 1: High growth period with elevated dividend growth
        Stage 2: Stable growth (perpetuity using Gordon Growth)

        Args:
            current_dividend: Current annual dividend per share
            high_growth_rate: Dividend growth during high-growth phase
            high_growth_years: Duration of high-growth period (typically 5-10 years)
            terminal_growth: Stable growth rate after high-growth period
            cost_of_equity: Required return on equity

        Returns:
            MethodResult with fair value
        """
        warnings = []

        # Validate inputs
        if current_dividend <= 0:
            return self._create_error_result(
                ValuationMethod.DDM_TWO_STAGE,
                "Company must pay dividends for DDM valuation",
            )

        if cost_of_equity <= terminal_growth:
            warnings.append("Cost of equity adjusted to exceed terminal growth")
            terminal_growth = cost_of_equity - 0.02

        if high_growth_rate > 0.25:
            warnings.append(f"High growth rate ({high_growth_rate:.2%}) is aggressive")

        # Calculate Stage 1: Present value of high-growth dividends
        pv_stage1 = 0
        dividend = current_dividend

        for year in range(1, high_growth_years + 1):
            dividend = dividend * (1 + high_growth_rate)
            pv_stage1 += dividend / ((1 + cost_of_equity) ** year)

        # Calculate Stage 2: Terminal value at end of high-growth period
        # D_(n+1) = D_n * (1 + g_terminal)
        terminal_dividend = dividend * (1 + terminal_growth)
        terminal_value = terminal_dividend / (cost_of_equity - terminal_growth)

        # Present value of terminal value
        pv_terminal = terminal_value / ((1 + cost_of_equity) ** high_growth_years)

        # Total fair value
        fair_value = pv_stage1 + pv_terminal

        # Calculate range
        low_estimate = fair_value * 0.80
        high_estimate = fair_value * 1.25

        confidence = self._calculate_confidence(terminal_growth, cost_of_equity) - 5  # Slightly less confident

        logger.debug(
            "Two-Stage DDM complete",
            fair_value=fair_value,
            pv_stage1=pv_stage1,
            pv_terminal=pv_terminal,
        )

        return MethodResult(
            method=ValuationMethod.DDM_TWO_STAGE,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "current_dividend": round(current_dividend, 4),
                "high_growth_rate": round(high_growth_rate, 4),
                "high_growth_years": high_growth_years,
                "terminal_growth": round(terminal_growth, 4),
                "cost_of_equity": round(cost_of_equity, 4),
            },
            calculation_details={
                "pv_high_growth_dividends": pv_stage1,
                "terminal_dividend": terminal_dividend,
                "terminal_value": terminal_value,
                "pv_terminal_value": pv_terminal,
            },
            warnings=warnings,
        )

    def h_model(
        self,
        current_dividend: float,
        initial_growth: float,
        terminal_growth: float,
        half_life_years: float,
        cost_of_equity: float,
    ) -> MethodResult:
        """
        H-Model for gradual growth decline.

        Assumes growth rate declines linearly from initial to terminal rate.

        Formula: P = D0 * (1+gL) / (r-gL) + D0 * H * (gS-gL) / (r-gL)

        Args:
            current_dividend: Current annual dividend per share
            initial_growth: Initial high growth rate (gS)
            terminal_growth: Long-term stable growth rate (gL)
            half_life_years: Half the period of high growth (H)
            cost_of_equity: Required return on equity

        Returns:
            MethodResult with fair value
        """
        warnings = []

        # Validate inputs
        if current_dividend <= 0:
            return self._create_error_result(
                ValuationMethod.DDM_H_MODEL,
                "Company must pay dividends for DDM valuation",
            )

        if cost_of_equity <= terminal_growth:
            warnings.append("Cost of equity adjusted to exceed terminal growth")
            terminal_growth = cost_of_equity - 0.02

        if initial_growth <= terminal_growth:
            warnings.append("Initial growth should exceed terminal growth for H-Model")
            # Fall back to Gordon Growth
            return self.gordon_growth(current_dividend, terminal_growth, cost_of_equity)

        # H-Model formula
        # Term 1: Stable growth component
        term1 = (current_dividend * (1 + terminal_growth)) / (cost_of_equity - terminal_growth)

        # Term 2: Extra value from initially higher growth
        term2 = (
            current_dividend * half_life_years * (initial_growth - terminal_growth)
        ) / (cost_of_equity - terminal_growth)

        fair_value = term1 + term2

        # Calculate range
        low_estimate = fair_value * 0.85
        high_estimate = fair_value * 1.20

        confidence = self._calculate_confidence(terminal_growth, cost_of_equity) - 5

        logger.debug(
            "H-Model DDM complete",
            fair_value=fair_value,
            stable_component=term1,
            growth_premium=term2,
        )

        return MethodResult(
            method=ValuationMethod.DDM_H_MODEL,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "current_dividend": round(current_dividend, 4),
                "initial_growth": round(initial_growth, 4),
                "terminal_growth": round(terminal_growth, 4),
                "half_life_years": half_life_years,
                "cost_of_equity": round(cost_of_equity, 4),
            },
            calculation_details={
                "stable_growth_value": term1,
                "excess_growth_value": term2,
            },
            warnings=warnings,
        )

    def _calculate_confidence(self, growth: float, cost_of_equity: float) -> float:
        """Calculate confidence score based on assumptions."""
        confidence = 75.0

        # Higher confidence for moderate growth
        if 0 <= growth <= 0.05:
            confidence += 5
        elif growth > 0.08:
            confidence -= 10

        # Reduce for narrow spread
        spread = cost_of_equity - growth
        if spread < 0.03:
            confidence -= 10

        return max(40, min(85, confidence))

    def _create_error_result(self, method: ValuationMethod, error_message: str) -> MethodResult:
        """Create an error result when valuation cannot be performed."""
        return MethodResult(
            method=method,
            fair_value=0,
            confidence=0,
            data_quality=DataQuality.INSUFFICIENT,
            warnings=[error_message],
        )

    def estimate_dividend_growth(
        self,
        payout_ratio: float,
        roe: float,
        historical_growth: float | None = None,
    ) -> float:
        """
        Estimate sustainable dividend growth rate.

        g = Retention Rate × ROE = (1 - Payout Ratio) × ROE

        Args:
            payout_ratio: Dividend payout ratio (0-1)
            roe: Return on Equity
            historical_growth: Historical dividend growth (optional)

        Returns:
            Estimated sustainable growth rate
        """
        # Calculate sustainable growth
        retention_rate = 1 - min(1, max(0, payout_ratio))
        sustainable_growth = retention_rate * roe

        # Cap at reasonable levels
        sustainable_growth = max(-0.05, min(0.15, sustainable_growth))

        # Blend with historical if available
        if historical_growth is not None:
            # Weight historical more heavily for established companies
            return 0.4 * sustainable_growth + 0.6 * historical_growth

        return sustainable_growth
