"""
Data models for the Valuation Engine.

Contains enums, dataclasses, and type definitions used throughout
the valuation module.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CompanyType(Enum):
    """Company classification for valuation method selection."""

    DIVIDEND_PAYER = "dividend_payer"  # Mature, stable dividend history (>2% yield)
    HIGH_GROWTH = "high_growth"  # >20% revenue growth, often unprofitable
    MATURE_GROWTH = "mature_growth"  # 5-20% growth, profitable
    VALUE = "value"  # Low growth, undervalued fundamentals
    REIT = "reit"  # Real Estate Investment Trust
    BANK = "bank"  # Financial institution
    INSURANCE = "insurance"  # Insurance company
    UTILITY = "utility"  # Regulated utility
    DISTRESSED = "distressed"  # Negative equity, Z-score < 1.81
    CYCLICAL = "cyclical"  # Highly cyclical industry
    COMMODITY = "commodity"  # Commodity producer


class ValuationMethod(Enum):
    """Available valuation methods."""

    # DCF Methods
    DCF_FCFF = "dcf_fcff"  # Free Cash Flow to Firm
    DCF_FCFE = "dcf_fcfe"  # Free Cash Flow to Equity

    # Dividend Discount Models
    DDM_GORDON = "ddm_gordon"  # Gordon Growth Model
    DDM_TWO_STAGE = "ddm_two_stage"  # Two-Stage DDM
    DDM_H_MODEL = "ddm_h_model"  # H-Model (gradual growth decline)

    # Relative Valuation
    RELATIVE_PE = "relative_pe"  # P/E multiple
    RELATIVE_PB = "relative_pb"  # P/B multiple
    RELATIVE_PS = "relative_ps"  # P/S multiple
    RELATIVE_EV_EBITDA = "relative_ev_ebitda"
    RELATIVE_EV_REVENUE = "relative_ev_revenue"
    RELATIVE_EV_FCF = "relative_ev_fcf"

    # Asset-Based
    ASSET_BOOK_VALUE = "asset_book_value"
    ASSET_NAV = "asset_nav"  # Net Asset Value (REITs)
    ASSET_LIQUIDATION = "asset_liquidation"

    # Growth Company Methods
    GROWTH_RULE_40 = "growth_rule_40"  # Revenue growth + margin
    GROWTH_EV_ARR = "growth_ev_arr"  # EV/Annual Recurring Revenue


class DataQuality(Enum):
    """Data quality indicators."""

    HIGH = "high"  # All required data available
    MEDIUM = "medium"  # Some data estimated or missing
    LOW = "low"  # Significant data gaps
    INSUFFICIENT = "insufficient"  # Cannot perform valuation


@dataclass
class MarketInputs:
    """Market-level inputs for valuation."""

    risk_free_rate: float = 0.04  # 10-year Treasury yield (default 4%)
    equity_risk_premium: float = 0.055  # Historical ERP ~5.5%
    sp500_return: float = 0.10  # Long-term market return
    sector_premium: float = 0.0  # Industry-specific premium

    # Source tracking
    rf_source: str = "hardcoded"  # "yahoo_finance", "hardcoded"
    rf_as_of_date: datetime | None = None
    data_quality: DataQuality = DataQuality.MEDIUM


@dataclass
class CAPMInputs:
    """CAPM model inputs for cost of equity calculation."""

    beta: float = 1.0
    risk_free_rate: float = 0.04
    equity_risk_premium: float = 0.055
    size_premium: float = 0.0  # Small-cap premium
    company_specific_risk: float = 0.0  # Additional risk factor

    @property
    def cost_of_equity(self) -> float:
        """Calculate cost of equity: Rf + Beta * ERP + premiums."""
        return (
            self.risk_free_rate
            + self.beta * self.equity_risk_premium
            + self.size_premium
            + self.company_specific_risk
        )


@dataclass
class WACCInputs:
    """WACC calculation inputs."""

    cost_of_equity: float = 0.10
    cost_of_debt: float = 0.05
    tax_rate: float = 0.21  # US corporate tax rate
    market_cap: float = 0.0
    total_debt: float = 0.0

    @property
    def total_capital(self) -> float:
        """Total capital (E + D)."""
        return self.market_cap + self.total_debt

    @property
    def weight_equity(self) -> float:
        """Weight of equity in capital structure."""
        if self.total_capital <= 0:
            return 1.0
        return self.market_cap / self.total_capital

    @property
    def weight_debt(self) -> float:
        """Weight of debt in capital structure."""
        if self.total_capital <= 0:
            return 0.0
        return self.total_debt / self.total_capital

    @property
    def wacc(self) -> float:
        """Calculate Weighted Average Cost of Capital."""
        after_tax_cost_of_debt = self.cost_of_debt * (1 - self.tax_rate)
        return self.weight_equity * self.cost_of_equity + self.weight_debt * after_tax_cost_of_debt


@dataclass
class MethodResult:
    """Result from a single valuation method."""

    method: ValuationMethod
    fair_value: float  # Per-share fair value
    confidence: float  # 0-100 confidence score
    data_quality: DataQuality

    # Range estimates
    low_estimate: float = 0.0
    high_estimate: float = 0.0

    # Method-specific details
    assumptions: dict[str, Any] = field(default_factory=dict)
    calculation_details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # For weighting in composite
    weight: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "method": self.method.value,
            "fair_value": round(self.fair_value, 2),
            "confidence": round(self.confidence, 1),
            "data_quality": self.data_quality.value,
            "low_estimate": round(self.low_estimate, 2),
            "high_estimate": round(self.high_estimate, 2),
            "assumptions": self.assumptions,
            "calculation_details": {
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.calculation_details.items()
            },
            "warnings": self.warnings,
            "weight": round(self.weight, 3),
        }


@dataclass
class ValuationResult:
    """Complete valuation output."""

    ticker: str
    valuation_date: datetime = field(default_factory=datetime.now)

    # Company classification
    company_type: CompanyType = CompanyType.MATURE_GROWTH
    classification_confidence: float = 0.0
    classification_reasons: list[str] = field(default_factory=list)

    # Current price for comparison
    current_price: float = 0.0
    shares_outstanding: int = 0

    # Composite fair value
    fair_value: float = 0.0  # Weighted average
    fair_value_low: float = 0.0  # Conservative estimate
    fair_value_high: float = 0.0  # Optimistic estimate

    # Valuation verdict
    upside_potential: float = 0.0  # (fair_value - current) / current * 100
    valuation_status: str = ""  # "undervalued", "fairly_valued", "overvalued"
    margin_of_safety: float = 0.0  # How much below fair value

    # Individual method results
    method_results: list[MethodResult] = field(default_factory=list)
    primary_method: ValuationMethod = ValuationMethod.DCF_FCFF

    # Data quality
    overall_data_quality: DataQuality = DataQuality.MEDIUM
    missing_data: list[str] = field(default_factory=list)
    data_warnings: list[str] = field(default_factory=list)

    # Confidence
    overall_confidence: float = 0.0  # 0-100

    # Discount rate inputs
    market_inputs: MarketInputs = field(default_factory=MarketInputs)
    wacc: float = 0.0
    cost_of_equity: float = 0.0

    # Data sources
    data_sources: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "valuation_date": self.valuation_date.isoformat(),
            "company_type": self.company_type.value,
            "classification_confidence": round(self.classification_confidence, 2),
            "classification_reasons": self.classification_reasons,
            "current_price": round(self.current_price, 2),
            "shares_outstanding": self.shares_outstanding,
            "fair_value": round(self.fair_value, 2),
            "fair_value_low": round(self.fair_value_low, 2),
            "fair_value_high": round(self.fair_value_high, 2),
            "upside_potential": round(self.upside_potential, 2),
            "valuation_status": self.valuation_status,
            "margin_of_safety": round(self.margin_of_safety, 2),
            "method_results": [mr.to_dict() for mr in self.method_results],
            "primary_method": self.primary_method.value,
            "overall_data_quality": self.overall_data_quality.value,
            "missing_data": self.missing_data,
            "data_warnings": self.data_warnings,
            "overall_confidence": round(self.overall_confidence, 1),
            "wacc": round(self.wacc, 4),
            "cost_of_equity": round(self.cost_of_equity, 4),
            "market_inputs": {
                "risk_free_rate": round(self.market_inputs.risk_free_rate, 4),
                "equity_risk_premium": round(self.market_inputs.equity_risk_premium, 4),
                "rf_source": self.market_inputs.rf_source,
            },
            "data_sources": self.data_sources,
        }


@dataclass
class SensitivityAnalysis:
    """Sensitivity analysis for fair value."""

    base_fair_value: float
    wacc_sensitivity: dict[float, float] = field(default_factory=dict)  # WACC -> Fair Value
    growth_sensitivity: dict[float, float] = field(default_factory=dict)  # Growth -> Fair Value
    matrix: list[list[float]] = field(default_factory=list)  # WACC x Growth matrix

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "base_fair_value": round(self.base_fair_value, 2),
            "wacc_sensitivity": {
                str(k): round(v, 2) for k, v in self.wacc_sensitivity.items()
            },
            "growth_sensitivity": {
                str(k): round(v, 2) for k, v in self.growth_sensitivity.items()
            },
            "matrix": [[round(v, 2) for v in row] for row in self.matrix],
        }
