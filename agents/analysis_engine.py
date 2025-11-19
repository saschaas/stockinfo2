"""Analysis Engine Agent for comprehensive stock analysis and recommendations."""

from typing import Any
from decimal import Decimal
import json

import ollama
import structlog

from backend.app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class AnalysisEngineAgent:
    """Agent for performing comprehensive stock analysis."""

    def __init__(self) -> None:
        self.model = settings.ollama_model

    async def analyze(
        self,
        ticker: str | None,
        stock_data: dict[str, Any],
        market_data: dict[str, Any],
        fund_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform comprehensive analysis on gathered data.

        Args:
            ticker: Stock ticker symbol
            stock_data: Data from Stock Research Agent
            market_data: Data from Market Sentiment Agent
            fund_data: Data from Investor Tracking Agent

        Returns:
            Comprehensive analysis results
        """
        logger.info("Analysis Engine Agent starting", ticker=ticker)

        result = {"ticker": ticker}

        # Calculate technical indicators
        if stock_data.get("historical_prices"):
            technical = self._calculate_technical_indicators(
                stock_data["historical_prices"]
            )
            result["technical_indicators"] = technical

        # Calculate valuation metrics
        valuation = self._calculate_valuation_metrics(stock_data)
        result["valuation_metrics"] = valuation

        # Analyze fund ownership
        if fund_data.get("ownership_summary"):
            ownership = self._analyze_fund_ownership(fund_data)
            result["fund_analysis"] = ownership

        # Generate peer comparison (simplified)
        peer_comparison = await self._generate_peer_comparison(ticker, stock_data)
        result["peer_comparison"] = peer_comparison

        # Calculate price target
        price_target = self._calculate_price_target(stock_data, valuation)
        result["target_price_6m"] = price_target

        # Run AI analysis for recommendation
        ai_analysis = await self._run_ai_analysis(
            ticker, stock_data, market_data, fund_data, result
        )
        result.update(ai_analysis)

        logger.info(
            "Analysis Engine Agent completed",
            ticker=ticker,
            recommendation=result.get("recommendation"),
        )

        return result

    def _calculate_technical_indicators(self, prices: list[dict]) -> dict[str, Any]:
        """Calculate technical indicators from price history."""
        if not prices or len(prices) < 20:
            return {}

        closes = [float(p["close"]) for p in prices]
        highs = [float(p["high"]) for p in prices]
        lows = [float(p["low"]) for p in prices]

        result = {}

        # RSI (14-day)
        if len(closes) >= 14:
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                gains.append(max(0, change))
                losses.append(max(0, -change))

            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                result["rsi"] = round(100 - (100 / (1 + rs)), 2)
            else:
                result["rsi"] = 100

        # Moving averages
        if len(closes) >= 20:
            result["sma_20"] = round(sum(closes[-20:]) / 20, 2)
        if len(closes) >= 50:
            result["sma_50"] = round(sum(closes[-50:]) / 50, 2)
        if len(closes) >= 200:
            result["sma_200"] = round(sum(closes[-200:]) / 200, 2)

        # MACD
        if len(closes) >= 26:
            ema_12 = self._calculate_ema(closes, 12)
            ema_26 = self._calculate_ema(closes, 26)
            macd = ema_12 - ema_26
            signal = self._calculate_ema([macd], 9) if len(closes) >= 35 else macd
            result["macd"] = round(macd, 4)
            result["macd_signal"] = round(signal, 4)

        # Bollinger Bands
        if len(closes) >= 20:
            sma = sum(closes[-20:]) / 20
            variance = sum((x - sma) ** 2 for x in closes[-20:]) / 20
            std = variance ** 0.5
            result["bollinger_upper"] = round(sma + 2 * std, 2)
            result["bollinger_lower"] = round(sma - 2 * std, 2)
            result["bollinger_middle"] = round(sma, 2)

        # Current price position
        current = closes[-1]
        result["current_price"] = current

        if "sma_20" in result:
            result["above_sma_20"] = current > result["sma_20"]
        if "sma_50" in result:
            result["above_sma_50"] = current > result["sma_50"]

        # RSI interpretation
        if "rsi" in result:
            rsi = result["rsi"]
            if rsi >= 70:
                result["rsi_signal"] = "overbought"
            elif rsi <= 30:
                result["rsi_signal"] = "oversold"
            else:
                result["rsi_signal"] = "neutral"

        return result

    def _calculate_ema(self, data: list, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return sum(data) / len(data) if data else 0

        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period

        for price in data[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _calculate_valuation_metrics(self, stock_data: dict[str, Any]) -> dict[str, Any]:
        """Calculate and interpret valuation metrics."""
        result = {}

        # P/E Analysis
        pe = stock_data.get("pe_ratio")
        if pe:
            pe_float = float(pe)
            result["pe_ratio"] = pe_float
            if pe_float < 15:
                result["pe_signal"] = "undervalued"
            elif pe_float < 25:
                result["pe_signal"] = "fair"
            else:
                result["pe_signal"] = "overvalued"

        # PEG Analysis
        peg = stock_data.get("peg_ratio")
        if peg:
            peg_float = float(peg)
            result["peg_ratio"] = peg_float
            if peg_float < 1:
                result["peg_signal"] = "undervalued"
            elif peg_float < 1.5:
                result["peg_signal"] = "fair"
            else:
                result["peg_signal"] = "overvalued"

        # Price to Book
        pb = stock_data.get("price_to_book")
        if pb:
            result["price_to_book"] = float(pb)

        # Debt to Equity
        de = stock_data.get("debt_to_equity")
        if de:
            de_float = float(de)
            result["debt_to_equity"] = de_float
            if de_float < 0.5:
                result["debt_signal"] = "low"
            elif de_float < 1:
                result["debt_signal"] = "moderate"
            else:
                result["debt_signal"] = "high"

        # Profit margins
        result["profit_margin"] = stock_data.get("profit_margin")
        result["operating_margin"] = stock_data.get("operating_margin")

        return result

    def _analyze_fund_ownership(self, fund_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze institutional fund ownership."""
        summary = fund_data.get("ownership_summary", [])

        if not summary:
            return {"institutional_interest": "none"}

        total_value = sum(f.get("value", 0) for f in summary)
        fund_count = len(summary)

        # Count by change type
        new_positions = sum(1 for f in summary if f.get("change_type") == "new")
        increased = sum(1 for f in summary if f.get("change_type") == "increased")
        decreased = sum(1 for f in summary if f.get("change_type") == "decreased")

        result = {
            "fund_count": fund_count,
            "total_value": total_value,
            "new_positions": new_positions,
            "increased_positions": increased,
            "decreased_positions": decreased,
        }

        # Determine sentiment
        if new_positions + increased > decreased:
            result["institutional_sentiment"] = "bullish"
        elif decreased > new_positions + increased:
            result["institutional_sentiment"] = "bearish"
        else:
            result["institutional_sentiment"] = "neutral"

        return result

    async def _generate_peer_comparison(
        self,
        ticker: str | None,
        stock_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate peer comparison data."""
        # In a full implementation, this would fetch peer data
        # For now, return placeholder
        return {
            "sector": stock_data.get("sector"),
            "industry": stock_data.get("industry"),
            "peers": [],  # Would be populated with actual peers
            "percentile_pe": None,
            "percentile_growth": None,
        }

    def _calculate_price_target(
        self,
        stock_data: dict[str, Any],
        valuation: dict[str, Any],
    ) -> float | None:
        """Calculate 6-month price target."""
        # Use analyst target if available
        analyst_target = stock_data.get("target_mean_price")
        if analyst_target:
            return float(analyst_target)

        # Fallback calculation based on valuation
        current_price = stock_data.get("current_price")
        if not current_price:
            return None

        current = float(current_price)

        # Simple adjustment based on valuation signals
        adjustment = 1.0

        pe_signal = valuation.get("pe_signal")
        if pe_signal == "undervalued":
            adjustment += 0.1
        elif pe_signal == "overvalued":
            adjustment -= 0.05

        peg_signal = valuation.get("peg_signal")
        if peg_signal == "undervalued":
            adjustment += 0.1
        elif peg_signal == "overvalued":
            adjustment -= 0.05

        return round(current * adjustment, 2)

    async def _run_ai_analysis(
        self,
        ticker: str | None,
        stock_data: dict[str, Any],
        market_data: dict[str, Any],
        fund_data: dict[str, Any],
        analysis_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run AI analysis for recommendation."""
        context = self._build_analysis_context(
            ticker, stock_data, market_data, fund_data, analysis_data
        )

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(),
                    },
                    {"role": "user", "content": context},
                ],
            )

            content = response["message"]["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])

        except Exception as e:
            logger.error("AI analysis failed", error=str(e))

        return {
            "recommendation": "hold",
            "confidence_score": 0.5,
            "recommendation_reasoning": "Unable to complete AI analysis.",
            "risks": [],
            "opportunities": [],
        }

    def _build_analysis_context(
        self,
        ticker: str | None,
        stock_data: dict[str, Any],
        market_data: dict[str, Any],
        fund_data: dict[str, Any],
        analysis_data: dict[str, Any],
    ) -> str:
        """Build context for AI analysis."""
        context = f"""Analyze {ticker} and provide an investment recommendation.

## Company Information
- Name: {stock_data.get('company_name', 'Unknown')}
- Sector: {stock_data.get('sector', 'Unknown')}
- Industry: {stock_data.get('industry', 'Unknown')}
- Market Cap: ${stock_data.get('market_cap', 0):,}

## Current Price
- Price: ${stock_data.get('current_price', 'N/A')}
- Target (6m): ${analysis_data.get('target_price_6m', 'N/A')}

## Valuation
"""
        valuation = analysis_data.get("valuation_metrics", {})
        context += f"- P/E Ratio: {valuation.get('pe_ratio', 'N/A')} ({valuation.get('pe_signal', 'N/A')})\n"
        context += f"- PEG Ratio: {valuation.get('peg_ratio', 'N/A')} ({valuation.get('peg_signal', 'N/A')})\n"
        context += f"- Debt/Equity: {valuation.get('debt_to_equity', 'N/A')} ({valuation.get('debt_signal', 'N/A')})\n"

        context += "\n## Technical Indicators\n"
        technical = analysis_data.get("technical_indicators", {})
        context += f"- RSI: {technical.get('rsi', 'N/A')} ({technical.get('rsi_signal', 'N/A')})\n"
        context += f"- Above 20 SMA: {technical.get('above_sma_20', 'N/A')}\n"
        context += f"- Above 50 SMA: {technical.get('above_sma_50', 'N/A')}\n"

        context += "\n## Fund Ownership\n"
        fund_analysis = analysis_data.get("fund_analysis", {})
        context += f"- Funds Holding: {fund_analysis.get('fund_count', 0)}\n"
        context += f"- Institutional Sentiment: {fund_analysis.get('institutional_sentiment', 'unknown')}\n"

        context += "\n## Market Context\n"
        context += f"- Overall Market Sentiment: {market_data.get('overall_sentiment', 'N/A')}\n"

        return context

    def _get_system_prompt(self) -> str:
        """Get system prompt for analysis."""
        return """You are a senior financial analyst providing objective investment recommendations.

Analyze the provided data and generate a comprehensive investment recommendation.

Your response must be valid JSON:
{
    "recommendation": "<strong_buy|buy|hold|sell|strong_sell>",
    "confidence_score": <0.0-1.0>,
    "recommendation_reasoning": "<2-3 sentence explanation>",
    "risks": ["risk1", "risk2", "risk3"],
    "opportunities": ["opportunity1", "opportunity2", "opportunity3"]
}

Consider:
- Valuation metrics and their signals
- Technical indicator positions
- Institutional ownership trends
- Overall market conditions
- Company fundamentals

Be objective and data-driven. Provide specific, actionable insights.
Respond ONLY with valid JSON."""
