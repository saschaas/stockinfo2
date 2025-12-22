"""
Discounted Cash Flow (DCF) Valuation Methods.

Implements:
- FCFF (Free Cash Flow to Firm) - Enterprise value approach
- FCFE (Free Cash Flow to Equity) - Direct equity value approach
"""

import structlog

from ..models import DataQuality, MethodResult, ValuationMethod

logger = structlog.get_logger(__name__)


class DCFValuation:
    """
    DCF valuation using Free Cash Flow projections.

    Supports both FCFF (to firm) and FCFE (to equity) approaches.
    """

    # Default projection assumptions
    DEFAULT_PROJECTION_YEARS = 5
    DEFAULT_TERMINAL_GROWTH = 0.025  # 2.5% perpetual growth (close to GDP growth)
    MAX_TERMINAL_GROWTH = 0.04  # Cap terminal growth at 4%

    # Minimum discount rate floors to prevent unrealistic valuations
    # These are conservative minimums - actual rates should be higher for riskier companies
    MIN_WACC = 0.08  # 8% minimum WACC - any company has this minimum cost of capital
    MIN_COST_OF_EQUITY = 0.10  # 10% minimum cost of equity
    MIN_SPREAD = 0.04  # 4% minimum spread between discount rate and terminal growth

    def __init__(
        self,
        projection_years: int = DEFAULT_PROJECTION_YEARS,
        terminal_growth: float = DEFAULT_TERMINAL_GROWTH,
    ):
        """
        Initialize DCF calculator.

        Args:
            projection_years: Number of years to project FCF
            terminal_growth: Long-term perpetual growth rate
        """
        self.projection_years = projection_years
        self.terminal_growth = min(terminal_growth, self.MAX_TERMINAL_GROWTH)

    def calculate_fcff(
        self,
        current_fcf: float,
        growth_rates: list[float] | None,
        wacc: float,
        terminal_growth: float | None,
        net_debt: float,
        shares_outstanding: int,
    ) -> MethodResult:
        """
        Calculate fair value using FCFF (Free Cash Flow to Firm).

        Enterprise Value = Sum(FCFF_t / (1+WACC)^t) + Terminal Value / (1+WACC)^n
        Equity Value = Enterprise Value - Net Debt
        Fair Value = Equity Value / Shares Outstanding

        Args:
            current_fcf: Current year's free cash flow
            growth_rates: Year-by-year FCF growth rates (or None for auto)
            wacc: Weighted Average Cost of Capital
            terminal_growth: Terminal growth rate (or None for default)
            net_debt: Net debt (total debt - cash)
            shares_outstanding: Diluted shares outstanding

        Returns:
            MethodResult with fair value and calculation details
        """
        terminal_growth = terminal_growth or self.terminal_growth
        warnings = []
        original_wacc = wacc

        # Validate inputs
        if current_fcf <= 0:
            return self._create_error_result(
                ValuationMethod.DCF_FCFF,
                "FCFF must be positive for DCF valuation",
            )

        # Apply minimum WACC floor
        # This prevents unrealistic valuations from low beta/high debt companies
        if wacc < self.MIN_WACC:
            warnings.append(
                f"WACC ({wacc:.2%}) adjusted to minimum floor ({self.MIN_WACC:.2%})"
            )
            wacc = self.MIN_WACC

        # Ensure minimum spread between WACC and terminal growth
        # Small spreads create extremely high terminal values
        min_required_wacc = terminal_growth + self.MIN_SPREAD
        if wacc < min_required_wacc:
            warnings.append(
                f"WACC ({wacc:.2%}) adjusted to maintain {self.MIN_SPREAD:.0%} spread above terminal growth"
            )
            wacc = min_required_wacc

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.DCF_FCFF,
                "Shares outstanding must be positive",
            )

        # Generate growth rates if not provided
        if growth_rates is None:
            growth_rates = self._estimate_growth_rates(current_fcf, self.projection_years)

        # Project FCF for each year
        projected_fcf = []
        fcf = current_fcf
        for i, growth in enumerate(growth_rates[: self.projection_years]):
            fcf = fcf * (1 + growth)
            projected_fcf.append(fcf)

        # Fill remaining years if growth_rates is shorter
        while len(projected_fcf) < self.projection_years:
            fcf = fcf * (1 + self.terminal_growth)
            projected_fcf.append(fcf)

        # Calculate present value of projected FCF
        pv_fcf = 0
        for i, fcf in enumerate(projected_fcf):
            pv_fcf += fcf / ((1 + wacc) ** (i + 1))

        # Terminal value using Gordon Growth Model
        terminal_fcf = projected_fcf[-1] * (1 + terminal_growth)
        terminal_value = terminal_fcf / (wacc - terminal_growth)
        pv_terminal = terminal_value / ((1 + wacc) ** len(projected_fcf))

        # Enterprise value and equity value
        enterprise_value = pv_fcf + pv_terminal
        equity_value = enterprise_value - net_debt
        fair_value_per_share = equity_value / shares_outstanding

        # Calculate range (±15% on growth assumptions)
        low_estimate = fair_value_per_share * 0.85
        high_estimate = fair_value_per_share * 1.20

        # Calculate confidence based on inputs
        confidence = self._calculate_confidence(
            has_growth_rates=growth_rates is not None,
            terminal_growth=terminal_growth,
            wacc=wacc,
        )

        logger.debug(
            "FCFF DCF calculation complete",
            fair_value=fair_value_per_share,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            terminal_value=terminal_value,
        )

        return MethodResult(
            method=ValuationMethod.DCF_FCFF,
            fair_value=max(0, fair_value_per_share),
            confidence=confidence,
            data_quality=DataQuality.HIGH if not warnings else DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "projection_years": self.projection_years,
                "growth_rates": [round(g, 4) for g in growth_rates[: self.projection_years]],
                "wacc": round(wacc, 4),
                "terminal_growth": round(terminal_growth, 4),
            },
            calculation_details={
                "current_fcf": current_fcf,
                "pv_projected_fcf": pv_fcf,
                "terminal_value": terminal_value,
                "pv_terminal_value": pv_terminal,
                "enterprise_value": enterprise_value,
                "net_debt": net_debt,
                "equity_value": equity_value,
                "shares_outstanding": shares_outstanding,
            },
            warnings=warnings,
        )

    def calculate_fcfe(
        self,
        current_fcfe: float,
        growth_rates: list[float] | None,
        cost_of_equity: float,
        terminal_growth: float | None,
        shares_outstanding: int,
    ) -> MethodResult:
        """
        Calculate fair value using FCFE (Free Cash Flow to Equity).

        Equity Value = Sum(FCFE_t / (1+re)^t) + Terminal Value / (1+re)^n
        Fair Value = Equity Value / Shares Outstanding

        Args:
            current_fcfe: Current year's free cash flow to equity
            growth_rates: Year-by-year FCFE growth rates
            cost_of_equity: Cost of equity (discount rate)
            terminal_growth: Terminal growth rate
            shares_outstanding: Diluted shares outstanding

        Returns:
            MethodResult with fair value and calculation details
        """
        terminal_growth = terminal_growth or self.terminal_growth
        warnings = []

        # Validate inputs
        if current_fcfe <= 0:
            return self._create_error_result(
                ValuationMethod.DCF_FCFE,
                "FCFE must be positive for DCF valuation",
            )

        # Apply minimum cost of equity floor
        if cost_of_equity < self.MIN_COST_OF_EQUITY:
            warnings.append(
                f"Cost of equity ({cost_of_equity:.2%}) adjusted to minimum floor ({self.MIN_COST_OF_EQUITY:.2%})"
            )
            cost_of_equity = self.MIN_COST_OF_EQUITY

        # Ensure minimum spread between cost of equity and terminal growth
        min_required_coe = terminal_growth + self.MIN_SPREAD
        if cost_of_equity < min_required_coe:
            warnings.append(
                f"Cost of equity ({cost_of_equity:.2%}) adjusted to maintain {self.MIN_SPREAD:.0%} spread above terminal growth"
            )
            cost_of_equity = min_required_coe

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.DCF_FCFE,
                "Shares outstanding must be positive",
            )

        # Generate growth rates if not provided
        if growth_rates is None:
            growth_rates = self._estimate_growth_rates(current_fcfe, self.projection_years)

        # Project FCFE for each year
        projected_fcfe = []
        fcfe = current_fcfe
        for i, growth in enumerate(growth_rates[: self.projection_years]):
            fcfe = fcfe * (1 + growth)
            projected_fcfe.append(fcfe)

        while len(projected_fcfe) < self.projection_years:
            fcfe = fcfe * (1 + self.terminal_growth)
            projected_fcfe.append(fcfe)

        # Calculate present value of projected FCFE
        pv_fcfe = 0
        for i, fcfe in enumerate(projected_fcfe):
            pv_fcfe += fcfe / ((1 + cost_of_equity) ** (i + 1))

        # Terminal value
        terminal_fcfe = projected_fcfe[-1] * (1 + terminal_growth)
        terminal_value = terminal_fcfe / (cost_of_equity - terminal_growth)
        pv_terminal = terminal_value / ((1 + cost_of_equity) ** len(projected_fcfe))

        # Equity value
        equity_value = pv_fcfe + pv_terminal
        fair_value_per_share = equity_value / shares_outstanding

        # Calculate range
        low_estimate = fair_value_per_share * 0.85
        high_estimate = fair_value_per_share * 1.20

        confidence = self._calculate_confidence(
            has_growth_rates=growth_rates is not None,
            terminal_growth=terminal_growth,
            wacc=cost_of_equity,
        )

        logger.debug(
            "FCFE DCF calculation complete",
            fair_value=fair_value_per_share,
            equity_value=equity_value,
        )

        return MethodResult(
            method=ValuationMethod.DCF_FCFE,
            fair_value=max(0, fair_value_per_share),
            confidence=confidence,
            data_quality=DataQuality.HIGH if not warnings else DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "projection_years": self.projection_years,
                "growth_rates": [round(g, 4) for g in growth_rates[: self.projection_years]],
                "cost_of_equity": round(cost_of_equity, 4),
                "terminal_growth": round(terminal_growth, 4),
            },
            calculation_details={
                "current_fcfe": current_fcfe,
                "pv_projected_fcfe": pv_fcfe,
                "terminal_value": terminal_value,
                "pv_terminal_value": pv_terminal,
                "equity_value": equity_value,
                "shares_outstanding": shares_outstanding,
            },
            warnings=warnings,
        )

    def _estimate_growth_rates(self, current_fcf: float, years: int) -> list[float]:
        """
        Estimate growth rates when not provided.

        Uses a declining growth model:
        - Year 1-2: 10% growth
        - Year 3-4: 7% growth
        - Year 5+: 4% growth (converging to terminal)
        """
        rates = []
        for year in range(years):
            if year < 2:
                rates.append(0.10)  # 10% first two years
            elif year < 4:
                rates.append(0.07)  # 7% years 3-4
            else:
                rates.append(0.04)  # 4% year 5+

        return rates

    def _calculate_confidence(
        self,
        has_growth_rates: bool,
        terminal_growth: float,
        wacc: float,
    ) -> float:
        """Calculate confidence score based on inputs."""
        confidence = 70.0

        # Reduce confidence for estimated growth rates
        if not has_growth_rates:
            confidence -= 10

        # Reduce for aggressive terminal growth
        if terminal_growth > 0.03:
            confidence -= 5

        # Reduce for low WACC (higher valuations)
        if wacc < 0.08:
            confidence -= 5

        # Reduce for very high WACC (may indicate risk)
        if wacc > 0.15:
            confidence -= 5

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

    def calculate_terminal_value_sensitivity(
        self,
        base_fcf: float,
        wacc_range: list[float],
        growth_range: list[float],
        years: int = 5,
    ) -> list[list[float]]:
        """
        Calculate sensitivity matrix for terminal value.

        Returns a 2D matrix of fair values for different
        WACC and growth rate combinations.
        """
        matrix = []

        for wacc in wacc_range:
            row = []
            for growth in growth_range:
                if wacc <= growth:
                    row.append(float("inf"))
                else:
                    # Simple single-stage DCF for sensitivity
                    terminal_value = base_fcf * (1 + growth) / (wacc - growth)
                    row.append(terminal_value)
            matrix.append(row)

        return matrix
