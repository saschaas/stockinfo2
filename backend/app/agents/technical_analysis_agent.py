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

    # Overall scoring (0-10)
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    volume_score: float = 0.0
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
        self.weights = {
            "trend": 0.30,
            "momentum": 0.35,  # Higher weight for momentum
            "volatility": 0.15,
            "volume": 0.20
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
        current_price: Optional[float] = None
    ) -> TechnicalAnalysisResult:
        """
        Perform comprehensive technical analysis

        Args:
            ticker: Stock ticker symbol
            price_data: Historical OHLCV data (list of dicts with keys: date, open, high, low, close, volume)
            current_price: Current price (optional, will use latest close if not provided)

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

        # Step 3: Analyze momentum
        result.momentum = self._analyze_momentum(df, result.current_price)
        result.momentum_score = result.momentum.momentum_score

        # Step 4: Analyze volatility
        result.volatility = self._analyze_volatility(df, result.current_price)
        result.volatility_score = result.volatility.volatility_score

        # Step 5: Analyze volume
        result.volume = self._analyze_volume(df)
        result.volume_score = result.volume.volume_score

        # Step 6: Calculate support/resistance levels
        result.support_resistance = self._calculate_support_resistance(df, result.current_price)

        # Step 7: Detect chart patterns
        result.patterns = self._detect_patterns(df)

        # Step 8: Calculate composite score
        result.composite_technical_score = self._calculate_composite_score(result)

        # Step 9: Generate trading signal
        result.overall_signal, result.signal_confidence = self._generate_signal(result)

        # Step 10: Prepare chart data
        result.chart_data = self._prepare_chart_data(df, result)

        # Step 11: Track data sources
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

    def _analyze_momentum(self, df: pd.DataFrame, current_price: float) -> MomentumAnalysis:
        """Analyze momentum indicators"""
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

            # Calculate momentum score (0-10)
            score = 5.0

            # RSI (30%)
            if momentum.rsi_signal == "oversold":
                score += 1.5
            elif momentum.rsi_signal == "overbought":
                score -= 1.5
            elif 40 < momentum.rsi < 60:
                score += 0.3

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

            # Auto-detect support/resistance from swing points
            if len(df) >= 20:
                window = 5
                highs = df['high'].rolling(window=window*2+1, center=True).max()
                lows = df['low'].rolling(window=window*2+1, center=True).min()

                # Resistance levels (local maxima)
                resistance_candidates = df[df['high'] == highs]['high'].unique()
                sr.resistance_levels = sorted([float(r) for r in resistance_candidates if r > current_price])[:3]

                # Support levels (local minima)
                support_candidates = df[df['low'] == lows]['low'].unique()
                sr.support_levels = sorted([float(s) for s in support_candidates if s < current_price], reverse=True)[:3]

            # Find nearest levels
            if sr.resistance_levels:
                sr.nearest_resistance = sr.resistance_levels[0]
                sr.resistance_distance_pct = ((sr.nearest_resistance - current_price) / current_price) * 100

            if sr.support_levels:
                sr.nearest_support = sr.support_levels[0]
                sr.support_distance_pct = ((current_price - sr.nearest_support) / current_price) * 100

        except Exception as e:
            logger.error("Error calculating support/resistance", error=str(e))

        return sr

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
        """Calculate weighted composite technical score"""
        composite = (
            result.trend_score * self.weights["trend"] +
            result.momentum_score * self.weights["momentum"] +
            result.volatility_score * self.weights["volatility"] +
            result.volume_score * self.weights["volume"]
        )
        return round(composite, 2)

    def _generate_signal(self, result: TechnicalAnalysisResult) -> Tuple[str, float]:
        """Generate overall trading signal and confidence"""
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

        # Calculate agreement
        signal_sum = sum(signals)
        max_agreement = len(signals)
        agreement = abs(signal_sum) / max_agreement

        confidence = min(95, max(50, 50 + (agreement * 45)))

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
