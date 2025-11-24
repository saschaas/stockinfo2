"""
Financial Calculator Service

Calculates derived financial metrics like CAGR, margin trends,
ratios, and other analytical computations
"""

import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class FinancialCalculator:
    """Calculate derived financial metrics and trends"""

    @staticmethod
    def calculate_cagr(
        start_value: float,
        end_value: float,
        num_years: float
    ) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate

        Args:
            start_value: Starting value
            end_value: Ending value
            num_years: Number of years between start and end

        Returns:
            CAGR as percentage (e.g., 15.5 for 15.5%)
        """
        if start_value <= 0 or end_value <= 0 or num_years <= 0:
            return None

        try:
            cagr = (pow(end_value / start_value, 1 / num_years) - 1) * 100
            return round(cagr, 2)
        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    @staticmethod
    def calculate_margin_trend(
        margins: List[float],
        min_data_points: int = 3
    ) -> str:
        """
        Determine margin trend from historical data

        Args:
            margins: List of margin values (most recent last)
            min_data_points: Minimum points needed for trend

        Returns:
            "expanding", "stable", or "contracting"
        """
        if len(margins) < min_data_points:
            return "insufficient_data"

        # Calculate simple linear trend
        n = len(margins)
        x_avg = (n - 1) / 2
        y_avg = sum(margins) / n

        numerator = sum((i - x_avg) * (margins[i] - y_avg) for i in range(n))
        denominator = sum((i - x_avg) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Determine trend based on slope
        if slope > 0.5:  # More than 0.5% improvement per period
            return "expanding"
        elif slope < -0.5:  # More than 0.5% decline per period
            return "contracting"
        else:
            return "stable"

    @staticmethod
    def calculate_roe(
        net_income: float,
        shareholders_equity: float
    ) -> Optional[float]:
        """
        Calculate Return on Equity

        Args:
            net_income: Net income
            shareholders_equity: Total shareholders' equity

        Returns:
            ROE as percentage
        """
        if shareholders_equity <= 0:
            return None

        return round((net_income / shareholders_equity) * 100, 2)

    @staticmethod
    def calculate_roa(
        net_income: float,
        total_assets: float
    ) -> Optional[float]:
        """
        Calculate Return on Assets

        Args:
            net_income: Net income
            total_assets: Total assets

        Returns:
            ROA as percentage
        """
        if total_assets <= 0:
            return None

        return round((net_income / total_assets) * 100, 2)

    @staticmethod
    def calculate_roic(
        nopat: float,
        invested_capital: float
    ) -> Optional[float]:
        """
        Calculate Return on Invested Capital

        Args:
            nopat: Net Operating Profit After Tax
            invested_capital: Total invested capital

        Returns:
            ROIC as percentage
        """
        if invested_capital <= 0:
            return None

        return round((nopat / invested_capital) * 100, 2)

    @staticmethod
    def calculate_current_ratio(
        current_assets: float,
        current_liabilities: float
    ) -> Optional[float]:
        """
        Calculate current ratio (liquidity measure)

        Args:
            current_assets: Total current assets
            current_liabilities: Total current liabilities

        Returns:
            Current ratio (e.g., 1.5)
        """
        if current_liabilities <= 0:
            return None

        return round(current_assets / current_liabilities, 2)

    @staticmethod
    def calculate_quick_ratio(
        current_assets: float,
        inventory: float,
        current_liabilities: float
    ) -> Optional[float]:
        """
        Calculate quick ratio (acid test)

        Args:
            current_assets: Total current assets
            inventory: Inventory value
            current_liabilities: Total current liabilities

        Returns:
            Quick ratio
        """
        if current_liabilities <= 0:
            return None

        quick_assets = current_assets - inventory
        return round(quick_assets / current_liabilities, 2)

    @staticmethod
    def calculate_debt_to_equity(
        total_debt: float,
        shareholders_equity: float
    ) -> Optional[float]:
        """
        Calculate debt to equity ratio

        Args:
            total_debt: Total debt
            shareholders_equity: Total equity

        Returns:
            Debt/Equity ratio
        """
        if shareholders_equity <= 0:
            return None

        return round(total_debt / shareholders_equity, 2)

    @staticmethod
    def calculate_interest_coverage(
        ebit: float,
        interest_expense: float
    ) -> Optional[float]:
        """
        Calculate interest coverage ratio

        Args:
            ebit: Earnings Before Interest and Tax
            interest_expense: Interest expense

        Returns:
            Interest coverage ratio (times)
        """
        if interest_expense <= 0:
            return None

        return round(ebit / interest_expense, 2)

    @staticmethod
    def calculate_peg_ratio(
        pe_ratio: float,
        earnings_growth_rate: float
    ) -> Optional[float]:
        """
        Calculate PEG ratio (Price/Earnings to Growth)

        Args:
            pe_ratio: P/E ratio
            earnings_growth_rate: Earnings growth rate (percentage)

        Returns:
            PEG ratio
        """
        if earnings_growth_rate <= 0 or pe_ratio <= 0:
            return None

        return round(pe_ratio / earnings_growth_rate, 2)

    @staticmethod
    def calculate_fcf_yield(
        free_cash_flow: float,
        market_cap: float
    ) -> Optional[float]:
        """
        Calculate Free Cash Flow yield

        Args:
            free_cash_flow: Free cash flow
            market_cap: Market capitalization

        Returns:
            FCF yield as percentage
        """
        if market_cap <= 0:
            return None

        return round((free_cash_flow / market_cap) * 100, 2)

    @staticmethod
    def calculate_cash_runway_months(
        cash_balance: float,
        monthly_burn_rate: float
    ) -> Optional[float]:
        """
        Calculate cash runway in months

        Args:
            cash_balance: Current cash balance
            monthly_burn_rate: Monthly cash burn (negative for burn)

        Returns:
            Months of runway
        """
        if monthly_burn_rate >= 0:  # No burn or positive cash flow
            return None

        return round(cash_balance / abs(monthly_burn_rate), 1)

    @staticmethod
    def assess_balance_sheet_strength(
        debt_to_equity: float,
        current_ratio: float,
        interest_coverage: Optional[float] = None
    ) -> Tuple[str, int]:
        """
        Assess overall balance sheet strength

        Args:
            debt_to_equity: Debt/Equity ratio
            current_ratio: Current ratio
            interest_coverage: Interest coverage ratio (optional)

        Returns:
            Tuple of (assessment_text, score_0_to_10)
        """
        score = 5  # Start at neutral

        # Debt assessment
        if debt_to_equity < 0.3:
            score += 2
            debt_strength = "very low leverage"
        elif debt_to_equity < 0.6:
            score += 1
            debt_strength = "low leverage"
        elif debt_to_equity < 1.0:
            debt_strength = "moderate leverage"
        elif debt_to_equity < 1.5:
            score -= 1
            debt_strength = "high leverage"
        else:
            score -= 2
            debt_strength = "very high leverage"

        # Liquidity assessment
        if current_ratio > 2.0:
            score += 1
            liquidity = "excellent liquidity"
        elif current_ratio > 1.5:
            score += 0.5
            liquidity = "good liquidity"
        elif current_ratio > 1.0:
            liquidity = "adequate liquidity"
        elif current_ratio > 0.8:
            score -= 1
            liquidity = "tight liquidity"
        else:
            score -= 2
            liquidity = "poor liquidity"

        # Interest coverage (if available)
        if interest_coverage is not None:
            if interest_coverage > 10:
                score += 1
            elif interest_coverage < 2:
                score -= 1

        score = max(0, min(10, score))

        assessment = f"Balance sheet shows {debt_strength} and {liquidity}"

        return assessment, int(score)

    @staticmethod
    def calculate_graham_number(
        eps: float,
        book_value_per_share: float
    ) -> Optional[float]:
        """
        Calculate Benjamin Graham's intrinsic value estimate

        Args:
            eps: Earnings per share
            book_value_per_share: Book value per share

        Returns:
            Graham number (estimated fair value)
        """
        if eps <= 0 or book_value_per_share <= 0:
            return None

        try:
            graham = pow(22.5 * eps * book_value_per_share, 0.5)
            return round(graham, 2)
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def calculate_altman_z_score(
        working_capital: float,
        total_assets: float,
        retained_earnings: float,
        ebit: float,
        market_cap: float,
        total_liabilities: float,
        sales: float
    ) -> Optional[Tuple[float, str]]:
        """
        Calculate Altman Z-Score (bankruptcy prediction)

        Args:
            working_capital: Working capital
            total_assets: Total assets
            retained_earnings: Retained earnings
            ebit: EBIT
            market_cap: Market capitalization
            total_liabilities: Total liabilities
            sales: Revenue/sales

        Returns:
            Tuple of (z_score, risk_zone)
            risk_zone: "safe", "grey", or "distress"
        """
        if total_assets <= 0:
            return None

        try:
            x1 = working_capital / total_assets
            x2 = retained_earnings / total_assets
            x3 = ebit / total_assets
            x4 = market_cap / total_liabilities if total_liabilities > 0 else 0
            x5 = sales / total_assets

            z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
            z_score = round(z_score, 2)

            if z_score > 2.99:
                zone = "safe"
            elif z_score > 1.81:
                zone = "grey"
            else:
                zone = "distress"

            return z_score, zone

        except (ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def calculate_magic_formula_rank(
        earnings_yield: float,
        roic: float
    ) -> Optional[float]:
        """
        Calculate Joel Greenblatt's Magic Formula composite score

        Args:
            earnings_yield: Earnings yield (EBIT/EV) as percentage
            roic: Return on Invested Capital as percentage

        Returns:
            Composite score (higher is better)
        """
        if earnings_yield <= 0 or roic <= 0:
            return None

        # Simple average of normalized percentile scores
        # In production, would rank against universe
        score = (earnings_yield + roic) / 2
        return round(score, 2)


# Singleton instance
_calculator: Optional[FinancialCalculator] = None


def get_financial_calculator() -> FinancialCalculator:
    """Get or create financial calculator instance"""
    global _calculator
    if _calculator is None:
        _calculator = FinancialCalculator()
    return _calculator
