"""
Enhanced Growth Stock Analysis Agent

Comprehensive analysis framework combining:
- Multi-factor analysis (fundamentals, sentiment, technicals, competition, risks)
- Weighted scoring for investment recommendations
- Strict data-driven approach (no hallucination)
- Portfolio allocation and multiple price targets
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging

import ollama

from backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class InvestmentRecommendation(Enum):
    """Investment recommendations"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class CompanyProfile:
    """Company profile and basic data"""
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: float = 0.0
    employees: int = 0
    description: str = ""
    website: str = ""


@dataclass
class FinancialData:
    """Financial metrics and trends"""
    # Revenue data
    revenue_current: float = 0.0
    revenue_yoy_growth: float = 0.0
    revenue_cagr_3y: float = 0.0
    revenue_cagr_5y: float = 0.0

    # Profitability
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    margin_trend: str = ""  # "expanding", "stable", "contracting"

    # Earnings
    eps: float = 0.0
    eps_growth_yoy: float = 0.0

    # Cash flow
    operating_cashflow: float = 0.0
    free_cashflow: float = 0.0
    fcf_margin: float = 0.0
    cash_balance: float = 0.0

    # Balance sheet
    total_debt: float = 0.0
    equity: float = 0.0
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0

    # Returns
    roe: float = 0.0
    roa: float = 0.0
    roic: float = 0.0


@dataclass
class SentimentData:
    """Market sentiment indicators"""
    # Analyst ratings
    analyst_buy_count: int = 0
    analyst_hold_count: int = 0
    analyst_sell_count: int = 0
    analyst_consensus: str = ""  # "buy", "hold", "sell"

    # Price targets
    price_target_avg: float = 0.0
    price_target_high: float = 0.0
    price_target_low: float = 0.0

    # News sentiment
    news_sentiment_score: float = 0.0  # -1 to 1
    news_count_positive: int = 0
    news_count_negative: int = 0

    # Ownership
    institutional_ownership: float = 0.0
    insider_ownership: float = 0.0
    short_interest: float = 0.0

    # Fund tracking
    funds_holding_count: int = 0
    funds_increasing_positions: int = 0
    funds_decreasing_positions: int = 0


@dataclass
class TechnicalIndicators:
    """Technical analysis indicators"""
    current_price: float = 0.0
    week_52_high: float = 0.0
    week_52_low: float = 0.0
    price_change_1m: float = 0.0
    price_change_3m: float = 0.0
    price_change_6m: float = 0.0
    price_change_ytd: float = 0.0

    # Indicators
    rsi: float = 0.0
    rsi_signal: str = ""  # "overbought", "neutral", "oversold"
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0

    # Moving averages
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    price_above_sma_20: bool = False
    price_above_sma_50: bool = False
    price_above_sma_200: bool = False

    # Volatility
    beta: float = 0.0
    volatility: float = 0.0

    # Volume
    volume_avg_10d: int = 0
    volume_ratio: float = 1.0  # Current vs average


@dataclass
class CompetitorAnalysis:
    """Competitive positioning analysis"""
    peers: List[str] = field(default_factory=list)

    # Relative valuation
    pe_ratio: float = 0.0
    pe_vs_peers: str = ""  # "premium", "discount", "inline"
    peg_ratio: float = 0.0
    peg_vs_peers: str = ""
    ps_ratio: float = 0.0
    ps_vs_peers: str = ""

    # Relative growth
    revenue_growth_vs_peers: str = ""  # "leading", "inline", "lagging"
    margin_vs_peers: str = ""

    # Market position
    market_share: float = 0.0
    competitive_advantages: List[str] = field(default_factory=list)
    competitive_risks: List[str] = field(default_factory=list)


@dataclass
class RiskAnalysis:
    """Comprehensive risk assessment"""
    business_risks: List[str] = field(default_factory=list)
    financial_risks: List[str] = field(default_factory=list)
    regulatory_risks: List[str] = field(default_factory=list)
    market_risks: List[str] = field(default_factory=list)
    geopolitical_risks: List[str] = field(default_factory=list)

    risk_score: float = 5.0  # 1 (low) to 10 (high)
    risk_level: str = "moderate"  # "low", "moderate", "high", "very high"


@dataclass
class DataCompletenessReport:
    """Tracks which data categories are available"""
    has_growth_metrics: bool = False
    has_margin_data: bool = False
    has_cash_flow_data: bool = False
    has_valuation_data: bool = False
    has_analyst_data: bool = False
    has_peer_comparison: bool = False
    has_technical_data: bool = False

    missing_critical: List[str] = field(default_factory=list)
    completeness_score: float = 0.0  # 0 to 100


@dataclass
class GrowthAnalysisResult:
    """Complete analysis output"""
    ticker: str
    analysis_date: datetime = field(default_factory=datetime.now)

    # Data components
    company_profile: CompanyProfile = field(default_factory=lambda: CompanyProfile(ticker=""))
    financial_data: FinancialData = field(default_factory=FinancialData)
    sentiment_data: SentimentData = field(default_factory=SentimentData)
    technical_indicators: TechnicalIndicators = field(default_factory=TechnicalIndicators)
    competitor_analysis: CompetitorAnalysis = field(default_factory=CompetitorAnalysis)
    risk_analysis: RiskAnalysis = field(default_factory=RiskAnalysis)

    # Analysis outputs
    recommendation: InvestmentRecommendation = InvestmentRecommendation.HOLD
    confidence_score: float = 0.0  # 0 to 100
    portfolio_allocation: float = 0.0  # Suggested % of portfolio

    # Price targets
    price_target_optimistic: float = 0.0
    price_target_base: float = 0.0
    price_target_pessimistic: float = 0.0
    upside_potential: float = 0.0  # % to base target

    # Key insights
    key_strengths: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    catalyst_points: List[str] = field(default_factory=list)
    monitoring_points: List[str] = field(default_factory=list)

    # Scoring breakdown
    fundamental_score: float = 0.0
    sentiment_score: float = 0.0
    technical_score: float = 0.0
    competitive_score: float = 0.0
    risk_adjusted_score: float = 0.0
    composite_score: float = 0.0

    # Data quality
    data_completeness: DataCompletenessReport = field(default_factory=DataCompletenessReport)
    data_sources: Dict[str, Any] = field(default_factory=dict)

    # AI analysis
    ai_summary: str = ""
    ai_reasoning: str = ""


class GrowthAnalysisAgent:
    """
    Comprehensive growth stock analysis agent

    Combines multiple analysis dimensions with weighted scoring
    to generate investment recommendations and portfolio allocations.
    """

    def __init__(self):
        """Initialize the analysis agent"""
        self.settings = settings
        self.model = settings.ollama_model

        # Scoring weights
        self.weights = {
            "fundamental": 0.35,
            "sentiment": 0.20,
            "technical": 0.15,
            "competitive": 0.20,
            "risk": 0.10
        }

    async def analyze(
        self,
        ticker: str,
        stock_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None,
        fund_ownership: Optional[List[Dict[str, Any]]] = None
    ) -> GrowthAnalysisResult:
        """
        Perform comprehensive growth stock analysis

        Args:
            ticker: Stock ticker symbol
            stock_data: Raw stock data from data sources
            market_context: Optional market sentiment context
            fund_ownership: Optional institutional ownership data

        Returns:
            GrowthAnalysisResult with complete analysis
        """
        logger.info(f"Starting comprehensive growth analysis for {ticker}")

        result = GrowthAnalysisResult(ticker=ticker.upper())

        # Step 1: Validate data completeness
        result.data_completeness = self._check_data_completeness(stock_data)

        if result.data_completeness.completeness_score < 30:
            logger.warning(f"Insufficient data for {ticker}: {result.data_completeness.completeness_score}%")
            result.key_risks.append("Insufficient data for comprehensive analysis")

        # Step 2: Extract and structure data
        result.company_profile = self._extract_company_profile(ticker, stock_data)
        result.financial_data = self._extract_financial_data(stock_data)
        result.sentiment_data = self._extract_sentiment_data(stock_data, fund_ownership)
        result.technical_indicators = self._extract_technical_indicators(stock_data)

        # Step 3: Perform analyses
        result.competitor_analysis = await self._analyze_competition(ticker, stock_data)
        result.risk_analysis = await self._assess_risks(ticker, stock_data, result.financial_data)

        # Step 4: Calculate scores
        result.fundamental_score = self._score_fundamentals(result.financial_data)
        result.sentiment_score = self._score_sentiment(result.sentiment_data)
        result.technical_score = self._score_technicals(result.technical_indicators)
        result.competitive_score = self._score_competitive_position(result.competitor_analysis)
        result.risk_adjusted_score = 10 - result.risk_analysis.risk_score

        # Step 5: Generate composite score and recommendation
        result.composite_score = self._calculate_composite_score(
            result.fundamental_score,
            result.sentiment_score,
            result.technical_score,
            result.competitive_score,
            result.risk_adjusted_score
        )

        result.recommendation, result.confidence_score, result.portfolio_allocation = \
            self._generate_recommendation(result.composite_score, result.data_completeness.completeness_score)

        # Step 6: Calculate price targets
        result = self._calculate_price_targets(result)

        # Step 7: Extract key insights
        result.key_strengths = self._identify_strengths(result)
        result.key_risks = self._identify_key_risks(result)
        result.catalyst_points = self._identify_catalysts(result)
        result.monitoring_points = self._generate_monitoring_points(result)

        # Step 8: Run AI analysis for qualitative insights
        result.ai_summary, result.ai_reasoning = await self._run_ai_analysis(result, market_context)

        # Step 9: Track data sources
        result.data_sources = self._compile_data_sources(stock_data)

        logger.info(f"Completed analysis for {ticker}: {result.recommendation.value} ({result.confidence_score:.0f}% confidence)")

        return result

    def _check_data_completeness(self, stock_data: Dict[str, Any]) -> DataCompletenessReport:
        """Validate data completeness"""
        report = DataCompletenessReport()

        # Check each category
        info = stock_data.get("info", {})

        # Growth metrics
        has_revenue = info.get("totalRevenue") or info.get("revenue")
        has_growth = info.get("revenueGrowth") is not None
        report.has_growth_metrics = bool(has_revenue and has_growth)

        # Margins
        has_margins = any([
            info.get("grossMargins"),
            info.get("operatingMargins"),
            info.get("profitMargins")
        ])
        report.has_margin_data = bool(has_margins)

        # Cash flow
        has_cash_flow = any([
            info.get("operatingCashflow"),
            info.get("freeCashflow")
        ])
        report.has_cash_flow_data = bool(has_cash_flow)

        # Valuation
        has_valuation = any([
            info.get("trailingPE"),
            info.get("priceToSalesTrailing12Months"),
            info.get("priceToBook")
        ])
        report.has_valuation_data = bool(has_valuation)

        # Analyst data
        has_recommendations = stock_data.get("recommendations") is not None
        has_targets = info.get("targetMeanPrice") is not None
        report.has_analyst_data = has_recommendations or has_targets

        # Technicals
        has_technicals = "technicals" in stock_data and stock_data["technicals"]
        report.has_technical_data = bool(has_technicals)

        # Peers
        has_peers = "peers" in stock_data and stock_data.get("peers")
        report.has_peer_comparison = bool(has_peers)

        # Calculate completeness
        categories = [
            report.has_growth_metrics,
            report.has_margin_data,
            report.has_cash_flow_data,
            report.has_valuation_data,
            report.has_analyst_data,
            report.has_technical_data,
            report.has_peer_comparison
        ]
        report.completeness_score = (sum(categories) / len(categories)) * 100

        # Identify missing critical data
        if not report.has_growth_metrics:
            report.missing_critical.append("Revenue and growth data")
        if not report.has_margin_data:
            report.missing_critical.append("Profitability margins")
        if not report.has_valuation_data:
            report.missing_critical.append("Valuation metrics")

        return report

    def _extract_company_profile(self, ticker: str, stock_data: Dict[str, Any]) -> CompanyProfile:
        """Extract company profile data"""
        info = stock_data.get("info", {})

        return CompanyProfile(
            ticker=ticker,
            name=info.get("longName", info.get("shortName", "")),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=float(info.get("marketCap", 0)),
            employees=int(info.get("fullTimeEmployees", 0)),
            description=info.get("longBusinessSummary", ""),
            website=info.get("website", "")
        )

    def _extract_financial_data(self, stock_data: Dict[str, Any]) -> FinancialData:
        """Extract and calculate financial metrics"""
        info = stock_data.get("info", {})

        financial = FinancialData()

        # Revenue
        financial.revenue_current = float(info.get("totalRevenue", 0))
        financial.revenue_yoy_growth = float(info.get("revenueGrowth", 0)) * 100 if info.get("revenueGrowth") else 0.0

        # Margins
        financial.gross_margin = float(info.get("grossMargins", 0)) * 100 if info.get("grossMargins") else 0.0
        financial.operating_margin = float(info.get("operatingMargins", 0)) * 100 if info.get("operatingMargins") else 0.0
        financial.net_margin = float(info.get("profitMargins", 0)) * 100 if info.get("profitMargins") else 0.0

        # Earnings
        financial.eps = float(info.get("trailingEps", 0))
        financial.eps_growth_yoy = float(info.get("earningsGrowth", 0)) * 100 if info.get("earningsGrowth") else 0.0

        # Cash flow
        financial.operating_cashflow = float(info.get("operatingCashflow", 0))
        financial.free_cashflow = float(info.get("freeCashflow", 0))
        if financial.revenue_current > 0:
            financial.fcf_margin = (financial.free_cashflow / financial.revenue_current) * 100
        financial.cash_balance = float(info.get("totalCash", 0))

        # Balance sheet
        financial.total_debt = float(info.get("totalDebt", 0))
        financial.equity = float(info.get("totalStockholderEquity", 0))
        financial.debt_to_equity = float(info.get("debtToEquity", 0)) / 100 if info.get("debtToEquity") else 0.0
        financial.current_ratio = float(info.get("currentRatio", 0))

        # Returns
        financial.roe = float(info.get("returnOnEquity", 0)) * 100 if info.get("returnOnEquity") else 0.0
        financial.roa = float(info.get("returnOnAssets", 0)) * 100 if info.get("returnOnAssets") else 0.0

        return financial

    def _extract_sentiment_data(
        self,
        stock_data: Dict[str, Any],
        fund_ownership: Optional[List[Dict[str, Any]]] = None
    ) -> SentimentData:
        """Extract sentiment indicators"""
        info = stock_data.get("info", {})
        recommendations = stock_data.get("recommendations", [])

        sentiment = SentimentData()

        # Analyst ratings
        if recommendations:
            latest = recommendations[-1] if isinstance(recommendations, list) else {}
            sentiment.analyst_buy_count = int(latest.get("strongBuy", 0)) + int(latest.get("buy", 0))
            sentiment.analyst_hold_count = int(latest.get("hold", 0))
            sentiment.analyst_sell_count = int(latest.get("sell", 0)) + int(latest.get("strongSell", 0))

            total = sentiment.analyst_buy_count + sentiment.analyst_hold_count + sentiment.analyst_sell_count
            if total > 0:
                if sentiment.analyst_buy_count / total > 0.5:
                    sentiment.analyst_consensus = "buy"
                elif sentiment.analyst_sell_count / total > 0.4:
                    sentiment.analyst_consensus = "sell"
                else:
                    sentiment.analyst_consensus = "hold"

        # Price targets
        sentiment.price_target_avg = float(info.get("targetMeanPrice", 0))
        sentiment.price_target_high = float(info.get("targetHighPrice", 0))
        sentiment.price_target_low = float(info.get("targetLowPrice", 0))

        # Ownership
        sentiment.institutional_ownership = float(info.get("heldPercentInstitutions", 0)) * 100 if info.get("heldPercentInstitutions") else 0.0
        sentiment.insider_ownership = float(info.get("heldPercentInsiders", 0)) * 100 if info.get("heldPercentInsiders") else 0.0
        sentiment.short_interest = float(info.get("shortPercentOfFloat", 0)) * 100 if info.get("shortPercentOfFloat") else 0.0

        # Fund tracking
        if fund_ownership:
            sentiment.funds_holding_count = len(fund_ownership)
            for fund in fund_ownership:
                change = fund.get("change_type", "")
                if change in ["new", "increased"]:
                    sentiment.funds_increasing_positions += 1
                elif change in ["decreased", "sold"]:
                    sentiment.funds_decreasing_positions += 1

        return sentiment

    def _extract_technical_indicators(self, stock_data: Dict[str, Any]) -> TechnicalIndicators:
        """Extract technical analysis data"""
        info = stock_data.get("info", {})
        technicals = stock_data.get("technicals", {})

        indicators = TechnicalIndicators()

        # Price data
        indicators.current_price = float(info.get("currentPrice", 0))
        indicators.week_52_high = float(info.get("fiftyTwoWeekHigh", 0))
        indicators.week_52_low = float(info.get("fiftyTwoWeekLow", 0))

        # Performance
        indicators.price_change_ytd = float(info.get("52WeekChange", 0)) * 100 if info.get("52WeekChange") else 0.0

        # Technical indicators from analysis
        if technicals:
            indicators.rsi = float(technicals.get("rsi", 0))
            indicators.rsi_signal = technicals.get("rsi_signal", "neutral")

            indicators.macd = float(technicals.get("macd", 0))
            indicators.macd_signal = float(technicals.get("macd_signal", 0))
            indicators.macd_histogram = float(technicals.get("macd_histogram", 0))

            indicators.sma_20 = float(technicals.get("sma_20", 0))
            indicators.sma_50 = float(technicals.get("sma_50", 0))
            indicators.sma_200 = float(technicals.get("sma_200", 0))

            if indicators.current_price > 0:
                indicators.price_above_sma_20 = indicators.current_price > indicators.sma_20
                indicators.price_above_sma_50 = indicators.current_price > indicators.sma_50
                indicators.price_above_sma_200 = indicators.current_price > indicators.sma_200

        # Volatility
        indicators.beta = float(info.get("beta", 1.0))

        # Volume
        indicators.volume_avg_10d = int(info.get("averageVolume10days", 0))

        return indicators

    async def _analyze_competition(self, ticker: str, stock_data: Dict[str, Any]) -> CompetitorAnalysis:
        """Analyze competitive position"""
        info = stock_data.get("info", {})
        peers_data = stock_data.get("peers", [])

        analysis = CompetitorAnalysis()

        # Extract peer tickers
        if peers_data:
            analysis.peers = [p.get("ticker", "") for p in peers_data if p.get("ticker") != ticker][:5]

        # Valuation comparison
        pe = float(info.get("trailingPE", 0))
        ps = float(info.get("priceToSalesTrailing12Months", 0))
        peg = float(info.get("pegRatio", 0))

        analysis.pe_ratio = pe
        analysis.ps_ratio = ps
        analysis.peg_ratio = peg

        # Compare with peers if data available
        if peers_data:
            peer_pes = [float(p.get("trailingPE", 0)) for p in peers_data if p.get("trailingPE")]
            if peer_pes and pe > 0:
                avg_peer_pe = sum(peer_pes) / len(peer_pes)
                if pe > avg_peer_pe * 1.2:
                    analysis.pe_vs_peers = "premium"
                elif pe < avg_peer_pe * 0.8:
                    analysis.pe_vs_peers = "discount"
                else:
                    analysis.pe_vs_peers = "inline"

        # Competitive advantages (basic inference from data)
        if float(info.get("grossMargins", 0)) > 0.5:
            analysis.competitive_advantages.append("High gross margins indicate pricing power")

        if float(info.get("returnOnEquity", 0)) > 0.2:
            analysis.competitive_advantages.append("Strong capital efficiency (ROE > 20%)")

        return analysis

    async def _assess_risks(
        self,
        ticker: str,
        stock_data: Dict[str, Any],
        financial_data: FinancialData
    ) -> RiskAnalysis:
        """Comprehensive risk assessment"""
        info = stock_data.get("info", {})
        risk = RiskAnalysis()

        # Financial risks
        if financial_data.debt_to_equity > 1.5:
            risk.financial_risks.append("High leverage (Debt/Equity > 1.5)")

        if financial_data.free_cashflow < 0:
            risk.financial_risks.append("Negative free cash flow")

        if financial_data.current_ratio < 1.0:
            risk.financial_risks.append("Low liquidity (Current Ratio < 1.0)")

        # Business risks
        if financial_data.revenue_yoy_growth < 0:
            risk.business_risks.append("Revenue decline year-over-year")

        if financial_data.net_margin < 0:
            risk.business_risks.append("Unprofitable operations")

        # Market risks
        beta = float(info.get("beta", 1.0))
        if beta > 1.5:
            risk.market_risks.append(f"High volatility (Beta: {beta:.2f})")

        short_interest = float(info.get("shortPercentOfFloat", 0))
        if short_interest > 0.1:
            risk.market_risks.append(f"Elevated short interest ({short_interest*100:.1f}%)")

        # Calculate risk score
        total_risks = (
            len(risk.business_risks) +
            len(risk.financial_risks) +
            len(risk.regulatory_risks) +
            len(risk.market_risks) +
            len(risk.geopolitical_risks)
        )

        risk.risk_score = min(10, max(1, 3 + total_risks * 0.7))

        if risk.risk_score < 3:
            risk.risk_level = "low"
        elif risk.risk_score < 5:
            risk.risk_level = "moderate"
        elif risk.risk_score < 7:
            risk.risk_level = "high"
        else:
            risk.risk_level = "very high"

        return risk

    def _score_fundamentals(self, financial: FinancialData) -> float:
        """Score fundamental strength (0-10)"""
        score = 5.0  # Base score

        # Growth (weight: 40%)
        if financial.revenue_yoy_growth > 20:
            score += 1.5
        elif financial.revenue_yoy_growth > 10:
            score += 0.8
        elif financial.revenue_yoy_growth < 0:
            score -= 1.5

        # Profitability (weight: 30%)
        if financial.net_margin > 20:
            score += 1.2
        elif financial.net_margin > 10:
            score += 0.6
        elif financial.net_margin < 0:
            score -= 1.2

        # Cash flow (weight: 20%)
        if financial.fcf_margin > 15:
            score += 0.8
        elif financial.fcf_margin > 5:
            score += 0.4
        elif financial.free_cashflow < 0:
            score -= 0.8

        # Balance sheet (weight: 10%)
        if financial.debt_to_equity < 0.3:
            score += 0.4
        elif financial.debt_to_equity > 1.5:
            score -= 0.4

        return max(0, min(10, score))

    def _score_sentiment(self, sentiment: SentimentData) -> float:
        """Score market sentiment (0-10)"""
        score = 5.0

        # Analyst consensus (weight: 40%)
        if sentiment.analyst_consensus == "buy":
            score += 1.6
        elif sentiment.analyst_consensus == "sell":
            score -= 1.6

        total_analysts = (sentiment.analyst_buy_count +
                         sentiment.analyst_hold_count +
                         sentiment.analyst_sell_count)
        if total_analysts > 0:
            buy_ratio = sentiment.analyst_buy_count / total_analysts
            if buy_ratio > 0.7:
                score += 0.8
            elif buy_ratio < 0.3:
                score -= 0.8

        # Fund activity (weight: 30%)
        if sentiment.funds_holding_count > 0:
            increasing_ratio = sentiment.funds_increasing_positions / sentiment.funds_holding_count
            if increasing_ratio > 0.6:
                score += 1.2
            elif increasing_ratio < 0.3:
                score -= 1.2

        # Short interest (weight: 15%)
        if sentiment.short_interest > 20:
            score -= 0.6
        elif sentiment.short_interest < 5:
            score += 0.3

        # Institutional ownership (weight: 15%)
        if sentiment.institutional_ownership > 70:
            score += 0.6
        elif sentiment.institutional_ownership < 30:
            score -= 0.3

        return max(0, min(10, score))

    def _score_technicals(self, tech: TechnicalIndicators) -> float:
        """Score technical indicators (0-10)"""
        score = 5.0

        # RSI (weight: 30%)
        if tech.rsi_signal == "oversold":
            score += 1.2
        elif tech.rsi_signal == "overbought":
            score -= 1.2

        # Moving averages (weight: 40%)
        ma_signals = sum([tech.price_above_sma_20, tech.price_above_sma_50, tech.price_above_sma_200])
        if ma_signals == 3:
            score += 1.6
        elif ma_signals == 0:
            score -= 1.6
        elif ma_signals == 2:
            score += 0.8

        # MACD (weight: 20%)
        if tech.macd_histogram > 0:
            score += 0.8
        else:
            score -= 0.4

        # Momentum (weight: 10%)
        if tech.price_change_ytd > 20:
            score += 0.4
        elif tech.price_change_ytd < -20:
            score -= 0.4

        return max(0, min(10, score))

    def _score_competitive_position(self, comp: CompetitorAnalysis) -> float:
        """Score competitive position (0-10)"""
        score = 5.0

        # Valuation relative to peers (weight: 40%)
        if comp.pe_vs_peers == "discount":
            score += 1.6
        elif comp.pe_vs_peers == "premium":
            score -= 0.8

        # PEG ratio (weight: 30%)
        if 0 < comp.peg_ratio < 1:
            score += 1.2  # Growth at reasonable price
        elif comp.peg_ratio > 2:
            score -= 1.2

        # Competitive advantages (weight: 30%)
        score += min(1.2, len(comp.competitive_advantages) * 0.3)
        score -= min(1.2, len(comp.competitive_risks) * 0.3)

        return max(0, min(10, score))

    def _calculate_composite_score(
        self,
        fundamental: float,
        sentiment: float,
        technical: float,
        competitive: float,
        risk_adjusted: float
    ) -> float:
        """Calculate weighted composite score"""
        composite = (
            fundamental * self.weights["fundamental"] +
            sentiment * self.weights["sentiment"] +
            technical * self.weights["technical"] +
            competitive * self.weights["competitive"] +
            risk_adjusted * self.weights["risk"]
        )
        return composite

    def _generate_recommendation(
        self,
        composite_score: float,
        completeness_score: float
    ) -> Tuple[InvestmentRecommendation, float, float]:
        """Generate recommendation with confidence and allocation"""

        # Adjust confidence based on data completeness
        confidence_base = min(95, composite_score * 10)
        confidence = confidence_base * (completeness_score / 100)

        # Determine recommendation
        if composite_score >= 8.0:
            recommendation = InvestmentRecommendation.STRONG_BUY
            allocation = 10.0
        elif composite_score >= 6.5:
            recommendation = InvestmentRecommendation.BUY
            allocation = 7.0
        elif composite_score >= 4.5:
            recommendation = InvestmentRecommendation.HOLD
            allocation = 3.0
        elif composite_score >= 3.0:
            recommendation = InvestmentRecommendation.SELL
            allocation = 0.0
        else:
            recommendation = InvestmentRecommendation.STRONG_SELL
            allocation = 0.0

        # Reduce allocation if confidence is low
        if confidence < 50:
            allocation *= 0.5

        return recommendation, confidence, allocation

    def _calculate_price_targets(self, result: GrowthAnalysisResult) -> GrowthAnalysisResult:
        """Calculate price targets for different scenarios"""
        current_price = result.technical_indicators.current_price

        if current_price <= 0:
            return result

        # Use analyst target if available
        if result.sentiment_data.price_target_avg > 0:
            result.price_target_base = result.sentiment_data.price_target_avg
            result.price_target_optimistic = result.sentiment_data.price_target_high or (result.price_target_base * 1.25)
            result.price_target_pessimistic = result.sentiment_data.price_target_low or (result.price_target_base * 0.85)
        else:
            # Calculate based on composite score
            if result.composite_score >= 7:
                upside = 0.30
            elif result.composite_score >= 5:
                upside = 0.15
            else:
                upside = 0.05

            result.price_target_base = current_price * (1 + upside)
            result.price_target_optimistic = current_price * (1 + upside * 1.5)
            result.price_target_pessimistic = current_price * (1 + upside * 0.5)

        # Calculate upside potential
        result.upside_potential = ((result.price_target_base - current_price) / current_price) * 100

        return result

    def _identify_strengths(self, result: GrowthAnalysisResult) -> List[str]:
        """Identify key strengths"""
        strengths = []

        fin = result.financial_data
        sent = result.sentiment_data
        tech = result.technical_indicators

        if fin.revenue_yoy_growth > 15:
            strengths.append(f"Strong revenue growth ({fin.revenue_yoy_growth:.1f}% YoY)")

        if fin.net_margin > 15:
            strengths.append(f"High profitability ({fin.net_margin:.1f}% net margin)")

        if fin.free_cashflow > 0 and fin.fcf_margin > 10:
            strengths.append(f"Strong cash generation ({fin.fcf_margin:.1f}% FCF margin)")

        if sent.analyst_consensus == "buy":
            strengths.append(f"Analyst consensus: BUY ({sent.analyst_buy_count} buy ratings)")

        if sent.funds_increasing_positions > sent.funds_decreasing_positions:
            strengths.append(f"Institutional buying ({sent.funds_increasing_positions} funds increasing)")

        if tech.price_above_sma_200:
            strengths.append("Price above 200-day moving average (long-term uptrend)")

        if result.competitor_analysis.pe_vs_peers == "discount":
            strengths.append("Trading at discount to peers")

        strengths.extend(result.competitor_analysis.competitive_advantages[:2])

        return strengths[:6]  # Limit to top 6

    def _identify_key_risks(self, result: GrowthAnalysisResult) -> List[str]:
        """Identify key risks"""
        risks = result.key_risks.copy()  # Start with any already identified

        risk_analysis = result.risk_analysis
        fin = result.financial_data
        sent = result.sentiment_data

        # Add top risks from each category
        risks.extend(risk_analysis.business_risks[:2])
        risks.extend(risk_analysis.financial_risks[:2])
        risks.extend(risk_analysis.market_risks[:1])

        # Add data completeness risk
        if result.data_completeness.completeness_score < 70:
            risks.append(f"Limited data availability ({result.data_completeness.completeness_score:.0f}% complete)")

        return risks[:6]  # Limit to top 6

    def _identify_catalysts(self, result: GrowthAnalysisResult) -> List[str]:
        """Identify potential catalysts"""
        catalysts = []

        fin = result.financial_data
        sent = result.sentiment_data

        if fin.revenue_yoy_growth > 0:
            catalysts.append("Continued revenue growth execution")

        if fin.net_margin < 0 and fin.net_margin > -10:
            catalysts.append("Path to profitability")

        if sent.analyst_buy_count > sent.analyst_hold_count:
            catalysts.append("Potential analyst upgrades")

        if result.upside_potential > 20:
            catalysts.append(f"Significant upside to price targets ({result.upside_potential:.1f}%)")

        catalysts.append("Earnings report and guidance")
        catalysts.append("Product launches or market expansion")

        return catalysts[:5]

    def _generate_monitoring_points(self, result: GrowthAnalysisResult) -> List[str]:
        """Generate monitoring recommendations"""
        points = [
            "Monitor quarterly earnings and guidance",
            "Track revenue growth trends",
            "Watch for changes in analyst recommendations",
            "Monitor institutional ownership changes"
        ]

        if result.risk_analysis.risk_score > 6:
            points.append("Closely monitor risk factors")

        if result.financial_data.debt_to_equity > 1.0:
            points.append("Track debt levels and interest coverage")

        if result.sentiment_data.short_interest > 10:
            points.append("Monitor short interest levels")

        return points[:6]

    async def _run_ai_analysis(
        self,
        result: GrowthAnalysisResult,
        market_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Generate AI-powered qualitative analysis"""

        try:
            # Prepare context
            context = f"""
Stock Analysis: {result.ticker} ({result.company_profile.name})
Sector: {result.company_profile.sector} | Industry: {result.company_profile.industry}

QUANTITATIVE SCORES:
- Fundamental Score: {result.fundamental_score:.1f}/10
- Sentiment Score: {result.sentiment_score:.1f}/10
- Technical Score: {result.technical_score:.1f}/10
- Competitive Score: {result.competitive_score:.1f}/10
- Risk-Adjusted Score: {result.risk_adjusted_score:.1f}/10
- Composite Score: {result.composite_score:.1f}/10

FINANCIAL METRICS:
- Revenue Growth: {result.financial_data.revenue_yoy_growth:.1f}% YoY
- Net Margin: {result.financial_data.net_margin:.1f}%
- FCF Margin: {result.financial_data.fcf_margin:.1f}%
- Debt/Equity: {result.financial_data.debt_to_equity:.2f}
- ROE: {result.financial_data.roe:.1f}%

SENTIMENT:
- Analyst Consensus: {result.sentiment_data.analyst_consensus}
- Price Target: ${result.sentiment_data.price_target_avg:.2f} (Current: ${result.technical_indicators.current_price:.2f})
- Institutional Ownership: {result.sentiment_data.institutional_ownership:.1f}%

RISKS:
- Risk Score: {result.risk_analysis.risk_score:.1f}/10 ({result.risk_analysis.risk_level})
- Business Risks: {', '.join(result.risk_analysis.business_risks[:2]) if result.risk_analysis.business_risks else 'None identified'}
- Financial Risks: {', '.join(result.risk_analysis.financial_risks[:2]) if result.risk_analysis.financial_risks else 'None identified'}

PRELIMINARY RECOMMENDATION: {result.recommendation.value} ({result.confidence_score:.0f}% confidence)
"""

            prompt = f"""You are a senior equity analyst. Analyze this growth stock and provide:

1. A concise 2-3 sentence investment summary
2. Detailed reasoning for the recommendation

{context}

Respond with JSON:
{{
    "summary": "2-3 sentence investment summary",
    "reasoning": "Detailed paragraph explaining the recommendation based on the data"
}}

Respond ONLY with valid JSON."""

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior financial analyst providing objective stock analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = response["message"]["content"]

            # Parse JSON
            import json
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                return data.get("summary", ""), data.get("reasoning", "")

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")

        return "", ""

    def _compile_data_sources(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track data source attribution"""
        return {
            "stock_info": stock_data.get("data_sources", {}).get("stock_info", {}),
            "fundamentals": stock_data.get("data_sources", {}).get("fundamentals", {}),
            "technicals": stock_data.get("data_sources", {}).get("technicals", {}),
            "peers": stock_data.get("data_sources", {}).get("peers", {}),
            "analysis_engine": {
                "type": "agent",
                "name": "growth_analysis_agent",
                "version": "1.0.0"
            }
        }
