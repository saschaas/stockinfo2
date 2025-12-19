"""
WACC and Cost of Capital Calculator.

Provides calculation of:
- Cost of Equity using CAPM
- Cost of Debt using synthetic rating method
- Weighted Average Cost of Capital (WACC)
"""

import structlog

from ..models import CAPMInputs, MarketInputs, WACCInputs

logger = structlog.get_logger(__name__)


class WACCCalculator:
    """
    Calculator for discount rates used in DCF valuation.

    Implements:
    - CAPM for cost of equity
    - Synthetic rating method for cost of debt
    - WACC calculation
    """

    # Interest Coverage to Credit Rating to Default Spread mapping
    # Based on Damodaran's synthetic rating methodology
    INTEREST_COVERAGE_RATINGS = [
        # (min_coverage, rating, default_spread)
        (12.5, "AAA", 0.0040),  # >12.5x: AAA, 0.40%
        (8.5, "AA", 0.0045),  # 8.5-12.5x: AA, 0.45%
        (6.5, "A+", 0.0060),  # 6.5-8.5x: A+, 0.60%
        (5.5, "A", 0.0075),  # 5.5-6.5x: A, 0.75%
        (4.25, "A-", 0.0085),  # 4.25-5.5x: A-, 0.85%
        (3.0, "BBB", 0.0110),  # 3.0-4.25x: BBB, 1.10%
        (2.5, "BB+", 0.0150),  # 2.5-3.0x: BB+, 1.50%
        (2.0, "BB", 0.0200),  # 2.0-2.5x: BB, 2.00%
        (1.75, "BB-", 0.0240),  # 1.75-2.0x: BB-, 2.40%
        (1.5, "B+", 0.0261),  # 1.5-1.75x: B+, 2.61%
        (1.25, "B", 0.0360),  # 1.25-1.5x: B, 3.60%
        (0.8, "B-", 0.0510),  # 0.8-1.25x: B-, 5.10%
        (0.65, "CCC", 0.0728),  # 0.65-0.8x: CCC, 7.28%
        (0.2, "CC", 0.0994),  # 0.2-0.65x: CC, 9.94%
        (float("-inf"), "D", 0.1350),  # <0.2x: D, 13.50%
    ]

    # Default tax rate
    DEFAULT_TAX_RATE = 0.21  # US corporate tax rate

    def __init__(self, market_inputs: MarketInputs | None = None):
        """
        Initialize calculator with market inputs.

        Args:
            market_inputs: Market-level inputs (risk-free rate, ERP)
        """
        self.market_inputs = market_inputs or MarketInputs()

    def calculate_cost_of_equity(
        self,
        beta: float,
        market_cap: float = 0,
        company_specific_risk: float = 0,
        size_premium: float | None = None,
    ) -> CAPMInputs:
        """
        Calculate cost of equity using CAPM.

        Formula: re = Rf + β × ERP + size_premium + company_risk

        Args:
            beta: Company beta (systematic risk)
            market_cap: Market cap for size premium calculation
            company_specific_risk: Additional company-specific risk premium
            size_premium: Override size premium (if None, calculated from market_cap)

        Returns:
            CAPMInputs with cost of equity and components
        """
        # Ensure beta is reasonable
        beta = max(0.5, min(3.0, beta)) if beta > 0 else 1.0

        # Calculate size premium if not provided
        if size_premium is None:
            size_premium = self._calculate_size_premium(market_cap)

        capm = CAPMInputs(
            beta=beta,
            risk_free_rate=self.market_inputs.risk_free_rate,
            equity_risk_premium=self.market_inputs.equity_risk_premium,
            size_premium=size_premium,
            company_specific_risk=company_specific_risk,
        )

        logger.debug(
            "Calculated cost of equity",
            cost_of_equity=capm.cost_of_equity,
            beta=beta,
            rf=self.market_inputs.risk_free_rate,
            erp=self.market_inputs.equity_risk_premium,
            size_premium=size_premium,
        )

        return capm

    def calculate_cost_of_debt(
        self,
        interest_expense: float = 0,
        total_debt: float = 0,
        ebit: float = 0,
    ) -> tuple[float, str, float]:
        """
        Calculate cost of debt using synthetic rating method.

        Uses interest coverage ratio to determine credit rating,
        then applies appropriate default spread.

        Args:
            interest_expense: Annual interest expense
            total_debt: Total debt
            ebit: Earnings Before Interest and Taxes

        Returns:
            Tuple of (pre-tax cost of debt, synthetic rating, default spread)
        """
        # Try to calculate from interest coverage
        if interest_expense > 0 and ebit != 0:
            interest_coverage = ebit / interest_expense
        elif total_debt > 0:
            # Estimate from yield on debt
            # Assume average interest rate if no expense data
            interest_coverage = 5.0  # Default to BBB territory
        else:
            # No debt
            return self.market_inputs.risk_free_rate, "N/A", 0.0

        # Find rating and spread based on coverage
        rating, spread = self._get_rating_and_spread(interest_coverage)

        cost_of_debt = self.market_inputs.risk_free_rate + spread

        logger.debug(
            "Calculated cost of debt",
            cost_of_debt=cost_of_debt,
            interest_coverage=interest_coverage,
            rating=rating,
            spread=spread,
        )

        return cost_of_debt, rating, spread

    def _get_rating_and_spread(self, interest_coverage: float) -> tuple[str, float]:
        """Get credit rating and default spread from interest coverage."""
        for min_coverage, rating, spread in self.INTEREST_COVERAGE_RATINGS:
            if interest_coverage >= min_coverage:
                return rating, spread

        # Default to CCC
        return "CCC", 0.0728

    def _calculate_size_premium(self, market_cap: float) -> float:
        """
        Calculate size premium based on market capitalization.

        Based on Kroll/Duff & Phelps size premium data.
        """
        if market_cap <= 0:
            return 0.02  # Default 2%

        size_tiers = [
            (50_000_000_000, -0.004),  # >$50B: -0.4%
            (10_000_000_000, 0.0),  # $10B-$50B: 0%
            (5_000_000_000, 0.008),  # $5B-$10B: 0.8%
            (3_000_000_000, 0.012),  # $3B-$5B: 1.2%
            (1_200_000_000, 0.016),  # $1.2B-$3B: 1.6%
            (600_000_000, 0.020),  # $600M-$1.2B: 2.0%
            (300_000_000, 0.026),  # $300M-$600M: 2.6%
            (150_000_000, 0.032),  # $150M-$300M: 3.2%
            (0, 0.05),  # <$150M: 5.0%
        ]

        for threshold, premium in size_tiers:
            if market_cap >= threshold:
                return premium

        return 0.05

    def calculate_wacc(
        self,
        cost_of_equity: float,
        cost_of_debt: float,
        market_cap: float,
        total_debt: float,
        tax_rate: float | None = None,
    ) -> WACCInputs:
        """
        Calculate Weighted Average Cost of Capital.

        Formula: WACC = (E/V) × re + (D/V) × rd × (1 - T)

        Args:
            cost_of_equity: Cost of equity (re)
            cost_of_debt: Pre-tax cost of debt (rd)
            market_cap: Market value of equity (E)
            total_debt: Market value of debt (D), often approximated by book value
            tax_rate: Corporate tax rate (T)

        Returns:
            WACCInputs with WACC and components
        """
        if tax_rate is None:
            tax_rate = self.DEFAULT_TAX_RATE

        wacc_inputs = WACCInputs(
            cost_of_equity=cost_of_equity,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate,
            market_cap=market_cap,
            total_debt=total_debt,
        )

        logger.debug(
            "Calculated WACC",
            wacc=wacc_inputs.wacc,
            weight_equity=wacc_inputs.weight_equity,
            weight_debt=wacc_inputs.weight_debt,
            cost_of_equity=cost_of_equity,
            cost_of_debt=cost_of_debt,
        )

        return wacc_inputs

    def calculate_full_wacc(
        self,
        beta: float,
        market_cap: float,
        total_debt: float,
        interest_expense: float = 0,
        ebit: float = 0,
        tax_rate: float | None = None,
    ) -> tuple[WACCInputs, CAPMInputs, str]:
        """
        Calculate complete WACC with all components.

        This is the main method that combines all calculations.

        Args:
            beta: Company beta
            market_cap: Market capitalization
            total_debt: Total debt
            interest_expense: Annual interest expense
            ebit: EBIT for interest coverage calculation
            tax_rate: Corporate tax rate

        Returns:
            Tuple of (WACCInputs, CAPMInputs, credit_rating)
        """
        # Step 1: Calculate cost of equity
        capm_inputs = self.calculate_cost_of_equity(beta=beta, market_cap=market_cap)

        # Step 2: Calculate cost of debt
        cost_of_debt, rating, _ = self.calculate_cost_of_debt(
            interest_expense=interest_expense,
            total_debt=total_debt,
            ebit=ebit,
        )

        # Step 3: Calculate WACC
        wacc_inputs = self.calculate_wacc(
            cost_of_equity=capm_inputs.cost_of_equity,
            cost_of_debt=cost_of_debt,
            market_cap=market_cap,
            total_debt=total_debt,
            tax_rate=tax_rate,
        )

        return wacc_inputs, capm_inputs, rating
