"""
Asset-Based Valuation Methods.

Implements:
- Book Value
- Net Asset Value (NAV) for REITs
- Liquidation Value
"""

import structlog

from ..models import DataQuality, MethodResult, ValuationMethod

logger = structlog.get_logger(__name__)


class AssetBasedValuation:
    """
    Asset-based valuation methods.

    Best for:
    - Financial institutions (banks, insurance)
    - REITs
    - Holding companies
    - Distressed companies (liquidation)
    """

    # Typical recovery rates for liquidation
    LIQUIDATION_RECOVERY_RATES = {
        "cash": 1.0,
        "marketable_securities": 0.95,
        "accounts_receivable": 0.80,
        "inventory": 0.60,
        "property_plant_equipment": 0.50,
        "intangibles": 0.10,
        "goodwill": 0.0,
    }

    def book_value(
        self,
        total_assets: float,
        total_liabilities: float,
        shares_outstanding: int,
        preferred_stock: float = 0,
    ) -> MethodResult:
        """
        Book Value valuation.

        Book Value per Share = (Total Assets - Total Liabilities - Preferred Stock) / Shares

        Args:
            total_assets: Total assets from balance sheet
            total_liabilities: Total liabilities from balance sheet
            shares_outstanding: Common shares outstanding
            preferred_stock: Value of preferred stock (if any)

        Returns:
            MethodResult with book value per share
        """
        warnings = []

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.ASSET_BOOK_VALUE,
                "Invalid shares outstanding",
            )

        # Calculate book value of equity
        book_value_equity = total_assets - total_liabilities - preferred_stock

        if book_value_equity < 0:
            warnings.append("Negative book value indicates liabilities exceed assets")

        book_value_per_share = book_value_equity / shares_outstanding

        # Calculate range (book value is usually a floor)
        low_estimate = book_value_per_share * 0.90
        high_estimate = book_value_per_share * 1.50  # Could trade at premium

        confidence = 70.0
        if book_value_equity < 0:
            confidence = 40.0

        logger.debug(
            "Book value calculation complete",
            book_value_per_share=book_value_per_share,
            book_value_equity=book_value_equity,
        )

        return MethodResult(
            method=ValuationMethod.ASSET_BOOK_VALUE,
            fair_value=book_value_per_share,
            confidence=confidence,
            data_quality=DataQuality.HIGH,
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            assumptions={
                "total_assets": round(total_assets, 0),
                "total_liabilities": round(total_liabilities, 0),
                "preferred_stock": round(preferred_stock, 0),
            },
            calculation_details={
                "book_value_equity": book_value_equity,
                "shares_outstanding": shares_outstanding,
            },
            warnings=warnings,
        )

    def nav_valuation(
        self,
        net_operating_income: float,
        cap_rate: float,
        other_assets: float,
        total_debt: float,
        shares_outstanding: int,
    ) -> MethodResult:
        """
        Net Asset Value (NAV) valuation for REITs.

        Property Value = NOI / Cap Rate
        NAV = Property Value + Other Assets - Debt
        NAV per Share = NAV / Shares

        Args:
            net_operating_income: NOI from properties
            cap_rate: Capitalization rate for property valuation
            other_assets: Cash and other non-property assets
            total_debt: Total debt
            shares_outstanding: Shares outstanding

        Returns:
            MethodResult with NAV per share
        """
        warnings = []

        if net_operating_income <= 0:
            return self._create_error_result(
                ValuationMethod.ASSET_NAV,
                "NOI must be positive for NAV valuation",
            )

        if cap_rate <= 0 or cap_rate > 0.15:
            warnings.append(f"Cap rate ({cap_rate:.2%}) may be unrealistic")
            cap_rate = max(0.04, min(0.12, cap_rate))

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.ASSET_NAV,
                "Invalid shares outstanding",
            )

        # Calculate property value
        property_value = net_operating_income / cap_rate

        # Calculate NAV
        nav = property_value + other_assets - total_debt
        nav_per_share = nav / shares_outstanding

        # Calculate range with different cap rates
        low_cap = cap_rate + 0.01  # Higher cap rate = lower value
        high_cap = max(0.03, cap_rate - 0.01)  # Lower cap rate = higher value

        low_estimate = ((net_operating_income / low_cap) + other_assets - total_debt) / shares_outstanding
        high_estimate = ((net_operating_income / high_cap) + other_assets - total_debt) / shares_outstanding

        confidence = 70.0

        logger.debug(
            "NAV calculation complete",
            nav_per_share=nav_per_share,
            property_value=property_value,
        )

        return MethodResult(
            method=ValuationMethod.ASSET_NAV,
            fair_value=max(0, nav_per_share),
            confidence=confidence,
            data_quality=DataQuality.MEDIUM,
            low_estimate=max(0, low_estimate),
            high_estimate=high_estimate,
            assumptions={
                "net_operating_income": round(net_operating_income, 0),
                "cap_rate": round(cap_rate, 4),
                "other_assets": round(other_assets, 0),
                "total_debt": round(total_debt, 0),
            },
            calculation_details={
                "property_value": property_value,
                "nav": nav,
                "shares_outstanding": shares_outstanding,
            },
            warnings=warnings,
        )

    def liquidation_value(
        self,
        cash: float,
        receivables: float,
        inventory: float,
        property_plant_equipment: float,
        other_assets: float,
        total_liabilities: float,
        shares_outstanding: int,
        orderly: bool = True,
    ) -> MethodResult:
        """
        Liquidation Value calculation.

        Applies recovery rates to assets and subtracts liabilities.

        Args:
            cash: Cash and equivalents
            receivables: Accounts receivable
            inventory: Inventory
            property_plant_equipment: PP&E
            other_assets: Other tangible assets
            total_liabilities: Total liabilities
            shares_outstanding: Shares outstanding
            orderly: True for orderly liquidation, False for forced sale

        Returns:
            MethodResult with liquidation value per share
        """
        warnings = []

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.ASSET_LIQUIDATION,
                "Invalid shares outstanding",
            )

        # Apply recovery rates
        if orderly:
            recovery_cash = cash * 1.0
            recovery_receivables = receivables * 0.80
            recovery_inventory = inventory * 0.60
            recovery_ppe = property_plant_equipment * 0.50
            recovery_other = other_assets * 0.30
        else:
            # Forced sale - lower recovery
            recovery_cash = cash * 1.0
            recovery_receivables = receivables * 0.60
            recovery_inventory = inventory * 0.40
            recovery_ppe = property_plant_equipment * 0.30
            recovery_other = other_assets * 0.15

        total_recovery = (
            recovery_cash
            + recovery_receivables
            + recovery_inventory
            + recovery_ppe
            + recovery_other
        )

        # Subtract liabilities (plus estimated liquidation costs ~5%)
        liquidation_costs = total_recovery * 0.05
        liquidation_value = total_recovery - total_liabilities - liquidation_costs

        liquidation_per_share = liquidation_value / shares_outstanding

        if liquidation_per_share < 0:
            warnings.append("Negative liquidation value - liabilities exceed recoverable assets")

        # Range based on orderly vs forced
        if orderly:
            low_estimate = liquidation_per_share * 0.70  # Forced sale scenario
            high_estimate = liquidation_per_share * 1.10
        else:
            low_estimate = liquidation_per_share * 0.80
            high_estimate = liquidation_per_share * 1.30  # Orderly sale

        confidence = 60.0

        return MethodResult(
            method=ValuationMethod.ASSET_LIQUIDATION,
            fair_value=liquidation_per_share,
            confidence=confidence,
            data_quality=DataQuality.LOW,  # Liquidation estimates are inherently uncertain
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            assumptions={
                "liquidation_type": "orderly" if orderly else "forced",
                "recovery_rates": {
                    "cash": 1.0,
                    "receivables": 0.80 if orderly else 0.60,
                    "inventory": 0.60 if orderly else 0.40,
                    "ppe": 0.50 if orderly else 0.30,
                    "other": 0.30 if orderly else 0.15,
                },
            },
            calculation_details={
                "total_recovery": total_recovery,
                "liquidation_costs": liquidation_costs,
                "total_liabilities": total_liabilities,
                "liquidation_value": liquidation_value,
            },
            warnings=warnings,
        )

    def tangible_book_value(
        self,
        total_assets: float,
        total_liabilities: float,
        goodwill: float,
        intangibles: float,
        shares_outstanding: int,
    ) -> MethodResult:
        """
        Tangible Book Value (excludes goodwill and intangibles).

        More conservative than regular book value.

        Args:
            total_assets: Total assets
            total_liabilities: Total liabilities
            goodwill: Goodwill on balance sheet
            intangibles: Other intangible assets
            shares_outstanding: Shares outstanding

        Returns:
            MethodResult with tangible book value per share
        """
        warnings = []

        if shares_outstanding <= 0:
            return self._create_error_result(
                ValuationMethod.ASSET_BOOK_VALUE,
                "Invalid shares outstanding",
            )

        tangible_assets = total_assets - goodwill - intangibles
        tangible_equity = tangible_assets - total_liabilities
        tbv_per_share = tangible_equity / shares_outstanding

        if tangible_equity < 0:
            warnings.append("Negative tangible book value")

        # Book value is typically a floor
        low_estimate = tbv_per_share * 0.85
        high_estimate = tbv_per_share * 1.50

        confidence = 65.0
        if tangible_equity < 0:
            confidence = 35.0

        return MethodResult(
            method=ValuationMethod.ASSET_BOOK_VALUE,
            fair_value=tbv_per_share,
            confidence=confidence,
            data_quality=DataQuality.HIGH,
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            assumptions={
                "total_assets": round(total_assets, 0),
                "goodwill": round(goodwill, 0),
                "intangibles": round(intangibles, 0),
                "total_liabilities": round(total_liabilities, 0),
            },
            calculation_details={
                "tangible_assets": tangible_assets,
                "tangible_equity": tangible_equity,
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
