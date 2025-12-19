"""
Company Classifier for Valuation Method Selection.

Classifies companies by type to determine the most appropriate
valuation methodologies based on:
- Sector/Industry (REIT, Bank, Utility detection)
- Financial metrics (dividend yield, growth rates, profitability)
- Balance sheet health (Altman Z-Score for distress)
"""

import structlog

from .models import CompanyType, DataQuality

logger = structlog.get_logger(__name__)


class CompanyClassifier:
    """
    Classifies companies by type to determine appropriate valuation methods.
    """

    # Sector/Industry keywords for classification
    REIT_KEYWORDS = ["reit", "real estate investment trust", "equity reit", "mortgage reit"]
    BANK_KEYWORDS = [
        "bank",
        "banking",
        "savings institution",
        "commercial bank",
        "regional bank",
    ]
    INSURANCE_KEYWORDS = ["insurance", "reinsurance", "life insurance", "property insurance"]
    UTILITY_KEYWORDS = [
        "utility",
        "utilities",
        "electric utility",
        "gas utility",
        "water utility",
        "regulated electric",
    ]
    CYCLICAL_KEYWORDS = [
        "auto",
        "automotive",
        "steel",
        "construction",
        "building materials",
        "homebuilding",
    ]
    COMMODITY_KEYWORDS = ["oil", "gas", "mining", "metals", "agricultural", "energy"]

    def classify(
        self,
        stock_info: dict,
        financial_data: dict | None = None,
    ) -> tuple[CompanyType, float, list[str]]:
        """
        Classify a company and return (type, confidence, reasons).

        Args:
            stock_info: Stock information from Yahoo Finance
            financial_data: Additional financial statements (optional)

        Returns:
            Tuple of (CompanyType, confidence 0-1, list of reasons)
        """
        sector = str(stock_info.get("sector", "")).lower()
        industry = str(stock_info.get("industry", "")).lower()
        reasons = []

        logger.debug(
            "Classifying company",
            sector=sector,
            industry=industry,
        )

        # Step 1: Check for special sectors (REIT, Bank, Utility, Insurance)
        if self._is_reit(sector, industry, stock_info):
            reasons.append("Classified as REIT based on sector/industry")
            return CompanyType.REIT, 0.95, reasons

        if self._is_bank(sector, industry):
            reasons.append("Classified as Bank based on Financial Services sector")
            return CompanyType.BANK, 0.95, reasons

        if self._is_insurance(sector, industry):
            reasons.append("Classified as Insurance based on sector/industry")
            return CompanyType.INSURANCE, 0.90, reasons

        if self._is_utility(sector, industry):
            reasons.append("Classified as Utility based on Utilities sector")
            return CompanyType.UTILITY, 0.90, reasons

        # Step 2: Check for distress (Altman Z-Score)
        z_score = self._calculate_z_score(stock_info, financial_data or {})
        if z_score is not None and z_score < 1.81:
            reasons.append(f"Altman Z-Score of {z_score:.2f} indicates distress (< 1.81)")
            return CompanyType.DISTRESSED, 0.85, reasons

        # Step 3: Check for cyclical/commodity companies
        if self._is_cyclical(sector, industry):
            reasons.append("Classified as Cyclical based on industry characteristics")
            return CompanyType.CYCLICAL, 0.75, reasons

        if self._is_commodity(sector, industry):
            reasons.append("Classified as Commodity based on industry characteristics")
            return CompanyType.COMMODITY, 0.75, reasons

        # Step 4: Classify by growth/dividend characteristics
        revenue_growth = self._safe_float(stock_info.get("revenueGrowth", 0)) * 100
        dividend_yield = self._safe_float(stock_info.get("dividendYield", 0)) * 100
        profit_margin = self._safe_float(stock_info.get("profitMargins", 0)) * 100
        payout_ratio = self._safe_float(stock_info.get("payoutRatio", 0)) * 100

        # High Growth: >20% revenue growth
        if revenue_growth > 20:
            if profit_margin < 0:
                reasons.append(
                    f"High revenue growth ({revenue_growth:.1f}%) but unprofitable "
                    f"(margin: {profit_margin:.1f}%)"
                )
                return CompanyType.HIGH_GROWTH, 0.85, reasons
            else:
                reasons.append(
                    f"High revenue growth ({revenue_growth:.1f}%) and profitable "
                    f"(margin: {profit_margin:.1f}%)"
                )
                return CompanyType.HIGH_GROWTH, 0.80, reasons

        # Dividend Payer: Consistent dividend >2% with sustainable payout
        if dividend_yield > 2.0:
            if 30 <= payout_ratio < 100:
                reasons.append(
                    f"Dividend yield {dividend_yield:.1f}% with sustainable payout "
                    f"ratio {payout_ratio:.1f}%"
                )
                return CompanyType.DIVIDEND_PAYER, 0.85, reasons
            elif payout_ratio > 0:
                reasons.append(
                    f"Dividend yield {dividend_yield:.1f}% (payout ratio: {payout_ratio:.1f}%)"
                )
                return CompanyType.DIVIDEND_PAYER, 0.70, reasons

        # Mature Growth: 5-20% growth, profitable
        if 5 < revenue_growth <= 20 and profit_margin > 5:
            reasons.append(
                f"Moderate revenue growth ({revenue_growth:.1f}%) with good margins "
                f"({profit_margin:.1f}%)"
            )
            return CompanyType.MATURE_GROWTH, 0.75, reasons

        # Value: Low growth but undervalued metrics
        pe_ratio = self._safe_float(stock_info.get("trailingPE", 0))
        pb_ratio = self._safe_float(stock_info.get("priceToBook", 0))
        if 0 < pe_ratio < 15 and 0 < pb_ratio < 1.5:
            reasons.append(f"Value characteristics: Low P/E ({pe_ratio:.1f}) and P/B ({pb_ratio:.1f})")
            return CompanyType.VALUE, 0.70, reasons

        # Check for low growth value
        if revenue_growth < 5 and 0 < pe_ratio < 18 and profit_margin > 0:
            reasons.append(
                f"Low growth ({revenue_growth:.1f}%) with moderate valuation (P/E: {pe_ratio:.1f})"
            )
            return CompanyType.VALUE, 0.65, reasons

        # Default to Mature Growth
        reasons.append("Default classification as mature company based on available metrics")
        return CompanyType.MATURE_GROWTH, 0.50, reasons

    def _is_reit(self, sector: str, industry: str, stock_info: dict) -> bool:
        """Check if company is a REIT."""
        combined = f"{sector} {industry}"
        if any(keyword in combined for keyword in self.REIT_KEYWORDS):
            return True
        # Also check quote type
        quote_type = str(stock_info.get("quoteType", "")).lower()
        return quote_type == "reit"

    def _is_bank(self, sector: str, industry: str) -> bool:
        """Check if company is a bank."""
        if sector == "financial services":
            return any(keyword in industry for keyword in self.BANK_KEYWORDS)
        return any(keyword in f"{sector} {industry}" for keyword in self.BANK_KEYWORDS)

    def _is_insurance(self, sector: str, industry: str) -> bool:
        """Check if company is an insurance company."""
        return any(keyword in f"{sector} {industry}" for keyword in self.INSURANCE_KEYWORDS)

    def _is_utility(self, sector: str, industry: str) -> bool:
        """Check if company is a utility."""
        if sector == "utilities":
            return True
        return any(keyword in f"{sector} {industry}" for keyword in self.UTILITY_KEYWORDS)

    def _is_cyclical(self, sector: str, industry: str) -> bool:
        """Check if company is in a cyclical industry."""
        return any(keyword in f"{sector} {industry}" for keyword in self.CYCLICAL_KEYWORDS)

    def _is_commodity(self, sector: str, industry: str) -> bool:
        """Check if company is a commodity producer."""
        if sector in ["energy", "basic materials"]:
            return True
        return any(keyword in f"{sector} {industry}" for keyword in self.COMMODITY_KEYWORDS)

    def _calculate_z_score(self, stock_info: dict, financial_data: dict) -> float | None:
        """
        Calculate Altman Z-Score for bankruptcy risk.

        Z-Score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
        Where:
        A = Working Capital / Total Assets
        B = Retained Earnings / Total Assets
        C = EBIT / Total Assets
        D = Market Value of Equity / Total Liabilities
        E = Sales / Total Assets

        Zones:
        < 1.81: Distress zone
        1.81-2.99: Grey zone
        > 2.99: Safe zone
        """
        try:
            total_assets = self._safe_float(stock_info.get("totalAssets", 0))
            total_liabilities = self._safe_float(stock_info.get("totalDebt", 0))
            market_cap = self._safe_float(stock_info.get("marketCap", 0))
            revenue = self._safe_float(stock_info.get("totalRevenue", 0))

            # Get from financial data if available
            current_assets = self._safe_float(
                financial_data.get("totalCurrentAssets", stock_info.get("totalCurrentAssets", 0))
            )
            current_liabilities = self._safe_float(
                financial_data.get(
                    "totalCurrentLiabilities", stock_info.get("totalCurrentLiabilities", 0)
                )
            )
            retained_earnings = self._safe_float(financial_data.get("retainedEarnings", 0))
            ebit = self._safe_float(stock_info.get("ebitda", 0))

            if total_assets <= 0:
                return None

            # Calculate components
            working_capital = current_assets - current_liabilities
            a = working_capital / total_assets if total_assets > 0 else 0
            b = retained_earnings / total_assets if total_assets > 0 else 0
            c = ebit / total_assets if total_assets > 0 else 0
            d = market_cap / total_liabilities if total_liabilities > 0 else 2.0
            e = revenue / total_assets if total_assets > 0 else 0

            z_score = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

            logger.debug(
                "Calculated Z-Score",
                z_score=z_score,
                components={"A": a, "B": b, "C": c, "D": d, "E": e},
            )

            return z_score

        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.debug("Could not calculate Z-Score", error=str(e))
            return None

    def _safe_float(self, value: any) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            result = float(value)
            return result if not (result != result) else 0.0  # Check for NaN
        except (TypeError, ValueError):
            return 0.0

    def get_data_quality_for_classification(self, stock_info: dict) -> DataQuality:
        """Assess data quality for classification."""
        required_fields = ["sector", "industry", "revenueGrowth", "dividendYield", "profitMargins"]
        available = sum(1 for f in required_fields if stock_info.get(f) is not None)

        if available >= 4:
            return DataQuality.HIGH
        elif available >= 2:
            return DataQuality.MEDIUM
        elif available >= 1:
            return DataQuality.LOW
        return DataQuality.INSUFFICIENT
