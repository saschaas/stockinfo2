"""
Technical Analysis Agent for Growth Stocks

Implements 11 technical indicators with weighted scoring optimized for growth stocks:
- Trend: SMA (20/50/200), EMA, ADX
- Momentum: RSI, MACD, Stochastic, ROC
- Volatility: Bollinger Bands, ATR
- Volume: OBV, Volume Analysis
- Support/Resistance: Pivot Points, auto-detected levels

Based on backtesting studies showing RSI (97% win-rate), Bollinger Bands, and MACD
are the most reliable indicators for growth stock analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import logging

import pandas as pd
import numpy as np

# Note: pandas_ta is not easily available in PyPI, so we'll use built-in calculations
ta = None

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TrendAnalysis:
    """Trend indicators and signals"""
    # Moving averages
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0

    # Trend signals
    price_above_sma_20: bool = False
    price_above_sma_50: bool = False
    price_above_sma_200: bool = False
    golden_cross: bool = False  # SMA 50 > SMA 200
    death_cross: bool = False   # SMA 50 < SMA 200

    # ADX (Average Directional Index)
    adx: float = 0.0
    adx_signal: str = "weak"  # "weak", "moderate", "strong", "very_strong"
    trend_direction: str = "neutral"  # "bullish", "bearish", "neutral"
    trend_strength_score: float = 0.0  # 0-10


@dataclass
class MomentumAnalysis:
    """Momentum indicators and signals"""
    # RSI (Relative Strength Index)
    rsi: float = 50.0
    rsi_signal: str = "neutral"  # "oversold", "neutral", "overbought"
    rsi_divergence: Optional[str] = None  # "bullish", "bearish", None
    rsi_weighted_signal: str = "neutral"  # Trend-context adjusted signal
    rsi_weight: float = 1.0  # Weight applied based on trend context

    # MACD
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_cross: Optional[str] = None  # "bullish", "bearish", None

    # Stochastic Oscillator
    stoch_k: float = 50.0
    stoch_d: float = 50.0
    stoch_signal: str = "neutral"

    # Rate of Change
    roc: float = 0.0
    roc_signal: str = "neutral"

    momentum_score: float = 0.0  # 0-10


@dataclass
class VolatilityAnalysis:
    """Volatility indicators"""
    # Bollinger Bands (2.5σ for growth stocks)
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    bb_signal: str = "neutral"  # "squeeze", "breakout_upper", "breakout_lower", "neutral"
    price_position: str = "middle"  # "above_upper", "upper", "middle", "lower", "below_lower"

    # ATR (Average True Range)
    atr: float = 0.0
    atr_percent: float = 0.0  # ATR as % of price
    volatility_level: str = "moderate"  # "low", "moderate", "high", "very_high"

    volatility_score: float = 0.0  # 0-10


@dataclass
class VolumeAnalysis:
    """Volume indicators"""
    # Current volume metrics
    current_volume: int = 0
    avg_volume_20d: int = 0
    volume_ratio: float = 1.0  # Current vs 20-day average
    volume_signal: str = "normal"  # "low", "normal", "high", "very_high"

    # OBV (On-Balance Volume)
    obv: float = 0.0
    obv_trend: str = "neutral"  # "rising", "falling", "neutral"

    # Volume-Price Trend
    vpt: float = 0.0

    volume_score: float = 0.0  # 0-10


@dataclass
class SupportResistanceAnalysis:
    """Support and resistance levels"""
    # Pivot points
    pivot: float = 0.0
    resistance_1: float = 0.0
    resistance_2: float = 0.0
    resistance_3: float = 0.0
    support_1: float = 0.0
    support_2: float = 0.0
    support_3: float = 0.0

    # Auto-detected levels
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)

    # Key levels relative to current price
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    support_distance_pct: float = 0.0
    resistance_distance_pct: float = 0.0


@dataclass
class ChartPatterns:
    """Detected chart patterns"""
    patterns: List[str] = field(default_factory=list)
    trend_channel: Optional[str] = None  # "ascending", "descending", "horizontal"
    consolidation: bool = False
    breakout_signal: Optional[str] = None  # "bullish", "bearish", None


@dataclass
class TimeframeAnalysis:
    """Analysis for a single timeframe"""
    timeframe: str  # "daily", "60min", "5min"
    trend_direction: str = "neutral"  # "bullish", "bearish", "neutral"
    trend_strength: float = 0.0  # 0-10
    ema_200_trend: str = "neutral"  # Based on price position relative to 200-EMA
    momentum_signal: str = "neutral"  # "bullish", "bearish", "neutral"
    entry_signal: Optional[str] = None  # "buy", "sell", None


@dataclass
class MultiTimeframeAnalysis:
    """Multi-timeframe strategy analysis for swing trading"""
    # Primary trend (Daily) - defines overall bias
    primary_trend: Optional[TimeframeAnalysis] = None
    # Confirmation (60-min) - validates alignment with primary
    confirmation_trend: Optional[TimeframeAnalysis] = None
    # Execution (5-min) - for entry/exit timing
    execution_trend: Optional[TimeframeAnalysis] = None

    # Composite signals
    trend_alignment: str = "neutral"  # "aligned_bullish", "aligned_bearish", "mixed"
    signal_quality: str = "low"  # "high", "medium", "low"
    recommended_action: str = "hold"  # "buy", "sell", "hold"
    confidence: float = 0.0  # 0-100


@dataclass
class BetaAnalysis:
    """Beta calculation relative to benchmark (NASDAQ)"""
    beta: float = 1.0  # Stock's beta relative to benchmark
    benchmark: str = "^IXIC"  # NASDAQ Composite
    correlation: float = 0.0  # Correlation with benchmark
    alpha: float = 0.0  # Jensen's alpha
    r_squared: float = 0.0  # R-squared of the regression

    # Risk interpretation
    volatility_vs_market: str = "average"  # "low", "average", "high", "very_high"
    risk_profile: str = "moderate"  # "conservative", "moderate", "aggressive", "very_aggressive"


@dataclass
class EntryAnalysis:
    """
    Comprehensive entry point analysis based on technical levels.

    Uses the framework from tech-analysis-logic-update.md:
    - Range Position %: Where price sits between support and resistance
    - Confluence Score: Weighted factors confirming the setup
    - Risk/Reward Ratio: Based on structural stop-loss and target
    - Entry Quality: Objective assessment of current price as entry
    """
    # Range Position (0-100%): 0% = at support, 100% = at resistance
    range_position_pct: float = 50.0
    range_position_zone: str = "neutral"  # "discount", "neutral", "premium"

    # Confluence Score (0-10): Weighted sum of confirming factors
    confluence_score: float = 0.0
    confluence_factors: List[str] = field(default_factory=list)

    # Stop-Loss Levels
    suggested_stop_loss: float = 0.0  # ATR-based or support-based
    stop_loss_type: str = "support"  # "support", "atr", "swing_low"
    stop_loss_distance_pct: float = 0.0  # Distance from current price

    # Take Profit / Target
    suggested_target: float = 0.0  # Based on resistance
    target_distance_pct: float = 0.0  # Distance from current price

    # Risk/Reward Calculation
    risk_reward_ratio: float = 0.0  # Target distance / Stop distance
    risk_reward_quality: str = "poor"  # "excellent", "good", "acceptable", "poor"

    # Entry Quality Assessment
    is_good_entry: bool = False  # Is current price a good entry point?
    entry_quality: str = "poor"  # "excellent", "good", "acceptable", "poor"
    entry_quality_score: float = 0.0  # 0-100 score

    # Suggested Entry Points
    suggested_entry_price: float = 0.0  # Optimal entry price
    suggested_entry_zone_low: float = 0.0  # Entry zone lower bound
    suggested_entry_zone_high: float = 0.0  # Entry zone upper bound
    wait_for_pullback: bool = False  # Should wait for pullback?

    # Analysis Reasoning
    entry_reasoning: str = ""  # Human-readable explanation
    warning_signals: List[str] = field(default_factory=list)  # Caution flags


@dataclass
class TechnicalAnalysisResult:
    """Complete technical analysis output"""
    ticker: str
    analysis_date: datetime = field(default_factory=datetime.now)
    current_price: float = 0.0

    # Analysis components
    trend: TrendAnalysis = field(default_factory=TrendAnalysis)
    momentum: MomentumAnalysis = field(default_factory=MomentumAnalysis)
    volatility: VolatilityAnalysis = field(default_factory=VolatilityAnalysis)
    volume: VolumeAnalysis = field(default_factory=VolumeAnalysis)
    support_resistance: SupportResistanceAnalysis = field(default_factory=SupportResistanceAnalysis)
    patterns: ChartPatterns = field(default_factory=ChartPatterns)

    # Multi-timeframe analysis
    multi_timeframe: MultiTimeframeAnalysis = field(default_factory=MultiTimeframeAnalysis)

    # Beta/Risk analysis
    beta_analysis: BetaAnalysis = field(default_factory=BetaAnalysis)

    # Entry Analysis (comprehensive entry point evaluation)
    entry_analysis: EntryAnalysis = field(default_factory=EntryAnalysis)

    # Overall scoring (0-10)
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    volume_score: float = 0.0
    price_action_score: float = 5.0  # Support/Resistance based score (0-10)
    composite_technical_score: float = 0.0

    # Trading signals
    overall_signal: str = "neutral"  # "strong_buy", "buy", "neutral", "sell", "strong_sell"
    signal_confidence: float = 0.0  # 0-100

    # Chart data for visualization
    chart_data: Dict[str, Any] = field(default_factory=dict)

    # Data source attribution
    data_sources: Dict[str, Any] = field(default_factory=dict)


class TechnicalAnalysisAgent:
    """
    Technical Analysis Agent optimized for growth stocks

    Implements 11 indicators with special configuration for high-growth,
    high-volatility stocks:
    - Broader RSI thresholds (25/75 instead of 30/70)
    - Wider Bollinger Bands (2.5σ instead of 2σ)
    - Higher momentum weighting
    - Shorter moving average periods
    """

    def __init__(self):
        """Initialize technical analysis agent"""
        self.min_periods = 50  # Minimum data points needed

        # Growth stock configuration
        self.rsi_oversold = 25  # Lower threshold for growth stocks
        self.rsi_overbought = 75  # Higher threshold for growth stocks
        self.bb_std = 2.5  # Wider bands for growth stocks

        # Scoring weights (optimized for growth stocks)
        # Now includes price_action based on support/resistance levels
        self.weights = {
            "trend": 0.25,
            "momentum": 0.30,  # Higher weight for momentum
            "volatility": 0.10,
            "volume": 0.15,
            "price_action": 0.20  # Support/Resistance based entry quality
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def analyze(
        self,
        ticker: str,
        price_data: List[Dict[str, Any]],
        current_price: Optional[float] = None,
        price_data_60min: Optional[List[Dict[str, Any]]] = None,
        price_data_5min: Optional[List[Dict[str, Any]]] = None,
        benchmark_data: Optional[List[Dict[str, Any]]] = None,
    ) -> TechnicalAnalysisResult:
        """
        Perform comprehensive technical analysis

        Args:
            ticker: Stock ticker symbol
            price_data: Historical OHLCV data - Daily (list of dicts with keys: date, open, high, low, close, volume)
            current_price: Current price (optional, will use latest close if not provided)
            price_data_60min: 60-minute OHLCV data for multi-timeframe analysis (optional)
            price_data_5min: 5-minute OHLCV data for multi-timeframe analysis (optional)
            benchmark_data: Benchmark (NASDAQ) daily price data for Beta calculation (optional)

        Returns:
            TechnicalAnalysisResult with complete technical analysis
        """
        logger.info("Starting technical analysis", ticker=ticker, data_points=len(price_data))

        result = TechnicalAnalysisResult(ticker=ticker.upper())

        # Validate data
        if not price_data or len(price_data) < self.min_periods:
            logger.warning("Insufficient data for technical analysis",
                         ticker=ticker,
                         data_points=len(price_data),
                         min_required=self.min_periods)
            result.overall_signal = "neutral"
            result.signal_confidence = 0.0
            return result

        # Convert to DataFrame
        df = self._prepare_dataframe(price_data)

        if df is None or len(df) < self.min_periods:
            logger.warning("Failed to prepare dataframe", ticker=ticker)
            return result

        # Get current price - ensure it's a float (not Decimal)
        if current_price is not None:
            result.current_price = self._safe_float(current_price)
        else:
            result.current_price = self._safe_float(df['close'].iloc[-1])

        # Step 1: Calculate all indicators
        df = self._calculate_indicators(df)

        # Step 2: Analyze trend
        result.trend = self._analyze_trend(df, result.current_price)
        result.trend_score = result.trend.trend_strength_score

        # Step 3: Analyze momentum (with trend context for RSI)
        result.momentum = self._analyze_momentum(df, result.current_price, result.trend)
        result.momentum_score = result.momentum.momentum_score

        # Step 4: Analyze volatility
        result.volatility = self._analyze_volatility(df, result.current_price)
        result.volatility_score = result.volatility.volatility_score

        # Step 5: Analyze volume
        result.volume = self._analyze_volume(df)
        result.volume_score = result.volume.volume_score

        # Step 6: Calculate support/resistance levels
        result.support_resistance = self._calculate_support_resistance(df, result.current_price)

        # Step 6b: Calculate price action score based on SR levels + technical confirmations
        result.price_action_score = self._calculate_price_action_score(
            result.current_price,
            result.support_resistance,
            result.trend.trend_direction,
            momentum=result.momentum,
            volume=result.volume,
            trend=result.trend
        )

        # Step 7: Detect chart patterns
        result.patterns = self._detect_patterns(df)

        # Step 8: Multi-timeframe analysis (if data available)
        if price_data_60min or price_data_5min:
            result.multi_timeframe = self._analyze_multi_timeframe(
                df,  # Daily data
                price_data_60min,
                price_data_5min,
                result.current_price
            )

        # Step 9: Beta calculation (if benchmark data available)
        if benchmark_data:
            result.beta_analysis = self._calculate_beta(df, benchmark_data)

        # Step 9b: Comprehensive Entry Analysis
        result.entry_analysis = self._calculate_entry_analysis(
            current_price=result.current_price,
            sr=result.support_resistance,
            trend=result.trend,
            momentum=result.momentum,
            volume=result.volume,
            volatility=result.volatility,
            atr=result.volatility.atr
        )
        # Update price_action_score from entry analysis
        result.price_action_score = result.entry_analysis.entry_quality_score / 10.0  # Convert 0-100 to 0-10

        # Step 10: Calculate composite score
        result.composite_technical_score = self._calculate_composite_score(result)

        # Step 11: Generate trading signal
        result.overall_signal, result.signal_confidence = self._generate_signal(result)

        # Step 12: Prepare chart data
        result.chart_data = self._prepare_chart_data(df, result)

        # Step 13: Track data sources
        result.data_sources = {
            "price_data": {"type": "input", "name": "historical_prices"},
            "indicators": {"type": "calculation", "name": "pandas_ta"},
            "analysis": {"type": "agent", "name": "technical_analysis_agent"}
        }

        logger.info("Technical analysis completed",
                   ticker=ticker,
                   signal=result.overall_signal,
                   confidence=result.signal_confidence,
                   composite_score=result.composite_technical_score)

        return result

    def _prepare_dataframe(self, price_data: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
        """Convert price data to DataFrame with proper formatting"""
        try:
            df = pd.DataFrame(price_data)

            # Ensure required columns exist
            required = ['close', 'high', 'low', 'open', 'volume']
            if not all(col in df.columns for col in required):
                logger.error("Missing required columns", columns=df.columns.tolist())
                return None

            # Convert to float - handle Decimal types explicitly
            def to_float(val):
                if val is None:
                    return np.nan
                if isinstance(val, Decimal):
                    return float(val)
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return np.nan

            for col in required:
                df[col] = df[col].apply(to_float)

            # Sort by date if date column exists and set as index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                df = df.set_index('date')

            # Drop rows with NaN values
            df = df.dropna(subset=required)

            return df

        except Exception as e:
            logger.error("Failed to prepare dataframe", error=str(e))
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        try:
            if ta is None:
                logger.warning("pandas_ta not available, using basic calculations")
                return self._calculate_indicators_basic(df)

            # Trend indicators
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            df.ta.sma(length=200, append=True)
            df.ta.ema(length=12, append=True)
            df.ta.ema(length=26, append=True)
            df.ta.adx(length=14, append=True)

            # Momentum indicators
            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.stoch(k=14, d=3, append=True)
            df.ta.roc(length=12, append=True)

            # Volatility indicators
            df.ta.bbands(length=20, std=self.bb_std, append=True)
            df.ta.atr(length=14, append=True)

            # Volume indicators
            df.ta.obv(append=True)

            logger.info("Calculated all indicators using pandas_ta")

        except Exception as e:
            logger.warning("Error calculating indicators with pandas_ta", error=str(e))
            df = self._calculate_indicators_basic(df)

        return df

    def _calculate_indicators_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic indicators without pandas_ta"""
        try:
            # Simple Moving Averages
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()
            df['SMA_200'] = df['close'].rolling(window=200).mean()

            # Exponential Moving Averages
            df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()

            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI_14'] = 100 - (100 / (1 + rs))

            # MACD
            df['MACD_12_26_9'] = df['EMA_12'] - df['EMA_26']
            df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
            df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']

            # Bollinger Bands
            df['BBM_20_2.5'] = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            df['BBU_20_2.5'] = df['BBM_20_2.5'] + (self.bb_std * std)
            df['BBL_20_2.5'] = df['BBM_20_2.5'] - (self.bb_std * std)
            df['BBB_20_2.5'] = df['BBU_20_2.5'] - df['BBL_20_2.5']

            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            df['ATRr_14'] = true_range.rolling(14).mean()

            # OBV
            df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

            # ROC
            df['ROC_12'] = ((df['close'] - df['close'].shift(12)) / df['close'].shift(12)) * 100

            logger.info("Calculated basic indicators")

        except Exception as e:
            logger.error("Error calculating basic indicators", error=str(e))

        return df

    def _analyze_trend(self, df: pd.DataFrame, current_price: float) -> TrendAnalysis:
        """Analyze trend indicators"""
        trend = TrendAnalysis()

        try:
            latest = df.iloc[-1]

            # Moving averages
            trend.sma_20 = self._safe_float(latest.get('SMA_20', 0))
            trend.sma_50 = self._safe_float(latest.get('SMA_50', 0))
            trend.sma_200 = self._safe_float(latest.get('SMA_200', 0))
            trend.ema_12 = self._safe_float(latest.get('EMA_12', 0))
            trend.ema_26 = self._safe_float(latest.get('EMA_26', 0))

            # Price position
            if current_price > 0:
                trend.price_above_sma_20 = current_price > trend.sma_20 if trend.sma_20 > 0 else False
                trend.price_above_sma_50 = current_price > trend.sma_50 if trend.sma_50 > 0 else False
                trend.price_above_sma_200 = current_price > trend.sma_200 if trend.sma_200 > 0 else False

            # Golden/Death cross
            if trend.sma_50 > 0 and trend.sma_200 > 0:
                trend.golden_cross = trend.sma_50 > trend.sma_200
                trend.death_cross = trend.sma_50 < trend.sma_200

            # ADX (trend strength)
            trend.adx = self._safe_float(latest.get('ADX_14', 0))
            if trend.adx > 40:
                trend.adx_signal = "very_strong"
            elif trend.adx > 25:
                trend.adx_signal = "strong"
            elif trend.adx > 15:
                trend.adx_signal = "moderate"
            else:
                trend.adx_signal = "weak"

            # Determine trend direction
            ma_signals = sum([trend.price_above_sma_20, trend.price_above_sma_50, trend.price_above_sma_200])
            if ma_signals >= 2:
                trend.trend_direction = "bullish"
            elif ma_signals <= 1:
                trend.trend_direction = "bearish"
            else:
                trend.trend_direction = "neutral"

            # Calculate trend strength score (0-10)
            score = 5.0

            # MA alignment (40%)
            if ma_signals == 3:
                score += 2.0
            elif ma_signals == 2:
                score += 1.0
            elif ma_signals == 0:
                score -= 2.0

            # ADX strength (30%)
            if trend.adx > 40:
                score += 1.5
            elif trend.adx > 25:
                score += 1.0
            elif trend.adx < 15:
                score -= 1.0

            # Golden cross (20%)
            if trend.golden_cross:
                score += 1.0
            elif trend.death_cross:
                score -= 1.0

            # EMA position (10%)
            if trend.ema_12 > trend.ema_26:
                score += 0.5
            else:
                score -= 0.5

            trend.trend_strength_score = max(0, min(10, score))

        except Exception as e:
            logger.error("Error analyzing trend", error=str(e))

        return trend

    def _analyze_momentum(
        self,
        df: pd.DataFrame,
        current_price: float,
        trend_analysis: Optional[TrendAnalysis] = None
    ) -> MomentumAnalysis:
        """Analyze momentum indicators with trend-context conditional weighting"""
        momentum = MomentumAnalysis()

        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # RSI
            momentum.rsi = self._safe_float(latest.get('RSI_14', 50))
            if momentum.rsi < self.rsi_oversold:
                momentum.rsi_signal = "oversold"
            elif momentum.rsi > self.rsi_overbought:
                momentum.rsi_signal = "overbought"
            else:
                momentum.rsi_signal = "neutral"

            # RSI Conditional Weighting based on Trend Context
            # If long-term trend is strongly bullish, RSI overbought should not auto-trigger sell
            # Assets in strong uptrends can remain overbought for extended periods
            momentum.rsi_weight = 1.0  # Default full weight
            momentum.rsi_weighted_signal = momentum.rsi_signal

            if trend_analysis:
                is_strong_uptrend = (
                    trend_analysis.price_above_sma_200 and
                    trend_analysis.price_above_sma_50 and
                    trend_analysis.trend_direction == "bullish" and
                    trend_analysis.adx > 25  # Strong trend
                )
                is_strong_downtrend = (
                    not trend_analysis.price_above_sma_200 and
                    not trend_analysis.price_above_sma_50 and
                    trend_analysis.trend_direction == "bearish" and
                    trend_analysis.adx > 25  # Strong trend
                )

                # In strong uptrend, reduce weight of overbought signal
                if is_strong_uptrend and momentum.rsi_signal == "overbought":
                    momentum.rsi_weight = 0.3  # Reduce overbought weight to 30%
                    momentum.rsi_weighted_signal = "neutral_in_uptrend"  # Override signal

                # In strong downtrend, reduce weight of oversold signal (may stay oversold)
                elif is_strong_downtrend and momentum.rsi_signal == "oversold":
                    momentum.rsi_weight = 0.3  # Reduce oversold weight to 30%
                    momentum.rsi_weighted_signal = "neutral_in_downtrend"

            # MACD
            momentum.macd = self._safe_float(latest.get('MACD_12_26_9', 0))
            momentum.macd_signal = self._safe_float(latest.get('MACDs_12_26_9', 0))
            momentum.macd_histogram = self._safe_float(latest.get('MACDh_12_26_9', 0))

            prev_hist = self._safe_float(prev.get('MACDh_12_26_9', 0))
            if momentum.macd_histogram > 0 and prev_hist <= 0:
                momentum.macd_cross = "bullish"
            elif momentum.macd_histogram < 0 and prev_hist >= 0:
                momentum.macd_cross = "bearish"

            # Stochastic
            momentum.stoch_k = self._safe_float(latest.get('STOCHk_14_3_3', 50))
            momentum.stoch_d = self._safe_float(latest.get('STOCHd_14_3_3', 50))
            if momentum.stoch_k < 20:
                momentum.stoch_signal = "oversold"
            elif momentum.stoch_k > 80:
                momentum.stoch_signal = "overbought"
            else:
                momentum.stoch_signal = "neutral"

            # ROC
            momentum.roc = self._safe_float(latest.get('ROC_12', 0))
            if momentum.roc > 10:
                momentum.roc_signal = "bullish"
            elif momentum.roc < -10:
                momentum.roc_signal = "bearish"
            else:
                momentum.roc_signal = "neutral"

            # Calculate momentum score (0-10) with RSI conditional weighting
            score = 5.0

            # RSI (30%) - Apply conditional weighting
            rsi_contribution = 0.0
            if momentum.rsi_signal == "oversold":
                rsi_contribution = 1.5
            elif momentum.rsi_signal == "overbought":
                rsi_contribution = -1.5
            elif 40 < momentum.rsi < 60:
                rsi_contribution = 0.3

            # Apply weight based on trend context
            score += rsi_contribution * momentum.rsi_weight

            # MACD (35%)
            if momentum.macd_cross == "bullish":
                score += 1.75
            elif momentum.macd_cross == "bearish":
                score -= 1.75
            elif momentum.macd_histogram > 0:
                score += 0.7
            else:
                score -= 0.7

            # Stochastic (20%)
            if momentum.stoch_signal == "oversold" and momentum.stoch_k > momentum.stoch_d:
                score += 1.0
            elif momentum.stoch_signal == "overbought" and momentum.stoch_k < momentum.stoch_d:
                score -= 1.0

            # ROC (15%)
            if momentum.roc > 10:
                score += 0.75
            elif momentum.roc < -10:
                score -= 0.75

            momentum.momentum_score = max(0, min(10, score))

        except Exception as e:
            logger.error("Error analyzing momentum", error=str(e))

        return momentum

    def _analyze_volatility(self, df: pd.DataFrame, current_price: float) -> VolatilityAnalysis:
        """Analyze volatility indicators"""
        volatility = VolatilityAnalysis()

        try:
            latest = df.iloc[-1]

            # Bollinger Bands
            volatility.bb_upper = self._safe_float(latest.get('BBU_20_2.5', 0))
            volatility.bb_middle = self._safe_float(latest.get('BBM_20_2.5', 0))
            volatility.bb_lower = self._safe_float(latest.get('BBL_20_2.5', 0))
            volatility.bb_width = self._safe_float(latest.get('BBB_20_2.5', 0))

            # Price position in bands
            if current_price > 0 and volatility.bb_upper > 0:
                if current_price > volatility.bb_upper:
                    volatility.price_position = "above_upper"
                    volatility.bb_signal = "breakout_upper"
                elif current_price > volatility.bb_middle:
                    volatility.price_position = "upper"
                    volatility.bb_signal = "neutral"
                elif current_price > volatility.bb_lower:
                    volatility.price_position = "lower"
                    volatility.bb_signal = "neutral"
                else:
                    volatility.price_position = "below_lower"
                    volatility.bb_signal = "breakout_lower"

                # Squeeze detection (narrow bands)
                if volatility.bb_middle > 0:
                    bandwidth_pct = (volatility.bb_width / volatility.bb_middle) * 100
                    if bandwidth_pct < 10:
                        volatility.bb_signal = "squeeze"

            # ATR
            volatility.atr = self._safe_float(latest.get('ATRr_14', 0))
            if current_price > 0:
                volatility.atr_percent = (volatility.atr / current_price) * 100

                if volatility.atr_percent < 2:
                    volatility.volatility_level = "low"
                elif volatility.atr_percent < 4:
                    volatility.volatility_level = "moderate"
                elif volatility.atr_percent < 6:
                    volatility.volatility_level = "high"
                else:
                    volatility.volatility_level = "very_high"

            # Calculate volatility score (0-10)
            # For growth stocks, moderate volatility is acceptable
            score = 5.0

            if volatility.bb_signal == "squeeze":
                score += 1.0  # Potential breakout
            elif volatility.bb_signal == "breakout_upper":
                score += 1.5  # Bullish breakout
            elif volatility.bb_signal == "breakout_lower":
                score -= 1.5  # Bearish breakout

            # Volatility level (growth stocks can handle more volatility)
            if volatility.volatility_level == "low":
                score += 0.5
            elif volatility.volatility_level == "very_high":
                score -= 1.0

            volatility.volatility_score = max(0, min(10, score))

        except Exception as e:
            logger.error("Error analyzing volatility", error=str(e))

        return volatility

    def _analyze_volume(self, df: pd.DataFrame) -> VolumeAnalysis:
        """Analyze volume indicators"""
        volume = VolumeAnalysis()

        try:
            latest = df.iloc[-1]

            # Current volume - handle NaN properly
            current_vol = latest['volume'] if 'volume' in latest.index else 0
            volume.current_volume = int(current_vol) if pd.notna(current_vol) else 0

            # Average volume
            if len(df) >= 20:
                avg_vol = df['volume'].tail(20).mean()
                volume.avg_volume_20d = int(avg_vol) if pd.notna(avg_vol) else 0
                if volume.avg_volume_20d > 0:
                    volume.volume_ratio = volume.current_volume / volume.avg_volume_20d

                    if volume.volume_ratio < 0.5:
                        volume.volume_signal = "low"
                    elif volume.volume_ratio > 2.0:
                        volume.volume_signal = "very_high"
                    elif volume.volume_ratio > 1.5:
                        volume.volume_signal = "high"
                    else:
                        volume.volume_signal = "normal"

            # OBV - access directly from the row
            obv_val = latest['OBV'] if 'OBV' in latest.index else 0
            volume.obv = self._safe_float(obv_val)

            # OBV trend
            if len(df) >= 20:
                obv_series = df['OBV'].tail(20)
                obv_slope = (obv_series.iloc[-1] - obv_series.iloc[0]) / len(obv_series)
                if obv_slope > 0:
                    volume.obv_trend = "rising"
                elif obv_slope < 0:
                    volume.obv_trend = "falling"
                else:
                    volume.obv_trend = "neutral"

            # Calculate volume score (0-10)
            score = 5.0

            # Volume confirmation (40%)
            if volume.volume_signal == "high" or volume.volume_signal == "very_high":
                # High volume confirms moves
                price_change = (latest['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close']
                if price_change > 0:
                    score += 2.0
                else:
                    score -= 1.0
            elif volume.volume_signal == "low":
                score -= 0.5

            # OBV trend (60%)
            if volume.obv_trend == "rising":
                score += 3.0
            elif volume.obv_trend == "falling":
                score -= 3.0

            volume.volume_score = max(0, min(10, score))

        except Exception as e:
            logger.error("Error analyzing volume", error=str(e))

        return volume

    def _calculate_support_resistance(self, df: pd.DataFrame, current_price: float) -> SupportResistanceAnalysis:
        """Calculate support and resistance levels"""
        sr = SupportResistanceAnalysis()

        try:
            latest = df.iloc[-1]

            # Pivot Points (Classic) - use direct column access
            high = self._safe_float(latest['high'] if 'high' in latest.index else 0)
            low = self._safe_float(latest['low'] if 'low' in latest.index else 0)
            close = self._safe_float(latest['close'] if 'close' in latest.index else 0)

            # Only calculate if we have valid data
            if high > 0 and low > 0 and close > 0:
                sr.pivot = (high + low + close) / 3
                sr.resistance_1 = (2 * sr.pivot) - low
                sr.support_1 = (2 * sr.pivot) - high
                sr.resistance_2 = sr.pivot + (high - low)
                sr.support_2 = sr.pivot - (high - low)
                sr.resistance_3 = high + 2 * (sr.pivot - low)
                sr.support_3 = low - 2 * (high - sr.pivot)

            # Auto-detect support/resistance from swing points using multiple windows
            if len(df) >= 20:
                # Use multiple window sizes to catch different timeframe swings
                all_support_candidates = set()
                all_resistance_candidates = set()

                for window in [5, 10, 20]:  # Multiple window sizes for robustness
                    if len(df) >= window * 2 + 1:
                        highs = df['high'].rolling(window=window*2+1, center=True).max()
                        lows = df['low'].rolling(window=window*2+1, center=True).min()

                        # Resistance levels (local maxima)
                        resistance_candidates = df[df['high'] == highs]['high'].unique()
                        for r in resistance_candidates:
                            if r > current_price:
                                all_resistance_candidates.add(float(r))

                        # Support levels (local minima)
                        support_candidates = df[df['low'] == lows]['low'].unique()
                        for s in support_candidates:
                            if s < current_price:
                                all_support_candidates.add(float(s))

                # Sort and take top 3
                sr.resistance_levels = sorted(list(all_resistance_candidates))[:3]
                sr.support_levels = sorted(list(all_support_candidates), reverse=True)[:3]

            # === FIND TRUE NEAREST LEVELS FROM ALL SOURCES ===
            # Combine pivot-based AND swing-detected levels to find actual nearest

            # Collect all valid support levels below current price
            all_supports_below = []

            # Add pivot-based supports if valid and below current price
            for pivot_support in [sr.support_1, sr.support_2, sr.support_3]:
                if pivot_support > 0 and pivot_support < current_price:
                    all_supports_below.append(pivot_support)

            # Add swing-detected supports
            for swing_support in sr.support_levels:
                if swing_support > 0 and swing_support < current_price:
                    all_supports_below.append(swing_support)

            # Collect all valid resistance levels above current price
            all_resistances_above = []

            # Add pivot-based resistances if valid and above current price
            for pivot_resistance in [sr.resistance_1, sr.resistance_2, sr.resistance_3]:
                if pivot_resistance > 0 and pivot_resistance > current_price:
                    all_resistances_above.append(pivot_resistance)

            # Add swing-detected resistances
            for swing_resistance in sr.resistance_levels:
                if swing_resistance > 0 and swing_resistance > current_price:
                    all_resistances_above.append(swing_resistance)

            # Find TRUE nearest support (highest value below current price)
            if all_supports_below:
                sr.nearest_support = max(all_supports_below)  # Closest to current price
                sr.support_distance_pct = ((current_price - sr.nearest_support) / current_price) * 100

            # Find TRUE nearest resistance (lowest value above current price)
            if all_resistances_above:
                sr.nearest_resistance = min(all_resistances_above)  # Closest to current price
                sr.resistance_distance_pct = ((sr.nearest_resistance - current_price) / current_price) * 100

        except Exception as e:
            logger.error("Error calculating support/resistance", error=str(e))

        return sr

    def _calculate_price_action_score(
        self,
        current_price: float,
        sr: SupportResistanceAnalysis,
        trend_direction: str,
        momentum: Optional['MomentumAnalysis'] = None,
        volume: Optional['VolumeAnalysis'] = None,
        trend: Optional['TrendAnalysis'] = None
    ) -> float:
        """
        Calculate price action score based on support/resistance levels and technical signals.

        A good entry point is where buying pressure is likely to overpower selling pressure.

        Technical Analysis Entry Signals:
        1. SUPPORT/RESISTANCE: Buy near strong support, or on breakout above resistance
        2. MOMENTUM (RSI): Oversold (<30) crossing back up = buy signal
        3. TREND (MA): Bullish crossover (50-day > 200-day) confirms uptrend
        4. MACD: MACD crossing above signal line = momentum shift
        5. VOLUME: Above-average volume confirms the move's significance

        Score ranges from 0-10:
        - 8-10: Excellent entry (near support + momentum confirmation + volume)
        - 6-8: Good entry (near support OR breakout with some confirmation)
        - 4-6: Neutral zone (no clear signal)
        - 2-4: Poor entry (at resistance, overextended, weak volume)
        - 0-2: Very poor entry (multiple warning signs)
        """
        score = 5.0  # Start neutral

        try:
            # Check if we have valid SR levels
            has_support = sr.nearest_support is not None and sr.nearest_support > 0
            has_resistance = sr.nearest_resistance is not None and sr.nearest_resistance > 0

            if not has_support and not has_resistance:
                return score  # Return neutral if no levels available

            # Get distances (already calculated as percentages)
            support_dist_pct = sr.support_distance_pct if has_support else 100
            resistance_dist_pct = sr.resistance_distance_pct if has_resistance else 100

            # === 1. SUPPORT & RESISTANCE ANALYSIS ===
            # Entry Signal: Buy when price rebounds off support OR breaks above resistance

            if trend_direction in ["bullish", "neutral"]:
                # GOOD: Price near support (potential bounce zone)
                if has_support:
                    if support_dist_pct <= 2.0:
                        # Very close to support - excellent entry zone
                        score += 2.0
                        logger.debug(f"Price within 2% of support - excellent entry zone")
                    elif support_dist_pct <= 5.0:
                        # Close to support - good entry zone
                        score += 1.5
                    elif support_dist_pct <= 8.0:
                        # Moderate - acceptable entry
                        score += 0.5

                # CAUTION: Price near resistance (potential rejection)
                if has_resistance:
                    if resistance_dist_pct <= 2.0:
                        # At resistance - high risk of rejection unless breakout
                        score -= 1.5
                    elif resistance_dist_pct <= 5.0:
                        # Near resistance - caution
                        score -= 0.5

            elif trend_direction == "bearish":
                # In bearish trend, near support is risky (may break down)
                if has_support and support_dist_pct <= 3.0:
                    score -= 1.0  # Support may fail in downtrend

            # === 2. MOMENTUM CONFIRMATION (RSI) ===
            # Entry Signal: RSI drops below 30 (oversold) then crosses back up above 30
            if momentum:
                rsi = momentum.rsi
                rsi_signal = momentum.rsi_signal

                if rsi_signal == "oversold" or (rsi and rsi < 35):
                    # Oversold = potential buying opportunity
                    score += 1.5
                    logger.debug(f"RSI oversold ({rsi}) - buying opportunity")
                elif rsi_signal == "overbought" or (rsi and rsi > 70):
                    # Overbought = not a good entry for longs
                    score -= 1.5
                    logger.debug(f"RSI overbought ({rsi}) - poor entry")
                elif rsi and 40 <= rsi <= 60:
                    # Neutral zone - acceptable
                    score += 0.25

                # MACD confirmation
                if momentum.macd_cross == "bullish":
                    # Bullish MACD crossover = momentum shift, good entry
                    score += 1.0
                    logger.debug("MACD bullish crossover - momentum confirmation")
                elif momentum.macd_cross == "bearish":
                    # Bearish MACD = weak entry
                    score -= 0.75

            # === 3. TREND CONFIRMATION (Moving Averages) ===
            # Entry Signal: Bullish when 50-day MA > 200-day MA (golden cross)
            if trend:
                if trend.golden_cross:
                    # Golden cross = confirmed uptrend, good entry
                    score += 1.0
                    logger.debug("Golden cross present - trend confirmation")
                elif trend.death_cross:
                    # Death cross = downtrend, risky entry for longs
                    score -= 1.0

                # Price above key MAs = bullish structure
                if trend.price_above_sma_50 and trend.price_above_sma_200:
                    score += 0.5
                elif not trend.price_above_sma_50 and not trend.price_above_sma_200:
                    score -= 0.5

            # === 4. VOLUME CONFIRMATION ===
            # Entry Signal: Above-average volume confirms move significance
            if volume:
                volume_ratio = volume.volume_ratio
                if volume_ratio and volume_ratio >= 1.5:
                    # High volume = strong conviction, confirms the move
                    score += 1.0
                    logger.debug(f"High volume ({volume_ratio}x) - move confirmed")
                elif volume_ratio and volume_ratio >= 1.2:
                    # Above average volume
                    score += 0.5
                elif volume_ratio and volume_ratio < 0.7:
                    # Low volume = weak move, may be false signal
                    score -= 0.5

                # OBV trend
                if volume.obv_trend == "rising":
                    score += 0.5  # Accumulation
                elif volume.obv_trend == "falling":
                    score -= 0.5  # Distribution

            # === 5. RISK/REWARD CALCULATION ===
            if has_support and has_resistance:
                if support_dist_pct > 0:
                    rr_ratio = resistance_dist_pct / support_dist_pct
                    if rr_ratio >= 3.0:
                        score += 1.5  # Excellent R/R
                    elif rr_ratio >= 2.0:
                        score += 1.0  # Good R/R
                    elif rr_ratio >= 1.5:
                        score += 0.5  # Acceptable
                    elif rr_ratio < 0.75:
                        score -= 1.0  # Poor R/R

            # === 6. MULTIPLE SUPPORT LEVEL CONFIRMATION ===
            # Count support levels below (stronger foundation = better entry)
            support_levels_below = len([s for s in sr.support_levels if s < current_price])
            pivot_supports_below = sum([
                1 for s in [sr.support_1, sr.support_2, sr.support_3]
                if s > 0 and s < current_price
            ])
            total_supports = support_levels_below + pivot_supports_below

            if total_supports >= 4:
                score += 0.75  # Strong support foundation
            elif total_supports >= 2:
                score += 0.5

            # === 7. BREAKOUT DETECTION ===
            # If price just broke above a resistance level, it's potentially good entry
            if has_resistance and resistance_dist_pct < 0:
                # Price is above what was resistance = breakout
                score += 0.5
                logger.debug("Potential breakout above resistance")

        except Exception as e:
            logger.error("Error calculating price action score", error=str(e))
            return 5.0  # Return neutral on error

        # Clamp score to 0-10 range
        return round(max(0.0, min(10.0, score)), 2)

    def _detect_patterns(self, df: pd.DataFrame) -> ChartPatterns:
        """Detect chart patterns"""
        patterns = ChartPatterns()

        try:
            if len(df) < 20:
                return patterns

            # Simple trend channel detection
            closes = df['close'].tail(20)
            x = np.arange(len(closes))
            slope = np.polyfit(x, closes.values, 1)[0]

            if slope > 0:
                patterns.trend_channel = "ascending"
                patterns.patterns.append("Ascending trend channel")
            elif slope < 0:
                patterns.trend_channel = "descending"
                patterns.patterns.append("Descending trend channel")
            else:
                patterns.trend_channel = "horizontal"

            # Consolidation detection (low volatility)
            if len(df) >= 20:
                recent_high = df['high'].tail(20).max()
                recent_low = df['low'].tail(20).min()
                current = df['close'].iloc[-1]

                range_pct = ((recent_high - recent_low) / current) * 100
                if range_pct < 5:
                    patterns.consolidation = True
                    patterns.patterns.append("Price consolidation")

            # Breakout detection
            if len(df) >= 50:
                ma_50 = df['close'].rolling(50).mean().iloc[-1]
                current = df['close'].iloc[-1]
                prev = df['close'].iloc[-2]

                if prev <= ma_50 and current > ma_50:
                    patterns.breakout_signal = "bullish"
                    patterns.patterns.append("Bullish breakout above 50-MA")
                elif prev >= ma_50 and current < ma_50:
                    patterns.breakout_signal = "bearish"
                    patterns.patterns.append("Bearish breakdown below 50-MA")

        except Exception as e:
            logger.error("Error detecting patterns", error=str(e))

        return patterns

    def _calculate_composite_score(self, result: TechnicalAnalysisResult) -> float:
        """Calculate weighted composite technical score including price action (SR levels)"""
        composite = (
            result.trend_score * self.weights["trend"] +
            result.momentum_score * self.weights["momentum"] +
            result.volatility_score * self.weights["volatility"] +
            result.volume_score * self.weights["volume"] +
            result.price_action_score * self.weights["price_action"]
        )
        return round(composite, 2)

    def _generate_signal(self, result: TechnicalAnalysisResult) -> Tuple[str, float]:
        """Generate overall trading signal and confidence, incorporating SR levels"""
        score = result.composite_technical_score

        # Determine signal
        if score >= 8.0:
            signal = "strong_buy"
        elif score >= 6.5:
            signal = "buy"
        elif score >= 4.5:
            signal = "neutral"
        elif score >= 3.0:
            signal = "sell"
        else:
            signal = "strong_sell"

        # Calculate confidence based on indicator agreement
        signals = []

        # Trend signals
        if result.trend.trend_direction == "bullish":
            signals.append(1)
        elif result.trend.trend_direction == "bearish":
            signals.append(-1)
        else:
            signals.append(0)

        # Momentum signals
        if result.momentum.rsi_signal == "oversold" or result.momentum.macd_cross == "bullish":
            signals.append(1)
        elif result.momentum.rsi_signal == "overbought" or result.momentum.macd_cross == "bearish":
            signals.append(-1)
        else:
            signals.append(0)

        # Volume signal
        if result.volume.obv_trend == "rising":
            signals.append(1)
        elif result.volume.obv_trend == "falling":
            signals.append(-1)
        else:
            signals.append(0)

        # Price Action signal (based on SR levels)
        sr = result.support_resistance
        if result.price_action_score >= 7.0:
            signals.append(1)  # Good entry point (near support with room to run)
        elif result.price_action_score <= 3.0:
            signals.append(-1)  # Poor entry point (near resistance or bad R/R)
        else:
            signals.append(0)

        # Calculate agreement
        signal_sum = sum(signals)
        max_agreement = len(signals)
        agreement = abs(signal_sum) / max_agreement

        confidence = min(95, max(50, 50 + (agreement * 45)))

        # === SR-BASED CONFIDENCE ADJUSTMENTS ===
        # Boost confidence if signal aligns with SR position
        if signal in ["buy", "strong_buy"]:
            # Buying near support = higher confidence
            if sr.support_distance_pct is not None and sr.support_distance_pct <= 3.0:
                confidence = min(95, confidence + 5)
            # Buying at resistance = lower confidence
            elif sr.resistance_distance_pct is not None and sr.resistance_distance_pct <= 2.0:
                confidence = max(50, confidence - 10)

        elif signal in ["sell", "strong_sell"]:
            # Selling near resistance (in downtrend) = higher confidence
            if sr.resistance_distance_pct is not None and sr.resistance_distance_pct <= 3.0:
                confidence = min(95, confidence + 5)
            # Selling near support = lower confidence (support may hold)
            elif sr.support_distance_pct is not None and sr.support_distance_pct <= 2.0:
                confidence = max(50, confidence - 5)

        return signal, round(confidence, 1)

    def _prepare_chart_data(self, df: pd.DataFrame, result: TechnicalAnalysisResult) -> Dict[str, Any]:
        """Prepare data for chart visualization

        Uses 1 year of data for calculating trendlines/indicators,
        but limits the display to 6 months (~130 trading days).
        """
        try:
            # Use last 252 trading days (1 year) for calculations
            df_full = df.tail(252).copy()

            # Limit display to last 130 trading days (~6 months)
            df_chart = df_full.tail(130).copy()

            # Convert NaN values to None for proper JSON serialization
            def clean_series(series):
                """Convert series to list with NaN replaced by None"""
                return [None if pd.isna(v) else float(v) for v in series]

            chart_data = {
                "dates": df_chart.index.strftime('%Y-%m-%d').tolist() if hasattr(df_chart.index, 'strftime') else list(range(len(df_chart))),
                "ohlcv": {
                    "open": clean_series(df_chart['open']),
                    "high": clean_series(df_chart['high']),
                    "low": clean_series(df_chart['low']),
                    "close": clean_series(df_chart['close']),
                    "volume": clean_series(df_chart['volume']),
                },
                "moving_averages": {
                    "sma_20": clean_series(df_chart.get('SMA_20', pd.Series())),
                    "sma_50": clean_series(df_chart.get('SMA_50', pd.Series())),
                    "sma_200": clean_series(df_chart.get('SMA_200', pd.Series())),
                },
                "bollinger_bands": {
                    "upper": clean_series(df_chart.get('BBU_20_2.5', pd.Series())),
                    "middle": clean_series(df_chart.get('BBM_20_2.5', pd.Series())),
                    "lower": clean_series(df_chart.get('BBL_20_2.5', pd.Series())),
                },
                "support_resistance": {
                    "support_levels": result.support_resistance.support_levels,
                    "resistance_levels": result.support_resistance.resistance_levels,
                    "pivot": result.support_resistance.pivot,
                },
                "indicators": {
                    "rsi": clean_series(df_chart.get('RSI_14', pd.Series())),
                    "macd": clean_series(df_chart.get('MACD_12_26_9', pd.Series())),
                    "macd_signal": clean_series(df_chart.get('MACDs_12_26_9', pd.Series())),
                    "macd_histogram": clean_series(df_chart.get('MACDh_12_26_9', pd.Series())),
                }
            }

            return chart_data

        except Exception as e:
            logger.error("Error preparing chart data", error=str(e))
            return {}

    def _analyze_single_timeframe(
        self,
        price_data: List[Dict[str, Any]],
        timeframe: str,
        current_price: float
    ) -> Optional[TimeframeAnalysis]:
        """Analyze a single timeframe for multi-timeframe strategy"""
        try:
            df = self._prepare_dataframe(price_data)
            if df is None or len(df) < 20:
                return None

            # Calculate EMAs
            df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean() if len(df) >= 200 else df['close']

            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            latest = df.iloc[-1]

            analysis = TimeframeAnalysis(timeframe=timeframe)

            # EMA 200 trend (defines overall bias)
            ema_200 = self._safe_float(latest.get('EMA_200', 0))
            if ema_200 > 0:
                if current_price > ema_200:
                    analysis.ema_200_trend = "bullish"
                else:
                    analysis.ema_200_trend = "bearish"

            # Trend direction based on EMA alignment
            ema_20 = self._safe_float(latest.get('EMA_20', 0))
            ema_50 = self._safe_float(latest.get('EMA_50', 0))

            if ema_20 > ema_50 > ema_200 and ema_200 > 0:
                analysis.trend_direction = "bullish"
                analysis.trend_strength = 8.0
            elif ema_20 < ema_50 < ema_200 and ema_200 > 0:
                analysis.trend_direction = "bearish"
                analysis.trend_strength = 2.0
            elif ema_20 > ema_50:
                analysis.trend_direction = "bullish"
                analysis.trend_strength = 6.0
            elif ema_20 < ema_50:
                analysis.trend_direction = "bearish"
                analysis.trend_strength = 4.0
            else:
                analysis.trend_direction = "neutral"
                analysis.trend_strength = 5.0

            # Momentum signal from RSI
            rsi = self._safe_float(latest.get('RSI', 50))
            if rsi < 30:
                analysis.momentum_signal = "oversold"
            elif rsi > 70:
                analysis.momentum_signal = "overbought"
            elif rsi < 45:
                analysis.momentum_signal = "bearish"
            elif rsi > 55:
                analysis.momentum_signal = "bullish"
            else:
                analysis.momentum_signal = "neutral"

            # Entry signal for execution timeframe
            if timeframe == "5min":
                # Look for short-term reversal or continuation patterns
                if analysis.trend_direction == "bullish" and rsi < 40:
                    analysis.entry_signal = "buy"
                elif analysis.trend_direction == "bearish" and rsi > 60:
                    analysis.entry_signal = "sell"

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing {timeframe} timeframe", error=str(e))
            return None

    def _analyze_multi_timeframe(
        self,
        df_daily: pd.DataFrame,
        price_data_60min: Optional[List[Dict[str, Any]]],
        price_data_5min: Optional[List[Dict[str, Any]]],
        current_price: float
    ) -> MultiTimeframeAnalysis:
        """
        Multi-Timeframe Strategy Analysis for swing trading

        Primary Trend (Daily): Defines overall market trend via 200-EMA
        Confirmation (60-min): Validates alignment with primary trend
        Execution (5-min): Entry/exit timing refinement
        """
        mtf = MultiTimeframeAnalysis()

        try:
            # Analyze Daily (Primary Trend)
            daily_prices = []
            for idx, row in df_daily.iterrows():
                daily_prices.append({
                    'date': idx,
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                })

            mtf.primary_trend = self._analyze_single_timeframe(
                daily_prices, "daily", current_price
            )

            # Analyze 60-minute (Confirmation)
            if price_data_60min:
                mtf.confirmation_trend = self._analyze_single_timeframe(
                    price_data_60min, "60min", current_price
                )

            # Analyze 5-minute (Execution)
            if price_data_5min:
                mtf.execution_trend = self._analyze_single_timeframe(
                    price_data_5min, "5min", current_price
                )

            # Determine trend alignment
            trends = []
            if mtf.primary_trend:
                trends.append(mtf.primary_trend.trend_direction)
            if mtf.confirmation_trend:
                trends.append(mtf.confirmation_trend.trend_direction)
            if mtf.execution_trend:
                trends.append(mtf.execution_trend.trend_direction)

            if all(t == "bullish" for t in trends) and len(trends) >= 2:
                mtf.trend_alignment = "aligned_bullish"
            elif all(t == "bearish" for t in trends) and len(trends) >= 2:
                mtf.trend_alignment = "aligned_bearish"
            else:
                mtf.trend_alignment = "mixed"

            # Determine signal quality
            if len(trends) >= 3 and mtf.trend_alignment != "mixed":
                mtf.signal_quality = "high"
                mtf.confidence = 85.0
            elif len(trends) >= 2 and mtf.trend_alignment != "mixed":
                mtf.signal_quality = "medium"
                mtf.confidence = 65.0
            else:
                mtf.signal_quality = "low"
                mtf.confidence = 40.0

            # Generate recommended action
            if mtf.trend_alignment == "aligned_bullish" and mtf.signal_quality in ["high", "medium"]:
                # Check if we have a good entry point
                if mtf.execution_trend and mtf.execution_trend.entry_signal == "buy":
                    mtf.recommended_action = "buy"
                else:
                    mtf.recommended_action = "hold_bullish"
            elif mtf.trend_alignment == "aligned_bearish" and mtf.signal_quality in ["high", "medium"]:
                if mtf.execution_trend and mtf.execution_trend.entry_signal == "sell":
                    mtf.recommended_action = "sell"
                else:
                    mtf.recommended_action = "hold_bearish"
            else:
                mtf.recommended_action = "hold"

        except Exception as e:
            logger.error("Error in multi-timeframe analysis", error=str(e))

        return mtf

    def _calculate_beta(
        self,
        df_stock: pd.DataFrame,
        benchmark_data: List[Dict[str, Any]]
    ) -> BetaAnalysis:
        """
        Calculate Beta relative to benchmark (NASDAQ)

        Beta measures systematic risk:
        - Beta > 1: More volatile than market
        - Beta < 1: Less volatile than market
        - Beta = 1: Same volatility as market
        """
        beta_analysis = BetaAnalysis()

        try:
            # Prepare benchmark DataFrame
            df_benchmark = self._prepare_dataframe(benchmark_data)
            if df_benchmark is None or len(df_benchmark) < 30:
                logger.warning("Insufficient benchmark data for beta calculation")
                return beta_analysis

            # Align the two dataframes by date
            # Get common dates
            common_dates = df_stock.index.intersection(df_benchmark.index)
            if len(common_dates) < 30:
                logger.warning("Insufficient overlapping data for beta calculation")
                return beta_analysis

            stock_aligned = df_stock.loc[common_dates, 'close']
            benchmark_aligned = df_benchmark.loc[common_dates, 'close']

            # Calculate returns
            stock_returns = stock_aligned.pct_change().dropna()
            benchmark_returns = benchmark_aligned.pct_change().dropna()

            # Align returns
            aligned_idx = stock_returns.index.intersection(benchmark_returns.index)
            stock_returns = stock_returns.loc[aligned_idx]
            benchmark_returns = benchmark_returns.loc[aligned_idx]

            if len(stock_returns) < 20:
                logger.warning("Insufficient return data for beta calculation")
                return beta_analysis

            # Calculate Beta using covariance / variance
            covariance = np.cov(stock_returns, benchmark_returns)[0, 1]
            variance = np.var(benchmark_returns)

            if variance > 0:
                beta_analysis.beta = covariance / variance
            else:
                beta_analysis.beta = 1.0

            # Calculate correlation
            beta_analysis.correlation = np.corrcoef(stock_returns, benchmark_returns)[0, 1]

            # Calculate R-squared
            beta_analysis.r_squared = beta_analysis.correlation ** 2

            # Calculate Alpha (Jensen's Alpha)
            # Using simple approach: alpha = avg(stock_return) - beta * avg(benchmark_return)
            avg_stock_return = stock_returns.mean()
            avg_benchmark_return = benchmark_returns.mean()
            beta_analysis.alpha = avg_stock_return - (beta_analysis.beta * avg_benchmark_return)

            # Interpret volatility vs market
            if beta_analysis.beta < 0.5:
                beta_analysis.volatility_vs_market = "low"
                beta_analysis.risk_profile = "conservative"
            elif beta_analysis.beta < 1.0:
                beta_analysis.volatility_vs_market = "below_average"
                beta_analysis.risk_profile = "moderate"
            elif beta_analysis.beta < 1.5:
                beta_analysis.volatility_vs_market = "above_average"
                beta_analysis.risk_profile = "aggressive"
            else:
                beta_analysis.volatility_vs_market = "high"
                beta_analysis.risk_profile = "very_aggressive"

            logger.info(
                "Beta calculated",
                beta=round(beta_analysis.beta, 2),
                correlation=round(beta_analysis.correlation, 2),
                r_squared=round(beta_analysis.r_squared, 2)
            )

        except Exception as e:
            logger.error("Error calculating beta", error=str(e))

        return beta_analysis

    def _calculate_entry_analysis(
        self,
        current_price: float,
        sr: SupportResistanceAnalysis,
        trend: TrendAnalysis,
        momentum: MomentumAnalysis,
        volume: VolumeAnalysis,
        volatility: VolatilityAnalysis,
        atr: float
    ) -> EntryAnalysis:
        """
        Comprehensive entry point analysis based on technical framework.

        Implements the logic from tech-analysis-logic-update.md:
        1. Calculate Range Position % - where price sits in trading range
        2. Calculate Confluence Score - weighted technical confirmations
        3. Calculate Risk/Reward Ratio - using structural levels
        4. Determine if current price is a good entry
        5. Suggest optimal entry point if current is not ideal

        Returns:
            EntryAnalysis with complete entry assessment
        """
        entry = EntryAnalysis()

        try:
            # === 1. RANGE POSITION CALCULATION ===
            # Range Position % = (Current Price - Support) / (Resistance - Support) × 100
            nearest_support = sr.nearest_support or sr.support_1 or 0
            nearest_resistance = sr.nearest_resistance or sr.resistance_1 or 0

            if nearest_support > 0 and nearest_resistance > 0 and nearest_resistance > nearest_support:
                range_size = nearest_resistance - nearest_support
                if range_size > 0:
                    entry.range_position_pct = ((current_price - nearest_support) / range_size) * 100
                    entry.range_position_pct = max(0, min(100, entry.range_position_pct))

                    # Determine zone
                    if entry.range_position_pct <= 30:
                        entry.range_position_zone = "discount"  # Near support - good for longs
                    elif entry.range_position_pct >= 70:
                        entry.range_position_zone = "premium"  # Near resistance - risky for longs
                    else:
                        entry.range_position_zone = "neutral"
            else:
                # Fallback if we don't have proper S/R
                entry.range_position_pct = 50.0
                entry.range_position_zone = "neutral"

            # === 2. CONFLUENCE SCORE CALCULATION ===
            # Based on framework: minimum 3.0 required, 4.5+ = high probability, 5.5+ = max position
            confluence_score = 0.0
            confluence_factors = []

            # Factor 1: Higher timeframe trend alignment (weight: 2.0)
            if trend.trend_direction == "bullish" and trend.price_above_sma_200:
                confluence_score += 2.0
                confluence_factors.append("Bullish trend aligned (above SMA 200)")
            elif trend.trend_direction == "bearish" and not trend.price_above_sma_200:
                confluence_score += 1.0  # Bearish alignment (less weight for shorts)
                confluence_factors.append("Bearish trend aligned")

            # Factor 2: Key support/resistance level (weight: 1.5)
            support_dist_pct = sr.support_distance_pct if sr.support_distance_pct else 100
            if support_dist_pct <= 3.0:
                confluence_score += 1.5
                confluence_factors.append(f"At key support level ({support_dist_pct:.1f}% away)")
            elif support_dist_pct <= 5.0:
                confluence_score += 1.0
                confluence_factors.append(f"Near support level ({support_dist_pct:.1f}% away)")

            # Factor 3: Moving average zone (weight: 1.0)
            if trend.price_above_sma_20 and trend.price_above_sma_50:
                confluence_score += 1.0
                confluence_factors.append("Price above key MAs (20/50)")
            elif not trend.price_above_sma_20 and not trend.price_above_sma_50:
                confluence_score -= 0.5  # Negative for bearish
                confluence_factors.append("Price below key MAs (bearish)")

            # Factor 4: Volume confirmation (weight: 1.0)
            if volume.volume_ratio >= 1.5:
                confluence_score += 1.0
                confluence_factors.append(f"High volume confirmation ({volume.volume_ratio:.1f}x)")
            elif volume.volume_ratio >= 1.2:
                confluence_score += 0.5
                confluence_factors.append(f"Above average volume ({volume.volume_ratio:.1f}x)")

            # Factor 5: Momentum indicator (weight: 0.5)
            if momentum.rsi_signal == "oversold" or (momentum.rsi and momentum.rsi < 35):
                confluence_score += 0.5
                confluence_factors.append(f"RSI oversold ({momentum.rsi:.1f})")
            elif momentum.macd_cross == "bullish":
                confluence_score += 0.5
                confluence_factors.append("MACD bullish crossover")

            # Factor 6: Golden cross present (weight: 0.5)
            if trend.golden_cross:
                confluence_score += 0.5
                confluence_factors.append("Golden cross (SMA 50 > 200)")
            elif trend.death_cross:
                confluence_score -= 0.5
                confluence_factors.append("Death cross warning")

            # Factor 7: OBV confirmation (weight: 0.5)
            if volume.obv_trend == "rising":
                confluence_score += 0.5
                confluence_factors.append("OBV rising (accumulation)")
            elif volume.obv_trend == "falling":
                confluence_score -= 0.5
                confluence_factors.append("OBV falling (distribution)")

            entry.confluence_score = max(0, confluence_score)
            entry.confluence_factors = confluence_factors

            # === 3. STOP-LOSS CALCULATION ===
            # Use ATR-based stop or support-based stop (whichever is more appropriate)
            atr_multiplier = 2.0  # Standard for swing trading

            # ATR-based stop
            atr_stop = current_price - (atr * atr_multiplier) if atr > 0 else 0

            # Support-based stop (1% below nearest support)
            support_stop = nearest_support * 0.99 if nearest_support > 0 else 0

            # Choose the more conservative (higher) stop for longs
            if support_stop > 0 and atr_stop > 0:
                if support_stop > atr_stop:
                    entry.suggested_stop_loss = support_stop
                    entry.stop_loss_type = "support"
                else:
                    entry.suggested_stop_loss = atr_stop
                    entry.stop_loss_type = "atr"
            elif support_stop > 0:
                entry.suggested_stop_loss = support_stop
                entry.stop_loss_type = "support"
            elif atr_stop > 0:
                entry.suggested_stop_loss = atr_stop
                entry.stop_loss_type = "atr"

            # Calculate stop distance
            if entry.suggested_stop_loss > 0 and current_price > 0:
                entry.stop_loss_distance_pct = ((current_price - entry.suggested_stop_loss) / current_price) * 100

            # === 4. TARGET CALCULATION ===
            # Target is nearest resistance (or R1 if no swing resistance)
            if nearest_resistance > 0:
                entry.suggested_target = nearest_resistance * 0.99  # 1% below resistance
                if current_price > 0:
                    entry.target_distance_pct = ((entry.suggested_target - current_price) / current_price) * 100
            elif sr.resistance_1 > 0:
                entry.suggested_target = sr.resistance_1 * 0.99
                if current_price > 0:
                    entry.target_distance_pct = ((entry.suggested_target - current_price) / current_price) * 100

            # === 5. RISK/REWARD RATIO ===
            # R/R = Target Distance / Stop Distance
            if entry.stop_loss_distance_pct > 0 and entry.target_distance_pct > 0:
                entry.risk_reward_ratio = entry.target_distance_pct / entry.stop_loss_distance_pct

                # Categorize R/R quality (minimum 2:1 for swing trading)
                if entry.risk_reward_ratio >= 3.0:
                    entry.risk_reward_quality = "excellent"
                elif entry.risk_reward_ratio >= 2.0:
                    entry.risk_reward_quality = "good"
                elif entry.risk_reward_ratio >= 1.5:
                    entry.risk_reward_quality = "acceptable"
                else:
                    entry.risk_reward_quality = "poor"

            # === 6. ENTRY QUALITY ASSESSMENT ===
            # Combines range position, confluence, and R/R into single quality score
            quality_score = 50.0  # Start neutral

            # Range Position contribution (25%)
            if entry.range_position_zone == "discount":
                quality_score += 20
            elif entry.range_position_zone == "premium":
                quality_score -= 20

            # Confluence contribution (25%)
            if entry.confluence_score >= 5.5:
                quality_score += 25
            elif entry.confluence_score >= 4.5:
                quality_score += 20
            elif entry.confluence_score >= 3.0:
                quality_score += 10
            elif entry.confluence_score < 2.0:
                quality_score -= 15

            # R/R contribution (25%)
            if entry.risk_reward_quality == "excellent":
                quality_score += 25
            elif entry.risk_reward_quality == "good":
                quality_score += 20
            elif entry.risk_reward_quality == "acceptable":
                quality_score += 10
            else:
                quality_score -= 15

            # Trend alignment contribution (25%)
            if trend.trend_direction == "bullish" and trend.price_above_sma_200:
                quality_score += 20
            elif trend.trend_direction == "neutral":
                quality_score += 5
            elif trend.trend_direction == "bearish":
                quality_score -= 15

            entry.entry_quality_score = max(0, min(100, quality_score))

            # Categorize quality
            if entry.entry_quality_score >= 80:
                entry.entry_quality = "excellent"
                entry.is_good_entry = True
            elif entry.entry_quality_score >= 60:
                entry.entry_quality = "good"
                entry.is_good_entry = True
            elif entry.entry_quality_score >= 40:
                entry.entry_quality = "acceptable"
                entry.is_good_entry = False  # Not ideal, but tradeable
            else:
                entry.entry_quality = "poor"
                entry.is_good_entry = False

            # === 7. SUGGESTED ENTRY POINT ===
            # If current price is not ideal, suggest where to enter
            if nearest_support > 0:
                # Optimal entry is 1-3% above nearest support
                entry.suggested_entry_price = nearest_support * 1.02  # 2% above support
                entry.suggested_entry_zone_low = nearest_support * 1.01  # 1% above
                entry.suggested_entry_zone_high = nearest_support * 1.03  # 3% above

                # Determine if should wait for pullback
                if current_price > entry.suggested_entry_zone_high:
                    entry.wait_for_pullback = True
                else:
                    entry.wait_for_pullback = False
            else:
                # Fallback to current price area
                entry.suggested_entry_price = current_price
                entry.suggested_entry_zone_low = current_price * 0.98
                entry.suggested_entry_zone_high = current_price * 1.02
                entry.wait_for_pullback = False

            # === 8. GENERATE REASONING ===
            reasoning_parts = []

            # Current price position
            if entry.range_position_zone == "discount":
                reasoning_parts.append(
                    f"Current price (${current_price:.2f}) is in the discount zone "
                    f"({entry.range_position_pct:.0f}% of range), near support at ${nearest_support:.2f}. "
                    "This is typically a favorable entry zone."
                )
            elif entry.range_position_zone == "premium":
                reasoning_parts.append(
                    f"Current price (${current_price:.2f}) is in the premium zone "
                    f"({entry.range_position_pct:.0f}% of range), near resistance at ${nearest_resistance:.2f}. "
                    "This increases risk of rejection. Consider waiting for a pullback."
                )
            else:
                reasoning_parts.append(
                    f"Current price (${current_price:.2f}) is in a neutral zone "
                    f"({entry.range_position_pct:.0f}% of range) between support and resistance."
                )

            # Confluence assessment
            if entry.confluence_score >= 4.5:
                reasoning_parts.append(
                    f"Confluence score is strong ({entry.confluence_score:.1f}/10) with {len(confluence_factors)} confirming factors."
                )
            elif entry.confluence_score >= 3.0:
                reasoning_parts.append(
                    f"Confluence score meets minimum threshold ({entry.confluence_score:.1f}/10)."
                )
            else:
                reasoning_parts.append(
                    f"Confluence score is weak ({entry.confluence_score:.1f}/10). "
                    "Consider waiting for more confirming signals."
                )

            # Risk/Reward assessment
            if entry.risk_reward_ratio >= 2.0:
                reasoning_parts.append(
                    f"Risk/Reward ratio is favorable at {entry.risk_reward_ratio:.1f}:1 "
                    f"(risk {entry.stop_loss_distance_pct:.1f}% to stop, reward {entry.target_distance_pct:.1f}% to target)."
                )
            elif entry.risk_reward_ratio > 0:
                reasoning_parts.append(
                    f"Risk/Reward ratio is below ideal at {entry.risk_reward_ratio:.1f}:1. "
                    "A minimum 2:1 ratio is recommended for swing trading."
                )

            # Final recommendation
            if entry.is_good_entry:
                reasoning_parts.append(
                    f"ENTRY QUALITY: {entry.entry_quality.upper()} ({entry.entry_quality_score:.0f}/100). "
                    "Current price offers a reasonable entry point."
                )
            else:
                if entry.wait_for_pullback:
                    reasoning_parts.append(
                        f"ENTRY QUALITY: {entry.entry_quality.upper()} ({entry.entry_quality_score:.0f}/100). "
                        f"Consider waiting for pullback to ${entry.suggested_entry_zone_low:.2f} - ${entry.suggested_entry_zone_high:.2f} "
                        "for better risk/reward."
                    )
                else:
                    reasoning_parts.append(
                        f"ENTRY QUALITY: {entry.entry_quality.upper()} ({entry.entry_quality_score:.0f}/100). "
                        "Setup lacks sufficient technical confirmation."
                    )

            entry.entry_reasoning = " ".join(reasoning_parts)

            # === 9. WARNING SIGNALS ===
            warnings = []

            # R/R warning
            if entry.risk_reward_ratio < 1.5 and entry.risk_reward_ratio > 0:
                warnings.append(f"Poor risk/reward ratio ({entry.risk_reward_ratio:.1f}:1)")

            # Premium zone warning
            if entry.range_position_zone == "premium":
                warnings.append("Price near resistance (premium zone)")

            # Death cross warning
            if trend.death_cross:
                warnings.append("Death cross present (bearish)")

            # Low confluence warning
            if entry.confluence_score < 3.0:
                warnings.append(f"Low confluence score ({entry.confluence_score:.1f}/10)")

            # RSI overbought warning
            if momentum.rsi_signal == "overbought":
                warnings.append(f"RSI overbought ({momentum.rsi:.1f})")

            # Low volume warning
            if volume.volume_ratio < 0.7:
                warnings.append(f"Below average volume ({volume.volume_ratio:.1f}x)")

            entry.warning_signals = warnings

            logger.info(
                "Entry analysis completed",
                entry_quality=entry.entry_quality,
                quality_score=entry.entry_quality_score,
                range_position=entry.range_position_pct,
                confluence=entry.confluence_score,
                rr_ratio=entry.risk_reward_ratio,
                is_good_entry=entry.is_good_entry
            )

        except Exception as e:
            logger.error("Error calculating entry analysis", error=str(e))
            entry.entry_reasoning = "Unable to calculate entry analysis due to insufficient data."

        return entry
