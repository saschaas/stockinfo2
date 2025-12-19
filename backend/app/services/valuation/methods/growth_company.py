"""
Growth Company Valuation Methods.

Specialized methods for high-growth, often unprofitable companies:
- Rule of 40
- EV/ARR (Annual Recurring Revenue)
"""

import structlog

from ..models import DataQuality, MethodResult, ValuationMethod

logger = structlog.get_logger(__name__)


class GrowthCompanyValuation:
    """
    Valuation methods for growth companies.

    Best for:
    - SaaS and subscription businesses
    - High-growth tech companies
    - Pre-profit companies with strong revenue growth
    """

    # EV/ARR multiple ranges by growth rate
    EV_ARR_MULTIPLES = {
        "hyper_growth": {"min_growth": 0.60, "multiple_range": (15, 25)},  # >60% growth
        "high_growth": {"min_growth": 0.40, "multiple_range": (10, 18)},  # 40-60%
        "solid_growth": {"min_growth": 0.25, "multiple_range": (6, 12)},  # 25-40%
        "moderate_growth": {"min_growth": 0.15, "multiple_range": (4, 8)},  # 15-25%
        "low_growth": {"min_growth": 0, "multiple_range": (2, 5)},  # <15%
    }

    def rule_of_40(
        self,
        revenue: float,
        revenue_growth_rate: float,
        profit_margin: float,
        net_debt: float,
        shares_outstanding: int,
        peer_ev_revenue_median: float | None = None,
    ) -> MethodResult:
        """
        Rule of 40 valuation for SaaS/growth companies.

        Rule of 40 Score = Revenue Growth Rate (%) + Profit Margin (%)
        Companies scoring 40+ are considered healthy.

        Adjusts EV/Revenue multiple based on Rule of 40 score.

        Args:
            revenue: Total revenue (or ARR for SaaS)
            revenue_growth_rate: Revenue growth rate as decimal
            profit_margin: Operating or EBITDA margin as decimal
            net_debt: Net debt (debt - cash)
            shares_outstanding: Shares outstanding
            peer_ev_revenue_median: Optional peer EV/Revenue multiple

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if revenue <= 0:
            return self._create_error_result(
                ValuationMethod.GROWTH_RULE_40,
                "Revenue must be positive",
            )

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.GROWTH_RULE_40,
                "Invalid shares outstanding",
            )

        # Calculate Rule of 40 score
        growth_pct = revenue_growth_rate * 100
        margin_pct = profit_margin * 100
        rule_of_40_score = growth_pct + margin_pct

        # Determine base EV/Revenue multiple
        if peer_ev_revenue_median:
            base_multiple = peer_ev_revenue_median
        else:
            # Default based on growth rate
            base_multiple = self._get_base_multiple_for_growth(revenue_growth_rate)

        # Adjust multiple based on Rule of 40 score
        if rule_of_40_score >= 60:
            multiple_adjustment = 1.3
        elif rule_of_40_score >= 40:
            multiple_adjustment = 1.1
        elif rule_of_40_score >= 25:
            multiple_adjustment = 0.9
        elif rule_of_40_score >= 10:
            multiple_adjustment = 0.7
        else:
            multiple_adjustment = 0.5
            warnings.append(f"Low Rule of 40 score ({rule_of_40_score:.1f}) indicates poor efficiency")

        target_multiple = base_multiple * multiple_adjustment
        target_multiple = max(1, min(20, target_multiple))

        # Calculate fair value
        enterprise_value = revenue * target_multiple
        equity_value = enterprise_value - net_debt
        fair_value = equity_value / shares_outstanding

        # Calculate range
        low_estimate = fair_value * 0.70
        high_estimate = fair_value * 1.40

        # Confidence based on score
        confidence = 60.0
        if rule_of_40_score >= 40:
            confidence += 10
        elif rule_of_40_score < 20:
            confidence -= 10

        logger.debug(
            "Rule of 40 valuation complete",
            rule_of_40_score=rule_of_40_score,
            fair_value=fair_value,
            target_multiple=target_multiple,
        )

        return MethodResult(
            method=ValuationMethod.GROWTH_RULE_40,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "revenue": round(revenue, 0),
                "revenue_growth_rate": round(revenue_growth_rate, 4),
                "profit_margin": round(profit_margin, 4),
                "rule_of_40_score": round(rule_of_40_score, 1),
                "base_multiple": round(base_multiple, 2),
                "multiple_adjustment": round(multiple_adjustment, 2),
                "target_multiple": round(target_multiple, 2),
            },
            calculation_details={
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
                "net_debt": net_debt,
            },
            warnings=warnings,
        )

    def ev_arr_valuation(
        self,
        arr: float,
        growth_rate: float,
        net_debt: float,
        shares_outstanding: int,
        net_revenue_retention: float | None = None,
        gross_margin: float | None = None,
    ) -> MethodResult:
        """
        EV/ARR valuation for SaaS companies.

        Determines appropriate multiple based on growth rate and
        SaaS quality metrics (NRR, gross margin).

        Args:
            arr: Annual Recurring Revenue
            growth_rate: ARR growth rate as decimal
            net_debt: Net debt (debt - cash)
            shares_outstanding: Shares outstanding
            net_revenue_retention: NRR if available (>100% = expansion)
            gross_margin: Gross margin if available

        Returns:
            MethodResult with fair value
        """
        warnings = []

        if arr <= 0:
            return self._create_error_result(
                ValuationMethod.GROWTH_EV_ARR,
                "ARR must be positive",
            )

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.GROWTH_EV_ARR,
                "Invalid shares outstanding",
            )

        # Determine base multiple from growth rate
        base_multiple = self._get_arr_multiple(growth_rate)

        # Adjust for NRR (premium for >120% NRR)
        nrr_adjustment = 1.0
        if net_revenue_retention is not None:
            if net_revenue_retention > 1.30:
                nrr_adjustment = 1.25
                warnings.append(f"Premium applied for excellent NRR ({net_revenue_retention:.0%})")
            elif net_revenue_retention > 1.15:
                nrr_adjustment = 1.10
            elif net_revenue_retention < 0.90:
                nrr_adjustment = 0.80
                warnings.append(f"Discount applied for low NRR ({net_revenue_retention:.0%})")

        # Adjust for gross margin (premium for >80%)
        margin_adjustment = 1.0
        if gross_margin is not None:
            if gross_margin > 0.80:
                margin_adjustment = 1.10
            elif gross_margin < 0.60:
                margin_adjustment = 0.85
                warnings.append(f"Discount for low gross margin ({gross_margin:.0%})")

        target_multiple = base_multiple * nrr_adjustment * margin_adjustment
        target_multiple = max(2, min(30, target_multiple))

        # Calculate fair value
        enterprise_value = arr * target_multiple
        equity_value = enterprise_value - net_debt
        fair_value = equity_value / shares_outstanding

        # Range based on multiple uncertainty
        low_estimate = fair_value * 0.65
        high_estimate = fair_value * 1.45

        confidence = 55.0
        if growth_rate > 0.40 and (net_revenue_retention or 1.0) > 1.1:
            confidence += 10

        logger.debug(
            "EV/ARR valuation complete",
            fair_value=fair_value,
            target_multiple=target_multiple,
            growth_rate=growth_rate,
        )

        return MethodResult(
            method=ValuationMethod.GROWTH_EV_ARR,
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "arr": round(arr, 0),
                "growth_rate": round(growth_rate, 4),
                "base_multiple": round(base_multiple, 2),
                "nrr_adjustment": round(nrr_adjustment, 2),
                "margin_adjustment": round(margin_adjustment, 2),
                "target_multiple": round(target_multiple, 2),
                "net_revenue_retention": net_revenue_retention,
                "gross_margin": gross_margin,
            },
            calculation_details={
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
            },
            warnings=warnings,
        )

    def _get_base_multiple_for_growth(self, growth_rate: float) -> float:
        """Get base EV/Revenue multiple based on growth rate."""
        if growth_rate >= 0.50:
            return 10.0
        elif growth_rate >= 0.30:
            return 7.0
        elif growth_rate >= 0.20:
            return 5.0
        elif growth_rate >= 0.10:
            return 3.0
        else:
            return 2.0

    def _get_arr_multiple(self, growth_rate: float) -> float:
        """Get EV/ARR multiple based on growth rate."""
        for tier_name, tier_data in self.EV_ARR_MULTIPLES.items():
            if growth_rate >= tier_data["min_growth"]:
                low, high = tier_data["multiple_range"]
                # Interpolate within range based on growth
                range_width = high - low
                multiple = low + range_width * 0.5  # Use midpoint
                return multiple

        return 3.0  # Default for very low growth

    def calculate_ltv_cac_implied_value(
        self,
        ltv: float,
        cac: float,
        customer_count: int,
        net_debt: float,
        shares_outstanding: int,
        growth_rate: float = 0.20,
    ) -> MethodResult:
        """
        LTV/CAC based valuation for customer-centric businesses.

        Calculates enterprise value based on customer economics.

        Args:
            ltv: Customer Lifetime Value
            cac: Customer Acquisition Cost
            customer_count: Number of customers
            net_debt: Net debt
            shares_outstanding: Shares outstanding
            growth_rate: Expected customer growth rate

        Returns:
            MethodResult with implied fair value
        """
        warnings = []

        ltv_cac_ratio = ltv / cac if cac > 0 else 0

        if ltv_cac_ratio < 1:
            warnings.append("LTV/CAC < 1 indicates unprofitable customer acquisition")

        # Value of existing customer base
        customer_base_value = customer_count * ltv

        # Apply growth premium (simplified)
        growth_premium = 1 + growth_rate * 3  # 3x growth rate as premium

        enterprise_value = customer_base_value * growth_premium
        equity_value = enterprise_value - net_debt
        fair_value = equity_value / shares_outstanding

        confidence = 50.0  # Lower confidence for this method
        if ltv_cac_ratio >= 3:
            confidence += 10

        return MethodResult(
            method=ValuationMethod.GROWTH_EV_ARR,  # Using EV_ARR as closest enum
            fair_value=max(0, fair_value),
            confidence=confidence,
            data_quality=DataQuality.LOW,
            low_estimate=fair_value * 0.60,
            high_estimate=fair_value * 1.50,
            assumptions={
                "ltv": round(ltv, 2),
                "cac": round(cac, 2),
                "ltv_cac_ratio": round(ltv_cac_ratio, 2),
                "customer_count": customer_count,
                "growth_premium": round(growth_premium, 2),
            },
            calculation_details={
                "customer_base_value": customer_base_value,
                "enterprise_value": enterprise_value,
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
