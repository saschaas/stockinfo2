"""
Risk Assessment Agent for Stock Investment Decisions

Analyzes all available stock research data to produce:
- A 0-100 risk score (higher = lower risk, better entry)
- Investment decision recommendation
- Risk/Reward analysis
- Entry, stop, and target levels

Based on the four-layer risk assessment framework:
1. Market Structure Risk (Support, Resistance, Trend)
2. Momentum & Indicator Risk
3. Volatility & Position-Sizing Risk
4. Volume Confirmation Risk

With Multi-Timeframe Alignment (MFTA) multiplier for signal quality.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SubscoreBreakdown:
    """Detailed breakdown of subscores"""
    # Market Structure (40% weight)
    support_proximity_score: float = 0.0  # 0-40
    resistance_distance_score: float = 0.0  # 0-40
    trend_alignment_score: float = 0.0  # 0-20
    market_structure_total: float = 0.0  # 0-100

    # Momentum (20% weight)
    macd_momentum_score: float = 0.0  # 0-10
    rsi_direction_score: float = 0.0  # 0-10
    momentum_total: float = 0.0  # 0-20

    # Overextension Penalty (15% weight, negative)
    rsi_overbought_penalty: float = 0.0  # 0-100
    bollinger_penalty: float = 0.0  # 0-100
    ema_distance_penalty: float = 0.0  # 0-100
    overextension_total: float = 0.0  # 0-100

    # Volatility Penalty (15% weight, negative)
    atr_volatility_penalty: float = 0.0  # 0-100
    stop_distance_penalty: float = 0.0  # 0-100
    volatility_total: float = 0.0  # 0-100

    # Volume Confirmation (20% weight)
    volume_ratio_score: float = 0.0  # 0-20
    volume_total: float = 0.0  # 0-20


@dataclass
class RiskRewardAnalysis:
    """Risk/Reward calculation"""
    current_price: float = 0.0
    nearest_support: float = 0.0
    nearest_resistance: float = 0.0
    risk_distance_pct: float = 0.0  # Distance to support (%)
    reward_distance_pct: float = 0.0  # Distance to resistance (%)
    risk_reward_ratio: float = 0.0
    is_favorable: bool = False  # True if reward >= 2x risk
    suggested_entry: Optional[float] = None
    suggested_stop: float = 0.0  # 2x ATR below support
    suggested_target: float = 0.0


@dataclass
class RiskAssessmentResult:
    """Complete risk assessment output"""
    ticker: str
    assessment_date: datetime = field(default_factory=datetime.now)
    current_price: float = 0.0

    # Main Risk Score (0-100, higher = lower risk)
    risk_score: float = 50.0
    risk_level: str = "medium"  # "low", "medium", "elevated", "high"

    # Weighted subscores (final contribution)
    market_structure_weighted: float = 0.0  # 0-40
    momentum_weighted: float = 0.0  # 0-20
    overextension_penalty_weighted: float = 0.0  # 0-15 (negative impact)
    volatility_penalty_weighted: float = 0.0  # 0-15 (negative impact)
    volume_confirmation_weighted: float = 0.0  # 0-20

    # Raw subscores
    subscore_breakdown: SubscoreBreakdown = field(default_factory=SubscoreBreakdown)

    # MFTA (Multi-Timeframe Analysis)
    mfta_multiplier: float = 1.0  # 0.5, 0.8, 1.0, 1.2
    mfta_alignment: str = "neutral"  # aligned_bullish, aligned_bearish, mixed, neutral
    pre_mfta_score: float = 50.0  # Score before MFTA adjustment

    # Risk/Reward Analysis
    risk_reward: RiskRewardAnalysis = field(default_factory=RiskRewardAnalysis)

    # Investment Decision
    investment_decision: str = "HOLD"  # "BUY", "HOLD", "AVOID", "SELL"
    decision_confidence: float = 50.0  # 0-100
    entry_quality: str = "fair"  # "excellent", "good", "fair", "poor"

    # Key Factors Summary
    bullish_factors: List[str] = field(default_factory=list)
    bearish_factors: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)

    # Detailed Analysis
    summary: str = ""  # 2-3 sentence summary
    detailed_analysis: str = ""  # Full analysis

    # Position Sizing
    position_sizing_suggestion: str = ""  # Based on ATR

    # Data Sources
    data_sources: Dict[str, Any] = field(default_factory=dict)


class RiskAssessmentAgent:
    """
    Risk Assessment Agent that combines all stock research data
    to produce an investment decision with risk scoring.
    """

    def __init__(self):
        """Initialize the risk assessment agent"""
        # Scoring weights (from scoring values.json)
        self.weights = {
            "market_structure": 0.40,
            "momentum": 0.20,
            "overextension": -0.15,  # Negative weight (penalty)
            "volatility": -0.15,  # Negative weight (penalty)
            "volume": 0.20
        }

        # MFTA multipliers
        self.mfta_multipliers = {
            "aligned_bullish": 1.2,
            "aligned_bearish": 0.5,
            "mixed": 0.8,
            "neutral": 1.0
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def analyze(
        self,
        ticker: str,
        technical_analysis: Optional[Dict[str, Any]] = None,
        growth_analysis: Optional[Dict[str, Any]] = None,
        stock_info: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessmentResult:
        """
        Perform comprehensive risk assessment

        Args:
            ticker: Stock ticker symbol
            technical_analysis: Technical analysis result dictionary
            growth_analysis: Growth analysis result dictionary
            stock_info: Basic stock info from Yahoo Finance

        Returns:
            RiskAssessmentResult with complete risk assessment
        """
        logger.info("Starting risk assessment", ticker=ticker)

        result = RiskAssessmentResult(ticker=ticker.upper())

        # Validate we have at least technical analysis data
        if not technical_analysis:
            logger.warning("No technical analysis data for risk assessment", ticker=ticker)
            result.summary = "Insufficient data for risk assessment."
            result.investment_decision = "HOLD"
            return result

        # Get current price
        result.current_price = self._safe_float(
            technical_analysis.get("current_price", 0)
        )

        # Step 1: Calculate Market Structure Score (40%)
        result.subscore_breakdown = self._calculate_subscores(
            technical_analysis, growth_analysis, stock_info
        )

        # Step 2: Apply weights to calculate pre-MFTA score
        result.market_structure_weighted = (
            result.subscore_breakdown.market_structure_total *
            self.weights["market_structure"]
        )
        result.momentum_weighted = (
            result.subscore_breakdown.momentum_total *
            self.weights["momentum"] * 5  # Scale 0-20 to 0-100
        )
        result.overextension_penalty_weighted = (
            result.subscore_breakdown.overextension_total *
            abs(self.weights["overextension"])
        )
        result.volatility_penalty_weighted = (
            result.subscore_breakdown.volatility_total *
            abs(self.weights["volatility"])
        )
        result.volume_confirmation_weighted = (
            result.subscore_breakdown.volume_total *
            self.weights["volume"] * 5  # Scale 0-20 to 0-100
        )

        # Calculate base score
        result.pre_mfta_score = (
            result.market_structure_weighted +
            result.momentum_weighted +
            result.volume_confirmation_weighted -
            result.overextension_penalty_weighted -
            result.volatility_penalty_weighted
        )
        result.pre_mfta_score = max(0, min(100, result.pre_mfta_score))

        # Step 3: Apply MFTA multiplier
        mfta_data = technical_analysis.get("multi_timeframe", {})
        result.mfta_alignment = mfta_data.get("trend_alignment", "neutral")
        result.mfta_multiplier = self.mfta_multipliers.get(
            result.mfta_alignment, 1.0
        )

        result.risk_score = result.pre_mfta_score * result.mfta_multiplier
        result.risk_score = max(0, min(100, result.risk_score))

        # Step 4: Determine risk level
        result.risk_level = self._determine_risk_level(result.risk_score)

        # Step 5: Calculate risk/reward analysis
        result.risk_reward = self._calculate_risk_reward(
            technical_analysis, result.current_price
        )

        # Step 6: Generate investment decision
        result.investment_decision, result.decision_confidence, result.entry_quality = (
            self._generate_investment_decision(result, growth_analysis)
        )

        # Step 7: Identify key factors
        result.bullish_factors = self._identify_bullish_factors(
            technical_analysis, growth_analysis
        )
        result.bearish_factors = self._identify_bearish_factors(
            technical_analysis, growth_analysis
        )
        result.key_risks = self._identify_key_risks(
            technical_analysis, growth_analysis
        )

        # Step 8: Generate position sizing suggestion
        result.position_sizing_suggestion = self._generate_position_sizing(
            technical_analysis, result.current_price
        )

        # Step 9: Generate summary and detailed analysis
        result.summary = self._generate_summary(result)
        result.detailed_analysis = self._generate_detailed_analysis(result)

        # Step 10: Track data sources
        result.data_sources = {
            "technical_analysis": {"type": "agent", "name": "technical_analysis_agent"},
            "growth_analysis": {"type": "agent", "name": "growth_analysis_agent"} if growth_analysis else None,
            "risk_assessment": {"type": "agent", "name": "risk_assessment_agent", "version": "1.0.0"}
        }

        logger.info(
            "Risk assessment completed",
            ticker=ticker,
            risk_score=round(result.risk_score, 1),
            risk_level=result.risk_level,
            decision=result.investment_decision
        )

        return result

    def _calculate_subscores(
        self,
        technical: Dict[str, Any],
        growth: Optional[Dict[str, Any]],
        stock_info: Optional[Dict[str, Any]]
    ) -> SubscoreBreakdown:
        """Calculate all subscores based on scoring values.json"""
        breakdown = SubscoreBreakdown()

        # === Market Structure (40% weight) ===

        # Support Proximity Score (0-40)
        support_distance = self._safe_float(
            technical.get("support_distance_pct", 10)
        )
        if support_distance <= 2:
            breakdown.support_proximity_score = 40
        elif support_distance <= 5:
            breakdown.support_proximity_score = 30
        elif support_distance <= 8:
            breakdown.support_proximity_score = 20
        elif support_distance <= 12:
            breakdown.support_proximity_score = 10
        else:
            breakdown.support_proximity_score = 0

        # Resistance Distance Score (0-40)
        resistance_distance = self._safe_float(
            technical.get("resistance_distance_pct", 5)
        )
        if resistance_distance >= 10:
            breakdown.resistance_distance_score = 40
        elif resistance_distance >= 7:
            breakdown.resistance_distance_score = 30
        elif resistance_distance >= 4:
            breakdown.resistance_distance_score = 20
        elif resistance_distance >= 2:
            breakdown.resistance_distance_score = 10
        else:
            breakdown.resistance_distance_score = 0

        # Trend Alignment Score (0-20)
        trend_score = 0

        # SMA50 above SMA200 (golden cross equivalent)
        sma_50 = self._safe_float(technical.get("sma_50", 0))
        sma_200 = self._safe_float(technical.get("sma_200", 0))
        if sma_50 > sma_200 and sma_200 > 0:
            trend_score += 10

        # MACD above zero
        macd = self._safe_float(technical.get("macd", 0))
        if macd > 0:
            trend_score += 5

        # ADX above 20 (strong trend)
        adx = self._safe_float(technical.get("adx", 0))
        if adx > 20:
            trend_score += 5

        breakdown.trend_alignment_score = trend_score

        breakdown.market_structure_total = (
            breakdown.support_proximity_score +
            breakdown.resistance_distance_score +
            breakdown.trend_alignment_score
        )

        # === Momentum (20% weight) ===

        # MACD Momentum Score (0-10)
        macd_hist = self._safe_float(technical.get("macd_histogram", 0))
        macd_cross = technical.get("macd_cross")

        # Check if histogram is rising (we need to infer from cross signal)
        if macd_hist > 0:
            if macd_cross == "bullish":
                breakdown.macd_momentum_score = 10  # Positive and rising
            else:
                breakdown.macd_momentum_score = 7  # Positive
        elif macd_hist < 0:
            # Negative but potentially rising (bearish turning bullish)
            if macd_cross == "bullish":
                breakdown.macd_momentum_score = 4  # Negative but rising
            else:
                breakdown.macd_momentum_score = 0

        # RSI Direction Score (0-10)
        rsi = self._safe_float(technical.get("rsi", 50))
        rsi_signal = technical.get("rsi_signal", "neutral")
        rsi_weighted = technical.get("rsi_weighted_signal", "neutral")

        # Determine RSI score based on level and trend context
        if 40 <= rsi <= 60:
            breakdown.rsi_direction_score = 10  # Neutral zone, potentially rising
        elif rsi < 40:
            if rsi_signal == "oversold":
                breakdown.rsi_direction_score = 7  # Oversold, potential bounce
            else:
                breakdown.rsi_direction_score = 5
        elif rsi > 60:
            if rsi_weighted == "neutral_in_uptrend":
                breakdown.rsi_direction_score = 7  # Overbought but in strong trend
            else:
                breakdown.rsi_direction_score = 5

        breakdown.momentum_total = (
            breakdown.macd_momentum_score +
            breakdown.rsi_direction_score
        )

        # === Overextension Penalty (15% weight) ===

        # RSI Overbought Penalty (0-100)
        if rsi > 80:
            breakdown.rsi_overbought_penalty = 100
        elif rsi > 70:
            breakdown.rsi_overbought_penalty = 60
        else:
            breakdown.rsi_overbought_penalty = 0

        # Bollinger Band Penalty (0-100)
        price_position = technical.get("price_position", "middle")
        if price_position == "above_upper":
            breakdown.bollinger_penalty = 60
        elif price_position == "upper":
            breakdown.bollinger_penalty = 30
        else:
            breakdown.bollinger_penalty = 0

        # Distance Above EMA20 Penalty (0-100)
        current_price = self._safe_float(technical.get("current_price", 0))
        sma_20 = self._safe_float(technical.get("sma_20", 0))
        if current_price > 0 and sma_20 > 0:
            ema_distance_pct = ((current_price - sma_20) / sma_20) * 100
            if ema_distance_pct > 8:
                breakdown.ema_distance_penalty = 100
            elif ema_distance_pct > 5:
                breakdown.ema_distance_penalty = 50
            elif ema_distance_pct > 2:
                breakdown.ema_distance_penalty = 20
            else:
                breakdown.ema_distance_penalty = 0

        # Aggregate overextension penalty (weighted average)
        breakdown.overextension_total = (
            breakdown.rsi_overbought_penalty * 0.5 +
            breakdown.bollinger_penalty * 0.3 +
            breakdown.ema_distance_penalty * 0.2
        )

        # === Volatility Penalty (15% weight) ===

        # ATR Volatility Penalty (0-100)
        atr_percent = self._safe_float(technical.get("atr_percent", 3))
        if atr_percent > 6:
            breakdown.atr_volatility_penalty = 100
        elif atr_percent > 4:
            breakdown.atr_volatility_penalty = 60
        elif atr_percent > 2:
            breakdown.atr_volatility_penalty = 30
        else:
            breakdown.atr_volatility_penalty = 0

        # Stop Distance Penalty (based on 2x ATR)
        atr = self._safe_float(technical.get("atr", 0))
        if current_price > 0 and atr > 0:
            stop_distance_pct = (2 * atr / current_price) * 100
            if stop_distance_pct > 8:
                breakdown.stop_distance_penalty = 100
            elif stop_distance_pct > 5:
                breakdown.stop_distance_penalty = 60
            elif stop_distance_pct > 3:
                breakdown.stop_distance_penalty = 30
            else:
                breakdown.stop_distance_penalty = 0

        # Aggregate volatility penalty
        breakdown.volatility_total = (
            breakdown.atr_volatility_penalty * 0.6 +
            breakdown.stop_distance_penalty * 0.4
        )

        # === Volume Confirmation (20% weight) ===

        volume_ratio = self._safe_float(technical.get("volume_ratio", 1.0))
        if volume_ratio >= 2.0:
            breakdown.volume_ratio_score = 20
        elif volume_ratio >= 1.5:
            breakdown.volume_ratio_score = 15
        elif volume_ratio >= 1.0:
            breakdown.volume_ratio_score = 10
        elif volume_ratio >= 0.8:
            breakdown.volume_ratio_score = 5
        else:
            breakdown.volume_ratio_score = 0

        breakdown.volume_total = breakdown.volume_ratio_score

        return breakdown

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score >= 80:
            return "low"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "elevated"
        else:
            return "high"

    def _calculate_risk_reward(
        self,
        technical: Dict[str, Any],
        current_price: float
    ) -> RiskRewardAnalysis:
        """Calculate risk/reward metrics"""
        rr = RiskRewardAnalysis()
        rr.current_price = current_price

        # Get support and resistance levels
        rr.nearest_support = self._safe_float(
            technical.get("nearest_support", 0)
        )
        rr.nearest_resistance = self._safe_float(
            technical.get("nearest_resistance", 0)
        )

        # Use support levels if nearest not available
        if rr.nearest_support == 0:
            support_levels = technical.get("support_levels", [])
            if support_levels:
                rr.nearest_support = support_levels[0]

        if rr.nearest_resistance == 0:
            resistance_levels = technical.get("resistance_levels", [])
            if resistance_levels:
                rr.nearest_resistance = resistance_levels[0]

        # Calculate percentages
        if current_price > 0 and rr.nearest_support > 0:
            rr.risk_distance_pct = ((current_price - rr.nearest_support) / current_price) * 100

        if current_price > 0 and rr.nearest_resistance > 0:
            rr.reward_distance_pct = ((rr.nearest_resistance - current_price) / current_price) * 100

        # Calculate risk/reward ratio
        if rr.risk_distance_pct > 0:
            rr.risk_reward_ratio = rr.reward_distance_pct / rr.risk_distance_pct
        else:
            rr.risk_reward_ratio = 0

        rr.is_favorable = rr.risk_reward_ratio >= 2.0

        # Calculate entry, stop, target
        atr = self._safe_float(technical.get("atr", 0))

        # Suggested entry near support (within 2%)
        if rr.nearest_support > 0:
            rr.suggested_entry = rr.nearest_support * 1.01  # 1% above support

        # Stop loss at 2x ATR below support
        if rr.nearest_support > 0 and atr > 0:
            rr.suggested_stop = rr.nearest_support - (2 * atr)
        elif rr.nearest_support > 0:
            rr.suggested_stop = rr.nearest_support * 0.97  # 3% below support

        # Target at nearest resistance
        rr.suggested_target = rr.nearest_resistance

        return rr

    def _generate_investment_decision(
        self,
        result: RiskAssessmentResult,
        growth: Optional[Dict[str, Any]]
    ) -> tuple[str, float, str]:
        """Generate investment decision based on risk score and other factors"""

        score = result.risk_score
        rr_favorable = result.risk_reward.is_favorable
        rr_ratio = result.risk_reward.risk_reward_ratio

        # Determine entry quality
        if score >= 80 and rr_favorable:
            entry_quality = "excellent"
        elif score >= 60 and rr_ratio >= 1.5:
            entry_quality = "good"
        elif score >= 40:
            entry_quality = "fair"
        else:
            entry_quality = "poor"

        # Determine decision
        if score >= 80 and rr_favorable:
            decision = "BUY"
            base_confidence = 85
        elif score >= 70 and rr_ratio >= 1.5:
            decision = "BUY"
            base_confidence = 75
        elif score >= 60:
            if rr_favorable:
                decision = "BUY"
                base_confidence = 65
            else:
                decision = "HOLD"
                base_confidence = 60
        elif score >= 40:
            decision = "HOLD"
            base_confidence = 55
        elif score >= 20:
            decision = "AVOID"
            base_confidence = 60
        else:
            decision = "SELL"
            base_confidence = 70

        # Adjust confidence based on MFTA
        mfta_adjustment = 0
        if result.mfta_alignment == "aligned_bullish" and decision in ["BUY", "HOLD"]:
            mfta_adjustment = 10
        elif result.mfta_alignment == "aligned_bearish" and decision in ["AVOID", "SELL"]:
            mfta_adjustment = 10
        elif result.mfta_alignment == "mixed":
            mfta_adjustment = -5

        # Adjust confidence based on growth analysis if available
        growth_adjustment = 0
        if growth:
            growth_score = self._safe_float(growth.get("composite_score", 5))
            if growth_score >= 7:
                growth_adjustment = 5
            elif growth_score <= 4:
                growth_adjustment = -5

        confidence = min(95, max(30, base_confidence + mfta_adjustment + growth_adjustment))

        return decision, confidence, entry_quality

    def _identify_bullish_factors(
        self,
        technical: Dict[str, Any],
        growth: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify bullish factors from the analysis"""
        factors = []

        # Technical factors
        if technical.get("price_above_sma_200"):
            factors.append("Price above 200-day moving average (long-term uptrend)")

        if technical.get("golden_cross"):
            factors.append("Golden cross pattern (SMA 50 > SMA 200)")

        if technical.get("macd_cross") == "bullish":
            factors.append("Bullish MACD crossover")

        if technical.get("rsi_signal") == "oversold":
            factors.append("RSI indicates oversold conditions (potential bounce)")

        trend_direction = technical.get("trend_direction", "")
        if trend_direction == "bullish":
            factors.append("Overall trend direction is bullish")

        if technical.get("volume_signal") in ["high", "very_high"]:
            factors.append("Strong volume confirmation")

        if technical.get("obv_trend") == "rising":
            factors.append("On-Balance Volume trending up (accumulation)")

        # Multi-timeframe
        mfta = technical.get("multi_timeframe", {})
        if mfta.get("trend_alignment") == "aligned_bullish":
            factors.append("All timeframes aligned bullish (high confidence)")

        # Growth factors
        if growth:
            if self._safe_float(growth.get("upside_potential", 0)) > 20:
                factors.append(f"Significant upside potential ({growth.get('upside_potential', 0):.1f}%)")

            strengths = growth.get("key_strengths", [])
            factors.extend(strengths[:2])  # Add top 2 strengths

        return factors[:8]  # Limit to 8 factors

    def _identify_bearish_factors(
        self,
        technical: Dict[str, Any],
        growth: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify bearish factors from the analysis"""
        factors = []

        # Technical factors
        if not technical.get("price_above_sma_200"):
            factors.append("Price below 200-day moving average (long-term downtrend)")

        if technical.get("death_cross"):
            factors.append("Death cross pattern (SMA 50 < SMA 200)")

        if technical.get("macd_cross") == "bearish":
            factors.append("Bearish MACD crossover")

        if technical.get("rsi_signal") == "overbought":
            rsi = self._safe_float(technical.get("rsi", 50))
            factors.append(f"RSI overbought at {rsi:.1f} (pullback risk)")

        if technical.get("price_position") in ["above_upper", "upper"]:
            factors.append("Price extended above Bollinger Bands")

        if technical.get("volume_signal") == "low":
            factors.append("Low volume (weak conviction)")

        if technical.get("obv_trend") == "falling":
            factors.append("On-Balance Volume declining (distribution)")

        # Multi-timeframe
        mfta = technical.get("multi_timeframe", {})
        if mfta.get("trend_alignment") == "aligned_bearish":
            factors.append("All timeframes aligned bearish (high risk)")
        elif mfta.get("trend_alignment") == "mixed":
            factors.append("Mixed timeframe signals (uncertain direction)")

        # Growth factors
        if growth:
            risk_score = self._safe_float(growth.get("risk_score", 5))
            if risk_score > 7:
                factors.append(f"Elevated risk score: {risk_score:.1f}/10")

            risks = growth.get("key_risks", [])
            factors.extend(risks[:2])  # Add top 2 risks

        return factors[:8]  # Limit to 8 factors

    def _identify_key_risks(
        self,
        technical: Dict[str, Any],
        growth: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify key investment risks"""
        risks = []

        # Volatility risks
        volatility_level = technical.get("volatility_level", "moderate")
        if volatility_level in ["high", "very_high"]:
            atr_pct = self._safe_float(technical.get("atr_percent", 0))
            risks.append(f"High volatility (ATR: {atr_pct:.1f}% of price)")

        # Beta risk
        beta_analysis = technical.get("beta_analysis", {})
        beta = self._safe_float(beta_analysis.get("beta", 1.0))
        if beta > 1.5:
            risks.append(f"High market sensitivity (Beta: {beta:.2f})")

        # Support risk
        support_distance = self._safe_float(technical.get("support_distance_pct", 0))
        if support_distance > 10:
            risks.append(f"Far from support ({support_distance:.1f}% downside to support)")

        # Resistance risk
        resistance_distance = self._safe_float(technical.get("resistance_distance_pct", 0))
        if resistance_distance < 3:
            risks.append("Near resistance level (limited upside)")

        # Trend strength risk
        adx = self._safe_float(technical.get("adx", 0))
        if adx < 20:
            risks.append("Weak trend (ADX < 20), increased whipsaw risk")

        # Growth analysis risks
        if growth:
            data_completeness = self._safe_float(growth.get("data_completeness_score", 100))
            if data_completeness < 70:
                risks.append(f"Limited data availability ({data_completeness:.0f}% complete)")

            growth_risks = growth.get("key_risks", [])
            risks.extend(growth_risks[:3])

        return risks[:6]  # Limit to 6 risks

    def _generate_position_sizing(
        self,
        technical: Dict[str, Any],
        current_price: float
    ) -> str:
        """Generate position sizing suggestion based on volatility"""
        atr = self._safe_float(technical.get("atr", 0))
        atr_percent = self._safe_float(technical.get("atr_percent", 3))

        if atr_percent > 6:
            return "Small position size recommended (high volatility). Consider 1-2% portfolio risk."
        elif atr_percent > 4:
            return "Moderate position size recommended. Consider 2-3% portfolio risk."
        elif atr_percent > 2:
            return "Standard position size acceptable. Consider 3-5% portfolio risk."
        else:
            return "Larger position size possible (low volatility). Consider up to 5-7% portfolio risk."

    def _generate_summary(self, result: RiskAssessmentResult) -> str:
        """Generate 2-3 sentence summary"""
        decision = result.investment_decision
        score = result.risk_score
        level = result.risk_level
        rr = result.risk_reward.risk_reward_ratio
        entry = result.entry_quality

        summaries = []

        # Risk assessment summary
        if level == "low":
            summaries.append(f"Technical risk assessment shows favorable conditions with a score of {score:.0f}/100.")
        elif level == "medium":
            summaries.append(f"Technical risk assessment indicates moderate conditions with a score of {score:.0f}/100.")
        elif level == "elevated":
            summaries.append(f"Technical risk assessment shows elevated risk with a score of {score:.0f}/100.")
        else:
            summaries.append(f"Technical risk assessment indicates high risk with a score of {score:.0f}/100.")

        # Risk/Reward
        if rr >= 2.0:
            summaries.append(f"Risk/reward ratio of 1:{rr:.1f} is favorable for entry.")
        elif rr >= 1.0:
            summaries.append(f"Risk/reward ratio of 1:{rr:.1f} is acceptable but not ideal.")
        else:
            summaries.append(f"Risk/reward ratio of 1:{rr:.1f} is unfavorable - limited upside vs downside.")

        # Decision
        if decision == "BUY":
            summaries.append(f"Entry quality is {entry} - consider accumulating positions.")
        elif decision == "HOLD":
            summaries.append("Recommend holding current positions and monitoring for better entry.")
        elif decision == "AVOID":
            summaries.append("Recommend avoiding new positions until conditions improve.")
        else:
            summaries.append("Recommend reducing exposure due to unfavorable risk profile.")

        return " ".join(summaries)

    def _generate_detailed_analysis(self, result: RiskAssessmentResult) -> str:
        """Generate detailed analysis paragraph"""
        breakdown = result.subscore_breakdown
        mfta = result.mfta_alignment
        rr = result.risk_reward

        parts = []

        # Market structure analysis
        market_assessment = ""
        if breakdown.market_structure_total >= 70:
            market_assessment = "Market structure is strong"
        elif breakdown.market_structure_total >= 50:
            market_assessment = "Market structure is moderate"
        else:
            market_assessment = "Market structure is weak"

        parts.append(f"{market_assessment} with a score of {breakdown.market_structure_total:.0f}/100. "
                    f"Price proximity to support contributes {breakdown.support_proximity_score:.0f} points, "
                    f"while distance to resistance adds {breakdown.resistance_distance_score:.0f} points.")

        # Momentum analysis
        if breakdown.momentum_total >= 15:
            parts.append(f"Momentum indicators are bullish (score: {breakdown.momentum_total:.0f}/20).")
        elif breakdown.momentum_total >= 10:
            parts.append(f"Momentum is neutral to slightly positive (score: {breakdown.momentum_total:.0f}/20).")
        else:
            parts.append(f"Momentum is weak or negative (score: {breakdown.momentum_total:.0f}/20).")

        # Penalties
        total_penalty = breakdown.overextension_total + breakdown.volatility_total
        if total_penalty > 100:
            parts.append(f"Significant penalties applied for overextension ({breakdown.overextension_total:.0f}) "
                        f"and volatility ({breakdown.volatility_total:.0f}).")
        elif total_penalty > 50:
            parts.append(f"Moderate penalties for market conditions reduce the score.")

        # MFTA
        if mfta == "aligned_bullish":
            parts.append("Multi-timeframe analysis confirms bullish alignment across daily, hourly, and intraday charts, "
                        "applying a 1.2x confidence multiplier.")
        elif mfta == "aligned_bearish":
            parts.append("Multi-timeframe analysis shows bearish alignment, applying a 0.5x penalty multiplier.")
        elif mfta == "mixed":
            parts.append("Timeframe signals are mixed, suggesting caution with a 0.8x adjustment.")

        # Risk/Reward
        if rr.is_favorable:
            parts.append(f"With support at ${rr.nearest_support:.2f} and resistance at ${rr.nearest_resistance:.2f}, "
                        f"the risk/reward ratio of 1:{rr.risk_reward_ratio:.1f} supports potential entry.")
        else:
            parts.append(f"Current risk/reward of 1:{rr.risk_reward_ratio:.1f} suggests waiting for a better entry point.")

        return " ".join(parts)
