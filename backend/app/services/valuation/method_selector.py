"""
Method Selector for Valuation Engine.

Selects appropriate valuation methods and weights based on:
- Company classification
- Available data
- Industry characteristics
"""

import structlog

from .models import CompanyType, ValuationMethod

logger = structlog.get_logger(__name__)


class MethodSelector:
    """
    Selects appropriate valuation methods based on company type
    and data availability.
    """

    # Method weights by company type
    # Weights should sum to 1.0 for each company type
    METHOD_WEIGHTS: dict[CompanyType, dict[ValuationMethod, float]] = {
        CompanyType.DIVIDEND_PAYER: {
            ValuationMethod.DDM_GORDON: 0.35,
            ValuationMethod.DDM_TWO_STAGE: 0.25,
            ValuationMethod.DCF_FCFE: 0.20,
            ValuationMethod.RELATIVE_PE: 0.10,
            ValuationMethod.RELATIVE_EV_EBITDA: 0.10,
        },
        CompanyType.HIGH_GROWTH: {
            ValuationMethod.DCF_FCFF: 0.30,
            ValuationMethod.RELATIVE_EV_REVENUE: 0.25,
            ValuationMethod.GROWTH_RULE_40: 0.20,
            ValuationMethod.GROWTH_EV_ARR: 0.15,
            ValuationMethod.RELATIVE_PS: 0.10,
        },
        CompanyType.MATURE_GROWTH: {
            ValuationMethod.DCF_FCFF: 0.35,
            ValuationMethod.RELATIVE_EV_EBITDA: 0.25,
            ValuationMethod.RELATIVE_PE: 0.20,
            ValuationMethod.DCF_FCFE: 0.10,
            ValuationMethod.DDM_GORDON: 0.10,
        },
        CompanyType.VALUE: {
            ValuationMethod.RELATIVE_PE: 0.25,
            ValuationMethod.RELATIVE_PB: 0.20,
            ValuationMethod.ASSET_BOOK_VALUE: 0.20,
            ValuationMethod.DCF_FCFF: 0.20,
            ValuationMethod.RELATIVE_EV_EBITDA: 0.15,
        },
        CompanyType.REIT: {
            ValuationMethod.ASSET_NAV: 0.40,
            ValuationMethod.DDM_GORDON: 0.25,
            ValuationMethod.RELATIVE_PB: 0.20,
            ValuationMethod.DCF_FCFE: 0.15,
        },
        CompanyType.BANK: {
            ValuationMethod.RELATIVE_PB: 0.35,
            ValuationMethod.DDM_GORDON: 0.30,
            ValuationMethod.RELATIVE_PE: 0.25,
            ValuationMethod.ASSET_BOOK_VALUE: 0.10,
        },
        CompanyType.INSURANCE: {
            ValuationMethod.RELATIVE_PB: 0.35,
            ValuationMethod.RELATIVE_PE: 0.30,
            ValuationMethod.DDM_GORDON: 0.20,
            ValuationMethod.ASSET_BOOK_VALUE: 0.15,
        },
        CompanyType.UTILITY: {
            ValuationMethod.DDM_GORDON: 0.35,
            ValuationMethod.DCF_FCFF: 0.25,
            ValuationMethod.RELATIVE_EV_EBITDA: 0.20,
            ValuationMethod.RELATIVE_PE: 0.20,
        },
        CompanyType.DISTRESSED: {
            ValuationMethod.ASSET_LIQUIDATION: 0.40,
            ValuationMethod.ASSET_BOOK_VALUE: 0.30,
            ValuationMethod.RELATIVE_EV_REVENUE: 0.20,
            ValuationMethod.RELATIVE_PB: 0.10,
        },
        CompanyType.CYCLICAL: {
            ValuationMethod.DCF_FCFF: 0.30,
            ValuationMethod.RELATIVE_EV_EBITDA: 0.30,
            ValuationMethod.RELATIVE_PE: 0.20,
            ValuationMethod.ASSET_BOOK_VALUE: 0.20,
        },
        CompanyType.COMMODITY: {
            ValuationMethod.RELATIVE_EV_EBITDA: 0.35,
            ValuationMethod.DCF_FCFF: 0.25,
            ValuationMethod.RELATIVE_PB: 0.20,
            ValuationMethod.ASSET_BOOK_VALUE: 0.20,
        },
    }

    # Data requirements for each method
    METHOD_REQUIREMENTS: dict[ValuationMethod, list[str]] = {
        ValuationMethod.DCF_FCFF: ["free_cash_flow", "shares_outstanding", "wacc"],
        ValuationMethod.DCF_FCFE: ["free_cash_flow", "shares_outstanding", "cost_of_equity"],
        ValuationMethod.DDM_GORDON: ["dividend_per_share", "cost_of_equity"],
        ValuationMethod.DDM_TWO_STAGE: ["dividend_per_share", "cost_of_equity"],
        ValuationMethod.DDM_H_MODEL: ["dividend_per_share", "cost_of_equity"],
        ValuationMethod.RELATIVE_PE: ["eps", "peer_pe"],
        ValuationMethod.RELATIVE_PB: ["book_value_per_share", "peer_pb"],
        ValuationMethod.RELATIVE_PS: ["revenue_per_share", "peer_ps"],
        ValuationMethod.RELATIVE_EV_EBITDA: ["ebitda", "shares_outstanding", "peer_ev_ebitda"],
        ValuationMethod.RELATIVE_EV_REVENUE: ["revenue", "shares_outstanding", "peer_ev_revenue"],
        ValuationMethod.ASSET_BOOK_VALUE: ["total_assets", "total_liabilities", "shares_outstanding"],
        ValuationMethod.ASSET_NAV: ["noi", "cap_rate", "shares_outstanding"],
        ValuationMethod.ASSET_LIQUIDATION: ["total_assets", "total_liabilities", "shares_outstanding"],
        ValuationMethod.GROWTH_RULE_40: ["revenue", "revenue_growth", "profit_margin", "shares_outstanding"],
        ValuationMethod.GROWTH_EV_ARR: ["arr", "growth_rate", "shares_outstanding"],
    }

    def select_methods(
        self,
        company_type: CompanyType,
        available_data: dict[str, bool],
    ) -> list[tuple[ValuationMethod, float]]:
        """
        Select methods and weights based on company type and data availability.

        Args:
            company_type: Classification of the company
            available_data: Dict of data field -> availability (True/False)

        Returns:
            List of (method, weight) tuples, weights normalized to sum to 1.0
        """
        base_weights = self.METHOD_WEIGHTS.get(
            company_type,
            self.METHOD_WEIGHTS[CompanyType.MATURE_GROWTH],
        )

        selected = []
        for method, weight in base_weights.items():
            if self._can_execute_method(method, available_data):
                selected.append((method, weight))
            else:
                logger.debug(
                    "Method skipped due to missing data",
                    method=method.value,
                    missing=self._get_missing_requirements(method, available_data),
                )

        # Normalize weights to sum to 1.0
        total_weight = sum(w for _, w in selected)
        if total_weight > 0:
            selected = [(m, w / total_weight) for m, w in selected]

        logger.info(
            "Selected valuation methods",
            company_type=company_type.value,
            methods=[m.value for m, _ in selected],
            weights=[round(w, 3) for _, w in selected],
        )

        return selected

    def _can_execute_method(
        self,
        method: ValuationMethod,
        available_data: dict[str, bool],
    ) -> bool:
        """Check if required data is available for a method."""
        requirements = self.METHOD_REQUIREMENTS.get(method, [])

        # Check each requirement
        for req in requirements:
            # Skip discount rate requirements as they're always calculated
            if req in ["wacc", "cost_of_equity"]:
                continue
            # For peer data, we'll use defaults if not available
            if req.startswith("peer_"):
                continue
            if not available_data.get(req, False):
                return False

        return True

    def _get_missing_requirements(
        self,
        method: ValuationMethod,
        available_data: dict[str, bool],
    ) -> list[str]:
        """Get list of missing requirements for a method."""
        requirements = self.METHOD_REQUIREMENTS.get(method, [])
        missing = []

        for req in requirements:
            if req in ["wacc", "cost_of_equity"]:
                continue
            if req.startswith("peer_"):
                continue
            if not available_data.get(req, False):
                missing.append(req)

        return missing

    def get_method_description(self, method: ValuationMethod) -> str:
        """Get human-readable description of a valuation method."""
        descriptions = {
            ValuationMethod.DCF_FCFF: "Discounted Cash Flow (Free Cash Flow to Firm)",
            ValuationMethod.DCF_FCFE: "Discounted Cash Flow (Free Cash Flow to Equity)",
            ValuationMethod.DDM_GORDON: "Gordon Growth Dividend Discount Model",
            ValuationMethod.DDM_TWO_STAGE: "Two-Stage Dividend Discount Model",
            ValuationMethod.DDM_H_MODEL: "H-Model Dividend Discount",
            ValuationMethod.RELATIVE_PE: "Price-to-Earnings Multiple",
            ValuationMethod.RELATIVE_PB: "Price-to-Book Multiple",
            ValuationMethod.RELATIVE_PS: "Price-to-Sales Multiple",
            ValuationMethod.RELATIVE_EV_EBITDA: "EV/EBITDA Multiple",
            ValuationMethod.RELATIVE_EV_REVENUE: "EV/Revenue Multiple",
            ValuationMethod.ASSET_BOOK_VALUE: "Book Value",
            ValuationMethod.ASSET_NAV: "Net Asset Value (NAV)",
            ValuationMethod.ASSET_LIQUIDATION: "Liquidation Value",
            ValuationMethod.GROWTH_RULE_40: "Rule of 40 (SaaS Valuation)",
            ValuationMethod.GROWTH_EV_ARR: "EV/ARR Multiple",
        }
        return descriptions.get(method, method.value)

    def assess_data_availability(self, stock_info: dict) -> dict[str, bool]:
        """
        Assess which data fields are available from stock info.

        Args:
            stock_info: Stock information dictionary

        Returns:
            Dict mapping data field names to availability
        """
        availability = {}

        # Basic financial metrics
        availability["eps"] = self._has_value(stock_info.get("trailingEps")) or self._has_value(
            stock_info.get("forwardEps")
        )
        availability["book_value_per_share"] = self._has_value(stock_info.get("bookValue"))
        availability["revenue"] = self._has_value(stock_info.get("totalRevenue"))
        availability["ebitda"] = self._has_value(stock_info.get("ebitda"))
        availability["free_cash_flow"] = self._has_value(stock_info.get("freeCashflow"))
        availability["shares_outstanding"] = self._has_value(stock_info.get("sharesOutstanding"))

        # Calculate revenue per share
        revenue = stock_info.get("totalRevenue", 0) or 0
        shares = stock_info.get("sharesOutstanding", 0) or 0
        availability["revenue_per_share"] = revenue > 0 and shares > 0

        # Dividend data
        availability["dividend_per_share"] = self._has_value(stock_info.get("dividendRate"))

        # Balance sheet
        availability["total_assets"] = self._has_value(stock_info.get("totalAssets"))
        availability["total_liabilities"] = self._has_value(stock_info.get("totalDebt"))

        # Growth metrics
        availability["revenue_growth"] = self._has_value(stock_info.get("revenueGrowth"))
        availability["profit_margin"] = self._has_value(stock_info.get("profitMargins"))

        # For SaaS-specific
        availability["arr"] = availability["revenue"]  # Use revenue as proxy
        availability["growth_rate"] = availability["revenue_growth"]

        # NAV specific (usually not available for non-REITs)
        availability["noi"] = False  # Would need specific REIT data
        availability["cap_rate"] = False

        # Peer data will be fetched separately or defaulted
        availability["peer_pe"] = True  # Will use defaults
        availability["peer_pb"] = True
        availability["peer_ps"] = True
        availability["peer_ev_ebitda"] = True
        availability["peer_ev_revenue"] = True

        return availability

    def _has_value(self, value) -> bool:
        """Check if a value is present and valid."""
        if value is None:
            return False
        try:
            float_val = float(value)
            return float_val != 0 and float_val == float_val  # Check for NaN
        except (TypeError, ValueError):
            return False
