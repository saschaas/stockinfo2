"""
Valuation Engine - Main Orchestrator.

Coordinates company classification, method selection, and valuation
calculation to produce comprehensive fair value estimates.
"""

from datetime import datetime

import structlog

from .company_classifier import CompanyClassifier
from .inputs.market_data import MarketDataService
from .inputs.peer_multiples import PeerMultiplesService
from .method_selector import MethodSelector
from .methods.asset_based import AssetBasedValuation
from .methods.dcf import DCFValuation
from .methods.dividend_discount import DividendDiscountValuation
from .methods.growth_company import GrowthCompanyValuation
from .methods.relative import RelativeValuation
from .models import (
    CompanyType,
    DataQuality,
    MethodResult,
    ValuationMethod,
    ValuationResult,
)
from .utils.wacc_calculator import WACCCalculator

logger = structlog.get_logger(__name__)


class ValuationEngine:
    """
    Main orchestrator for company valuation.

    Coordinates:
    1. Data gathering from multiple sources
    2. Company classification
    3. Method selection and execution
    4. Result aggregation and confidence scoring
    """

    def __init__(
        self,
        projection_years: int = 5,
        terminal_growth: float = 0.025,
    ):
        """
        Initialize the valuation engine.

        Args:
            projection_years: Years to project for DCF
            terminal_growth: Long-term growth rate for terminal value
        """
        self.classifier = CompanyClassifier()
        self.method_selector = MethodSelector()
        self.market_data = MarketDataService()
        self.peer_multiples = PeerMultiplesService()

        # Initialize valuation methods
        self.dcf = DCFValuation(projection_years, terminal_growth)
        self.ddm = DividendDiscountValuation()
        self.relative = RelativeValuation()
        self.asset_based = AssetBasedValuation()
        self.growth = GrowthCompanyValuation()

        self.projection_years = projection_years
        self.terminal_growth = terminal_growth

    async def calculate_fair_value(
        self,
        ticker: str,
        stock_info: dict,
        override_company_type: CompanyType | None = None,
    ) -> ValuationResult:
        """
        Calculate comprehensive fair value for a stock.

        Args:
            ticker: Stock ticker symbol
            stock_info: Data from yahoo_finance.get_stock_info()
            override_company_type: Force a specific company type (optional)

        Returns:
            ValuationResult with fair value range and method breakdown
        """
        result = ValuationResult(ticker=ticker.upper())

        logger.info("Starting valuation", ticker=ticker)

        # Debug: Log available keys in stock_info
        logger.info(
            "Stock info available keys",
            ticker=ticker,
            keys=list(stock_info.keys())[:20] if stock_info else [],
            has_data=bool(stock_info),
        )

        # Step 1: Get market inputs (risk-free rate, etc.)
        result.market_inputs = await self.market_data.get_market_inputs(
            market_cap=self._safe_float(stock_info.get("marketCap", 0))
        )

        # Step 2: Extract basic info
        result.current_price = self._safe_float(stock_info.get("currentPrice", 0))
        if result.current_price == 0:
            result.current_price = self._safe_float(stock_info.get("regularMarketPrice", 0))

        result.shares_outstanding = int(stock_info.get("sharesOutstanding", 0) or 0)

        logger.info(
            "Basic valuation data",
            ticker=ticker,
            current_price=result.current_price,
            shares_outstanding=result.shares_outstanding,
            market_cap=stock_info.get("marketCap"),
        )

        if result.shares_outstanding == 0:
            logger.warning("Shares outstanding is 0, returning early", ticker=ticker)
            result.data_warnings.append("Shares outstanding not available")
            return result

        # Step 3: Classify company
        if override_company_type:
            result.company_type = override_company_type
            result.classification_confidence = 1.0
            result.classification_reasons = ["User override"]
        else:
            (
                result.company_type,
                result.classification_confidence,
                result.classification_reasons,
            ) = self.classifier.classify(stock_info)

        logger.info(
            "Company classified",
            ticker=ticker,
            type=result.company_type.value,
            confidence=result.classification_confidence,
        )

        # Step 4: Determine data availability
        available_data = self.method_selector.assess_data_availability(stock_info)
        result.missing_data = [k for k, v in available_data.items() if not v]

        # Step 5: Calculate discount rates (WACC, Cost of Equity)
        wacc_calculator = WACCCalculator(result.market_inputs)
        wacc_inputs, capm_inputs, credit_rating = wacc_calculator.calculate_full_wacc(
            beta=self._safe_float(stock_info.get("beta", 1.0)),
            market_cap=self._safe_float(stock_info.get("marketCap", 0)),
            total_debt=self._safe_float(stock_info.get("totalDebt", 0)),
            interest_expense=0,  # Would need income statement
            ebit=self._safe_float(stock_info.get("ebitda", 0)),
        )

        result.wacc = wacc_inputs.wacc
        result.cost_of_equity = capm_inputs.cost_of_equity

        # Step 6: Get peer multiples
        sector = stock_info.get("sector", "")
        industry = stock_info.get("industry", "")
        peer_multiples = self.peer_multiples.get_peer_multiples(sector, industry)

        # Step 7: Select and execute valuation methods
        methods = self.method_selector.select_methods(result.company_type, available_data)

        logger.info(
            "Methods selected",
            ticker=ticker,
            methods=[m.value for m, _ in methods],
            weights=[round(w, 3) for _, w in methods],
            missing_data=result.missing_data[:5] if result.missing_data else [],
        )

        for method, weight in methods:
            try:
                method_result = await self._execute_method(
                    method=method,
                    stock_info=stock_info,
                    wacc=wacc_inputs.wacc,
                    cost_of_equity=capm_inputs.cost_of_equity,
                    peer_multiples=peer_multiples,
                )
                if method_result and method_result.fair_value > 0:
                    method_result.weight = weight
                    result.method_results.append(method_result)
                    logger.info(
                        "Method executed successfully",
                        method=method.value,
                        fair_value=method_result.fair_value,
                    )
                else:
                    logger.warning(
                        "Method returned no result",
                        method=method.value,
                        result_none=method_result is None,
                    )
            except Exception as e:
                logger.warning(f"Method {method.value} failed", error=str(e), exc_info=True)
                result.data_warnings.append(f"{method.value}: {str(e)}")

        # Step 8: Calculate composite fair value
        result = self._calculate_composite(result)

        # Step 9: Determine valuation status
        result = self._determine_status(result)

        # Step 10: Calculate overall confidence
        result.overall_confidence = self._calculate_overall_confidence(result)

        # Step 11: Track data sources
        result.data_sources = {
            "stock_info": {"type": "api", "name": "yahoo_finance"},
            "market_data": {"type": "api", "name": result.market_inputs.rf_source},
            "peer_multiples": {"type": "calculated", "name": "sector_defaults"},
            "valuation_engine": {"type": "service", "name": "valuation_engine", "version": "1.0.0"},
        }

        logger.info(
            "Valuation complete",
            ticker=ticker,
            fair_value=result.fair_value,
            upside=result.upside_potential,
            status=result.valuation_status,
            confidence=result.overall_confidence,
        )

        return result

    async def _execute_method(
        self,
        method: ValuationMethod,
        stock_info: dict,
        wacc: float,
        cost_of_equity: float,
        peer_multiples: dict,
    ) -> MethodResult | None:
        """Execute a single valuation method."""
        shares = int(stock_info.get("sharesOutstanding", 0) or 0)
        if shares == 0:
            return None

        # Common calculations
        market_cap = self._safe_float(stock_info.get("marketCap", 0))
        total_debt = self._safe_float(stock_info.get("totalDebt", 0))
        cash = self._safe_float(stock_info.get("totalCash", 0))
        net_debt = total_debt - cash

        # DCF Methods
        if method == ValuationMethod.DCF_FCFF:
            fcf = self._safe_float(stock_info.get("freeCashflow", 0))
            if fcf <= 0:
                return None
            return self.dcf.calculate_fcff(
                current_fcf=fcf,
                growth_rates=None,  # Will be estimated
                wacc=wacc,
                terminal_growth=self.terminal_growth,
                net_debt=net_debt,
                shares_outstanding=shares,
            )

        elif method == ValuationMethod.DCF_FCFE:
            fcf = self._safe_float(stock_info.get("freeCashflow", 0))
            if fcf <= 0:
                return None
            return self.dcf.calculate_fcfe(
                current_fcfe=fcf,
                growth_rates=None,
                cost_of_equity=cost_of_equity,
                terminal_growth=self.terminal_growth,
                shares_outstanding=shares,
            )

        # DDM Methods
        elif method == ValuationMethod.DDM_GORDON:
            dividend = self._safe_float(stock_info.get("dividendRate", 0))
            if dividend <= 0:
                return None
            # Estimate dividend growth from earnings growth or historical
            earnings_growth = self._safe_float(stock_info.get("earningsGrowth", 0.03))
            payout_ratio = self._safe_float(stock_info.get("payoutRatio", 0.5))
            div_growth = self.ddm.estimate_dividend_growth(
                payout_ratio=payout_ratio,
                roe=self._safe_float(stock_info.get("returnOnEquity", 0.12)),
                historical_growth=earnings_growth * 0.6 if earnings_growth > 0 else None,
            )
            return self.ddm.gordon_growth(
                current_dividend=dividend,
                dividend_growth=div_growth,
                cost_of_equity=cost_of_equity,
            )

        elif method == ValuationMethod.DDM_TWO_STAGE:
            dividend = self._safe_float(stock_info.get("dividendRate", 0))
            if dividend <= 0:
                return None
            earnings_growth = self._safe_float(stock_info.get("earningsGrowth", 0.05))
            # Cap high growth rate at reasonable level (25% max)
            high_growth = max(0.02, min(0.25, earnings_growth))
            return self.ddm.two_stage_ddm(
                current_dividend=dividend,
                high_growth_rate=high_growth,
                high_growth_years=5,
                terminal_growth=min(0.03, high_growth * 0.4),  # Terminal growth should be lower
                cost_of_equity=cost_of_equity,
            )

        # Relative Valuation Methods
        elif method == ValuationMethod.RELATIVE_PE:
            eps = self._safe_float(stock_info.get("trailingEps", 0))
            if eps <= 0:
                eps = self._safe_float(stock_info.get("forwardEps", 0))
            if eps <= 0:
                return None
            pe_data = peer_multiples.get("pe", {"median": 18, "low": 12, "high": 25})
            return self.relative.pe_valuation(
                eps=eps,
                peer_pe_median=pe_data["median"],
                peer_pe_range=(pe_data["low"], pe_data["high"]),
            )

        elif method == ValuationMethod.RELATIVE_PB:
            book_value = self._safe_float(stock_info.get("bookValue", 0))
            if book_value <= 0:
                return None
            pb_data = peer_multiples.get("pb", {"median": 2.5, "low": 1.5, "high": 4})
            return self.relative.pb_valuation(
                book_value_per_share=book_value,
                peer_pb_median=pb_data["median"],
                peer_pb_range=(pb_data["low"], pb_data["high"]),
            )

        elif method == ValuationMethod.RELATIVE_PS:
            revenue = self._safe_float(stock_info.get("totalRevenue", 0))
            if revenue <= 0:
                return None
            revenue_per_share = revenue / shares
            ps_data = peer_multiples.get("ps", {"median": 2, "low": 1, "high": 4})
            return self.relative.ps_valuation(
                revenue_per_share=revenue_per_share,
                peer_ps_median=ps_data["median"],
                peer_ps_range=(ps_data["low"], ps_data["high"]),
            )

        elif method == ValuationMethod.RELATIVE_EV_EBITDA:
            ebitda = self._safe_float(stock_info.get("ebitda", 0))
            if ebitda <= 0:
                return None
            ev_ebitda_data = peer_multiples.get(
                "ev_ebitda", {"median": 12, "low": 8, "high": 18}
            )
            return self.relative.ev_ebitda_valuation(
                ebitda=ebitda,
                net_debt=net_debt,
                shares_outstanding=shares,
                peer_ev_ebitda_median=ev_ebitda_data["median"],
                peer_ev_ebitda_range=(ev_ebitda_data["low"], ev_ebitda_data["high"]),
            )

        elif method == ValuationMethod.RELATIVE_EV_REVENUE:
            revenue = self._safe_float(stock_info.get("totalRevenue", 0))
            if revenue <= 0:
                return None
            ev_rev_data = peer_multiples.get(
                "ev_revenue", {"median": 2.5, "low": 1, "high": 5}
            )
            growth_rate = self._safe_float(stock_info.get("revenueGrowth", 0))
            return self.relative.ev_revenue_valuation(
                revenue=revenue,
                net_debt=net_debt,
                shares_outstanding=shares,
                peer_ev_revenue_median=ev_rev_data["median"],
                peer_ev_revenue_range=(ev_rev_data["low"], ev_rev_data["high"]),
                growth_rate=growth_rate,
            )

        # Asset-Based Methods
        elif method == ValuationMethod.ASSET_BOOK_VALUE:
            total_assets = self._safe_float(stock_info.get("totalAssets", 0))
            total_liabilities = self._safe_float(stock_info.get("totalDebt", 0))
            if total_assets <= 0:
                return None
            return self.asset_based.book_value(
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                shares_outstanding=shares,
            )

        elif method == ValuationMethod.ASSET_LIQUIDATION:
            total_assets = self._safe_float(stock_info.get("totalAssets", 0))
            if total_assets <= 0:
                return None
            # Simplified - would need more detailed balance sheet data
            return self.asset_based.liquidation_value(
                cash=cash,
                receivables=total_assets * 0.1,  # Estimate
                inventory=total_assets * 0.1,
                property_plant_equipment=total_assets * 0.3,
                other_assets=total_assets * 0.2,
                total_liabilities=total_debt,
                shares_outstanding=shares,
                orderly=True,
            )

        # Growth Company Methods
        elif method == ValuationMethod.GROWTH_RULE_40:
            revenue = self._safe_float(stock_info.get("totalRevenue", 0))
            if revenue <= 0:
                return None
            growth_rate = self._safe_float(stock_info.get("revenueGrowth", 0))
            margin = self._safe_float(stock_info.get("profitMargins", 0))
            ev_rev_data = peer_multiples.get(
                "ev_revenue", {"median": 5, "low": 2, "high": 10}
            )
            return self.growth.rule_of_40(
                revenue=revenue,
                revenue_growth_rate=growth_rate,
                profit_margin=margin,
                net_debt=net_debt,
                shares_outstanding=shares,
                peer_ev_revenue_median=ev_rev_data["median"],
            )

        elif method == ValuationMethod.GROWTH_EV_ARR:
            revenue = self._safe_float(stock_info.get("totalRevenue", 0))
            if revenue <= 0:
                return None
            growth_rate = self._safe_float(stock_info.get("revenueGrowth", 0))
            gross_margin = self._safe_float(stock_info.get("grossMargins", 0))
            return self.growth.ev_arr_valuation(
                arr=revenue,  # Use revenue as proxy for ARR
                growth_rate=growth_rate,
                net_debt=net_debt,
                shares_outstanding=shares,
                gross_margin=gross_margin if gross_margin > 0 else None,
            )

        return None

    def _calculate_composite(self, result: ValuationResult) -> ValuationResult:
        """Calculate weighted composite fair value from method results."""
        if not result.method_results:
            result.data_warnings.append("No valuation methods could be executed")
            return result

        # Calculate weighted average
        weighted_sum = 0
        total_weight = 0

        all_lows = []
        all_highs = []

        # Sanity check: If a method produces a value > 5x current price, reduce its weight
        # This prevents extreme DCF valuations from dominating the result
        MAX_REASONABLE_MULTIPLE = 5.0
        current_price = result.current_price

        for mr in result.method_results:
            if mr.fair_value > 0 and mr.confidence > 30:
                # Check for extreme valuations
                effective_weight = mr.weight * (mr.confidence / 100)

                if current_price > 0:
                    value_multiple = mr.fair_value / current_price
                    if value_multiple > MAX_REASONABLE_MULTIPLE:
                        # Reduce weight for extreme valuations
                        weight_penalty = min(0.8, (value_multiple - MAX_REASONABLE_MULTIPLE) / 10)
                        effective_weight *= (1 - weight_penalty)
                        result.data_warnings.append(
                            f"{mr.method.value}: Fair value {value_multiple:.1f}x current price - weight reduced"
                        )
                        logger.warning(
                            "Extreme valuation detected",
                            method=mr.method.value,
                            fair_value=mr.fair_value,
                            current_price=current_price,
                            multiple=value_multiple,
                            weight_reduced_by=f"{weight_penalty:.0%}",
                        )

                weighted_sum += mr.fair_value * effective_weight
                total_weight += effective_weight

                if mr.low_estimate > 0:
                    all_lows.append(mr.low_estimate)
                if mr.high_estimate > 0:
                    all_highs.append(mr.high_estimate)

        if total_weight > 0:
            result.fair_value = weighted_sum / total_weight

        # Calculate range
        if all_lows:
            result.fair_value_low = sum(all_lows) / len(all_lows)
        else:
            result.fair_value_low = result.fair_value * 0.85

        if all_highs:
            result.fair_value_high = sum(all_highs) / len(all_highs)
        else:
            result.fair_value_high = result.fair_value * 1.20

        # Set primary method (highest weighted executed)
        if result.method_results:
            primary = max(result.method_results, key=lambda x: x.weight * x.confidence)
            result.primary_method = primary.method

        return result

    def _determine_status(self, result: ValuationResult) -> ValuationResult:
        """Determine valuation status based on fair value vs current price."""
        if result.fair_value <= 0 or result.current_price <= 0:
            result.valuation_status = "insufficient_data"
            return result

        result.upside_potential = (
            (result.fair_value - result.current_price) / result.current_price
        ) * 100

        # Margin of safety
        if result.fair_value > result.current_price:
            result.margin_of_safety = (
                (result.fair_value - result.current_price) / result.fair_value
            ) * 100
        else:
            result.margin_of_safety = 0

        # Determine status
        if result.upside_potential > 25:
            result.valuation_status = "significantly_undervalued"
        elif result.upside_potential > 10:
            result.valuation_status = "undervalued"
        elif result.upside_potential > -10:
            result.valuation_status = "fairly_valued"
        elif result.upside_potential > -20:
            result.valuation_status = "overvalued"
        else:
            result.valuation_status = "significantly_overvalued"

        return result

    def _calculate_overall_confidence(self, result: ValuationResult) -> float:
        """Calculate overall confidence score."""
        if not result.method_results:
            return 0

        # Base confidence from method results
        avg_confidence = sum(mr.confidence for mr in result.method_results) / len(
            result.method_results
        )

        # Reduce for missing data
        missing_penalty = min(20, len(result.missing_data) * 3)

        # Reduce for few methods
        if len(result.method_results) < 2:
            method_penalty = 15
        elif len(result.method_results) < 3:
            method_penalty = 10
        else:
            method_penalty = 0

        # Bonus for method agreement
        if len(result.method_results) >= 2:
            values = [mr.fair_value for mr in result.method_results if mr.fair_value > 0]
            if values:
                avg_value = sum(values) / len(values)
                deviations = [abs(v - avg_value) / avg_value for v in values]
                avg_deviation = sum(deviations) / len(deviations)
                if avg_deviation < 0.15:
                    agreement_bonus = 10
                elif avg_deviation < 0.25:
                    agreement_bonus = 5
                else:
                    agreement_bonus = 0
            else:
                agreement_bonus = 0
        else:
            agreement_bonus = 0

        confidence = avg_confidence - missing_penalty - method_penalty + agreement_bonus
        return max(20, min(95, confidence))

    def _safe_float(self, value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            result = float(value)
            return result if result == result else 0.0  # Check for NaN
        except (TypeError, ValueError):
            return 0.0
