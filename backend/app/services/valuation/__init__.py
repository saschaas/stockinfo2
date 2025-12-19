"""
Valuation Engine Module

Provides comprehensive company valuation using multiple methodologies:
- DCF (Discounted Cash Flow) - FCFF and FCFE
- DDM (Dividend Discount Models) - Gordon Growth, Two-Stage, H-Model
- Relative Valuation - P/E, EV/EBITDA, P/B, EV/Revenue
- Asset-Based - Book Value, NAV, Liquidation Value
- Growth Company Methods - Rule of 40, EV/ARR

The engine automatically classifies companies and applies appropriate methods.
"""

from .valuation_engine import ValuationEngine
from .company_classifier import CompanyClassifier
from .method_selector import MethodSelector
from .models import (
    CompanyType,
    ValuationMethod,
    DataQuality,
    ValuationResult,
    MethodResult,
    MarketInputs,
    CAPMInputs,
    WACCInputs,
)

__all__ = [
    "ValuationEngine",
    "CompanyClassifier",
    "MethodSelector",
    "CompanyType",
    "ValuationMethod",
    "DataQuality",
    "ValuationResult",
    "MethodResult",
    "MarketInputs",
    "CAPMInputs",
    "WACCInputs",
]
