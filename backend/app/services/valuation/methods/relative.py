"""
Relative Valuation Methods.

Implements multiples-based valuation:
- P/E (Price-to-Earnings)
- P/B (Price-to-Book)
- P/S (Price-to-Sales)
- EV/EBITDA
- EV/Revenue
- EV/FCF
"""

import structlog

from ..models import DataQuality, MethodResult, ValuationMethod

logger = structlog.get_logger(__name__)


class RelativeValuation:
    """
    Relative valuation using peer multiples.

    Compares company metrics to peer group averages
    to determine fair value.
    """

    def pe_valuation(
        self,
        eps: float,
        peer_pe_median: float,
        peer_pe_range: tuple[float, float] | None = None,
        growth_adjustment: float | None = None,
    ) -> MethodResult:
        """
        Price-to-Earnings multiple valuation.

        Fair Value = EPS × Target P/E

        Args:
            eps: Earnings per share (trailing or forward)
            peer_pe_median: Median P/E of peer group
            peer_pe_range: (low, high) P/E range from peers
            growth_adjustment: Adjustment factor for growth differential

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if eps <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_PE,
                "Cannot use P/E valuation with negative or zero EPS",
            )

        if peer_pe_median <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_PE,
                "Invalid peer P/E multiple",
            )

        # Apply growth adjustment if provided
        target_pe = peer_pe_median
        if growth_adjustment is not None:
            target_pe = peer_pe_median * growth_adjustment
            if growth_adjustment > 1.2 or growth_adjustment < 0.8:
                warnings.append(f"Significant growth adjustment applied ({growth_adjustment:.2f}x)")

        # Cap P/E at reasonable levels
        target_pe = max(5, min(50, target_pe))

        fair_value = eps * target_pe

        # Calculate range
        if peer_pe_range:
            low_estimate = eps * max(5, peer_pe_range[0])
            high_estimate = eps * min(50, peer_pe_range[1])
        else:
            low_estimate = eps * target_pe * 0.85
            high_estimate = eps * target_pe * 1.15

        confidence = 75.0
        if peer_pe_range is None:
            confidence -= 10
        if warnings:
            confidence -= 5

        logger.debug(
            "P/E valuation complete",
            fair_value=fair_value,
            eps=eps,
            target_pe=target_pe,
        )

        return MethodResult(
            method=ValuationMethod.RELATIVE_PE,
            fair_value=fair_value,
            confidence=confidence,
            data_quality=DataQuality.HIGH if peer_pe_range else DataQuality.MEDIUM,
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            assumptions={
                "eps": round(eps, 4),
                "peer_pe_median": round(peer_pe_median, 2),
                "target_pe": round(target_pe, 2),
                "growth_adjustment": growth_adjustment,
            },
            calculation_details={
                "implied_pe_at_fair_value": target_pe,
            },
            warnings=warnings,
        )

    def pb_valuation(
        self,
        book_value_per_share: float,
        peer_pb_median: float,
        peer_pb_range: tuple[float, float] | None = None,
        roe_adjustment: float | None = None,
    ) -> MethodResult:
        """
        Price-to-Book multiple valuation.

        Fair Value = Book Value per Share × Target P/B

        Best for: Banks, insurance, asset-heavy industries.

        Args:
            book_value_per_share: Book value per share
            peer_pb_median: Median P/B of peer group
            peer_pb_range: (low, high) P/B range from peers
            roe_adjustment: Adjustment based on ROE vs peers

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if book_value_per_share <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_PB,
                "Cannot use P/B valuation with negative book value",
            )

        if peer_pb_median <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_PB,
                "Invalid peer P/B multiple",
            )

        target_pb = peer_pb_median
        if roe_adjustment is not None:
            target_pb = peer_pb_median * roe_adjustment

        # Cap P/B at reasonable levels
        target_pb = max(0.3, min(10, target_pb))

        fair_value = book_value_per_share * target_pb

        if peer_pb_range:
            low_estimate = book_value_per_share * max(0.3, peer_pb_range[0])
            high_estimate = book_value_per_share * min(10, peer_pb_range[1])
        else:
            low_estimate = fair_value * 0.80
            high_estimate = fair_value * 1.20

        confidence = 70.0
        if peer_pb_range is None:
            confidence -= 10

        logger.debug(
            "P/B valuation complete",
            fair_value=fair_value,
            book_value=book_value_per_share,
            target_pb=target_pb,
        )

        return MethodResult(
            method=ValuationMethod.RELATIVE_PB,
            fair_value=fair_value,
            confidence=confidence,
            data_quality=DataQuality.HIGH if peer_pb_range else DataQuality.MEDIUM,
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            assumptions={
                "book_value_per_share": round(book_value_per_share, 4),
                "peer_pb_median": round(peer_pb_median, 2),
                "target_pb": round(target_pb, 2),
                "roe_adjustment": roe_adjustment,
            },
            calculation_details={
                "implied_pb_at_fair_value": target_pb,
            },
            warnings=warnings,
        )

    def ps_valuation(
        self,
        revenue_per_share: float,
        peer_ps_median: float,
        peer_ps_range: tuple[float, float] | None = None,
        margin_adjustment: float | None = None,
    ) -> MethodResult:
        """
        Price-to-Sales multiple valuation.

        Fair Value = Revenue per Share × Target P/S

        Best for: High-growth, unprofitable companies.

        Args:
            revenue_per_share: Revenue per share
            peer_ps_median: Median P/S of peer group
            peer_ps_range: (low, high) P/S range from peers
            margin_adjustment: Adjustment based on margin differential

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if revenue_per_share <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_PS,
                "Cannot use P/S valuation with zero revenue",
            )

        target_ps = peer_ps_median
        if margin_adjustment is not None:
            target_ps = peer_ps_median * margin_adjustment

        # Cap P/S at reasonable levels
        target_ps = max(0.2, min(20, target_ps))

        fair_value = revenue_per_share * target_ps

        if peer_ps_range:
            low_estimate = revenue_per_share * max(0.2, peer_ps_range[0])
            high_estimate = revenue_per_share * min(20, peer_ps_range[1])
        else:
            low_estimate = fair_value * 0.75
            high_estimate = fair_value * 1.30

        confidence = 65.0  # Lower confidence for P/S
        if peer_ps_range is None:
            confidence -= 10

        return MethodResult(
            method=ValuationMethod.RELATIVE_PS,
            fair_value=fair_value,
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            assumptions={
                "revenue_per_share": round(revenue_per_share, 4),
                "peer_ps_median": round(peer_ps_median, 2),
                "target_ps": round(target_ps, 2),
            },
            warnings=warnings,
        )

    def ev_ebitda_valuation(
        self,
        ebitda: float,
        net_debt: float,
        shares_outstanding: int,
        peer_ev_ebitda_median: float,
        peer_ev_ebitda_range: tuple[float, float] | None = None,
    ) -> MethodResult:
        """
        EV/EBITDA multiple valuation.

        EV = EBITDA × Target Multiple
        Equity Value = EV - Net Debt
        Fair Value = Equity Value / Shares

        Best for: Capital-intensive businesses, M&A valuation.

        Args:
            ebitda: Earnings Before Interest, Taxes, D&A
            net_debt: Total debt minus cash
            shares_outstanding: Diluted shares outstanding
            peer_ev_ebitda_median: Median EV/EBITDA of peers
            peer_ev_ebitda_range: (low, high) range from peers

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if ebitda <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_EV_EBITDA,
                "Cannot use EV/EBITDA with negative EBITDA",
            )

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_EV_EBITDA,
                "Invalid shares outstanding",
            )

        # Cap multiple at reasonable levels
        target_multiple = max(3, min(25, peer_ev_ebitda_median))

        enterprise_value = ebitda * target_multiple
        equity_value = enterprise_value - net_debt
        fair_value = equity_value / shares_outstanding

        if peer_ev_ebitda_range:
            ev_low = ebitda * max(3, peer_ev_ebitda_range[0])
            ev_high = ebitda * min(25, peer_ev_ebitda_range[1])
            low_estimate = (ev_low - net_debt) / shares_outstanding
            high_estimate = (ev_high - net_debt) / shares_outstanding
        else:
            low_estimate = fair_value * 0.80
            high_estimate = fair_value * 1.25

        confidence = 75.0
        if fair_value < 0:
            warnings.append("Negative fair value indicates high debt relative to EBITDA")
            confidence -= 20

        logger.debug(
            "EV/EBITDA valuation complete",
            fair_value=fair_value,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
        )

        return MethodResult(
            method=ValuationMethod.RELATIVE_EV_EBITDA,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.HIGH if peer_ev_ebitda_range else DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=max(0, high_estimate),
            assumptions={
                "ebitda": round(ebitda, 0),
                "net_debt": round(net_debt, 0),
                "peer_ev_ebitda_median": round(peer_ev_ebitda_median, 2),
                "target_multiple": round(target_multiple, 2),
            },
            calculation_details={
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
                "shares_outstanding": shares_outstanding,
            },
            warnings=warnings,
        )

    def ev_revenue_valuation(
        self,
        revenue: float,
        net_debt: float,
        shares_outstanding: int,
        peer_ev_revenue_median: float,
        peer_ev_revenue_range: tuple[float, float] | None = None,
        growth_rate: float | None = None,
    ) -> MethodResult:
        """
        EV/Revenue multiple valuation.

        Best for: High-growth, unprofitable companies (SaaS, biotech).

        Args:
            revenue: Total revenue
            net_debt: Total debt minus cash
            shares_outstanding: Diluted shares outstanding
            peer_ev_revenue_median: Median EV/Revenue of peers
            peer_ev_revenue_range: (low, high) range from peers
            growth_rate: Revenue growth rate for adjustment

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if revenue <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_EV_REVENUE,
                "Cannot use EV/Revenue with zero revenue",
            )

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.RELATIVE_EV_REVENUE,
                "Invalid shares outstanding",
            )

        target_multiple = peer_ev_revenue_median

        # Adjust for growth differential
        if growth_rate is not None and growth_rate > 0.20:
            # Higher growth justifies premium multiple
            growth_premium = 1 + (growth_rate - 0.15) * 0.5
            target_multiple = peer_ev_revenue_median * min(1.5, growth_premium)
            warnings.append(f"Growth premium applied ({growth_premium:.2f}x)")

        # Cap multiple
        target_multiple = max(0.5, min(20, target_multiple))

        enterprise_value = revenue * target_multiple
        equity_value = enterprise_value - net_debt
        fair_value = equity_value / shares_outstanding

        if peer_ev_revenue_range:
            ev_low = revenue * max(0.5, peer_ev_revenue_range[0])
            ev_high = revenue * min(20, peer_ev_revenue_range[1])
            low_estimate = (ev_low - net_debt) / shares_outstanding
            high_estimate = (ev_high - net_debt) / shares_outstanding
        else:
            low_estimate = fair_value * 0.70
            high_estimate = fair_value * 1.40

        confidence = 60.0  # Lower confidence for revenue multiples

        return MethodResult(
            method=ValuationMethod.RELATIVE_EV_REVENUE,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=max(0, high_estimate),
            assumptions={
                "revenue": round(revenue, 0),
                "net_debt": round(net_debt, 0),
                "peer_ev_revenue_median": round(peer_ev_revenue_median, 2),
                "target_multiple": round(target_multiple, 2),
                "growth_rate": growth_rate,
            },
            calculation_details={
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
            },
            warnings=warnings,
        )

    def _create_error_result(self, method: ValuationMethod, error_message: str) -> MethodResult:
        """Create an error result when valuation cannot be performed."""
        return MethodResult(
            method=method,
            fair_value=0,
            confidence=0,
            data_quality=DataQuality.INSUFFICIENT,
            warnings=[error_message],
        )

    def get_default_multiples(self, sector: str) -> dict[str, dict]:
        """
        Get industry-average multiples as fallback.

        Returns default multiples when peer data unavailable.
        """
        sector_defaults = {
            "technology": {
                "pe": {"median": 25.0, "low": 18.0, "high": 35.0},
                "pb": {"median": 5.0, "low": 3.0, "high": 8.0},
                "ev_ebitda": {"median": 15.0, "low": 10.0, "high": 22.0},
                "ev_revenue": {"median": 5.0, "low": 3.0, "high": 10.0},
            },
            "financial services": {
                "pe": {"median": 12.0, "low": 8.0, "high": 16.0},
                "pb": {"median": 1.2, "low": 0.8, "high": 1.8},
                "ev_ebitda": {"median": 8.0, "low": 5.0, "high": 12.0},
            },
            "healthcare": {
                "pe": {"median": 22.0, "low": 15.0, "high": 30.0},
                "ev_ebitda": {"median": 14.0, "low": 10.0, "high": 20.0},
            },
            "consumer cyclical": {
                "pe": {"median": 18.0, "low": 12.0, "high": 25.0},
                "ev_ebitda": {"median": 10.0, "low": 7.0, "high": 15.0},
            },
            "consumer defensive": {
                "pe": {"median": 20.0, "low": 16.0, "high": 26.0},
                "ev_ebitda": {"median": 12.0, "low": 9.0, "high": 16.0},
            },
            "industrials": {
                "pe": {"median": 18.0, "low": 12.0, "high": 24.0},
                "ev_ebitda": {"median": 10.0, "low": 7.0, "high": 14.0},
            },
            "energy": {
                "pe": {"median": 12.0, "low": 6.0, "high": 18.0},
                "ev_ebitda": {"median": 6.0, "low": 4.0, "high": 10.0},
            },
            "utilities": {
                "pe": {"median": 16.0, "low": 12.0, "high": 20.0},
                "ev_ebitda": {"median": 10.0, "low": 8.0, "high": 13.0},
            },
            "real estate": {
                "pe": {"median": 30.0, "low": 20.0, "high": 45.0},
                "pb": {"median": 1.5, "low": 1.0, "high": 2.5},
            },
            "basic materials": {
                "pe": {"median": 14.0, "low": 8.0, "high": 20.0},
                "ev_ebitda": {"median": 7.0, "low": 5.0, "high": 10.0},
            },
            "communication services": {
                "pe": {"median": 20.0, "low": 14.0, "high": 28.0},
                "ev_ebitda": {"median": 10.0, "low": 7.0, "high": 15.0},
            },
        }

        sector_key = sector.lower() if sector else ""
        return sector_defaults.get(sector_key, {
            "pe": {"median": 18.0, "low": 12.0, "high": 25.0},
            "pb": {"median": 2.5, "low": 1.5, "high": 4.0},
            "ev_ebitda": {"median": 12.0, "low": 8.0, "high": 18.0},
            "ev_revenue": {"median": 2.0, "low": 1.0, "high": 4.0},
        })
