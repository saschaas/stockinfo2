"""Technical analysis Celery tasks."""

import asyncio
import uuid
from typing import Any

import structlog

from backend.app.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(bind=True, name="backend.app.tasks.technical_analysis.analyze_stock_technical")
def analyze_stock_technical(
    self,
    ticker: str,
    period: str = "1y",
) -> dict[str, Any]:
    """Perform technical analysis on a stock.

    Args:
        ticker: Stock ticker symbol
        period: Data period (1mo, 3mo, 6mo, 1y, 2y). Defaults to 1y for SMA 200.

    Returns:
        Technical analysis results
    """
    job_id = self.request.id or str(uuid.uuid4())
    ticker = ticker.upper()

    async def run():
        from backend.app.services.yahoo_finance import get_yahoo_finance_client
        from backend.app.services.cache import set_job_progress
        from backend.app.agents.technical_analysis_agent import TechnicalAnalysisAgent

        logger.info("Starting technical analysis", ticker=ticker, job_id=job_id, period=period)

        # Update job status
        await set_job_progress(job_id, "running", 0, "Initializing technical analysis...")

        try:
            result = {"ticker": ticker, "period": period}

            # Step 1: Fetch historical price data (20%)
            await set_job_progress(job_id, "running", 10, "Fetching historical price data...")

            yf_client = get_yahoo_finance_client()

            # Convert period to Yahoo Finance format
            period_map = {
                "1mo": "1mo",
                "3mo": "3mo",
                "6mo": "6mo",
                "1y": "1y",
                "2y": "2y",
            }
            yf_period = period_map.get(period, "6mo")

            prices = await yf_client.get_historical_prices(ticker, period=yf_period, interval="1d")

            if not prices or len(prices) < 50:
                error_msg = f"Insufficient price data for {ticker}. Need at least 50 trading days."
                logger.warning(error_msg, ticker=ticker, data_points=len(prices) if prices else 0)
                await set_job_progress(job_id, "failed", 0, error_msg)
                return {"error": error_msg, "ticker": ticker}

            logger.info("Fetched price data", ticker=ticker, data_points=len(prices))

            # Step 2: Get current price (30%)
            await set_job_progress(job_id, "running", 20, "Fetching current stock info...")

            stock_info = await yf_client.get_stock_info(ticker)
            current_price = stock_info.get("current_price", 0)

            if not current_price:
                # Fallback to latest close price
                current_price = prices[-1].get("close", 0) if prices else 0

            logger.info("Current price", ticker=ticker, price=current_price)

            # Step 3: Run technical analysis (90%)
            await set_job_progress(job_id, "running", 40, "Calculating technical indicators...")

            tech_agent = TechnicalAnalysisAgent()
            analysis_result = await tech_agent.analyze(
                ticker=ticker,
                price_data=prices,
                current_price=current_price
            )

            logger.info("Technical analysis completed",
                       ticker=ticker,
                       signal=analysis_result.overall_signal,
                       composite_score=analysis_result.composite_technical_score)

            # Step 4: Convert dataclass to dict (95%)
            await set_job_progress(job_id, "running", 90, "Preparing results...")

            # Convert result to dict for JSON serialization
            result.update({
                "analysis_date": analysis_result.analysis_date.isoformat(),
                "current_price": analysis_result.current_price,

                # Trend
                "trend_direction": analysis_result.trend.trend_direction,
                "trend_strength_score": analysis_result.trend.trend_strength_score,
                "sma_20": analysis_result.trend.sma_20,
                "sma_50": analysis_result.trend.sma_50,
                "sma_200": analysis_result.trend.sma_200,
                "adx": analysis_result.trend.adx,
                "adx_signal": analysis_result.trend.adx_signal,
                "price_above_sma_20": analysis_result.trend.price_above_sma_20,
                "price_above_sma_50": analysis_result.trend.price_above_sma_50,
                "price_above_sma_200": analysis_result.trend.price_above_sma_200,
                "golden_cross": analysis_result.trend.golden_cross,
                "death_cross": analysis_result.trend.death_cross,

                # Momentum
                "rsi": analysis_result.momentum.rsi,
                "rsi_signal": analysis_result.momentum.rsi_signal,
                "macd": analysis_result.momentum.macd,
                "macd_signal": analysis_result.momentum.macd_signal,
                "macd_histogram": analysis_result.momentum.macd_histogram,
                "macd_cross": analysis_result.momentum.macd_cross,
                "stoch_k": analysis_result.momentum.stoch_k,
                "stoch_d": analysis_result.momentum.stoch_d,
                "stoch_signal": analysis_result.momentum.stoch_signal,
                "roc": analysis_result.momentum.roc,
                "roc_signal": analysis_result.momentum.roc_signal,
                "momentum_score": analysis_result.momentum.momentum_score,

                # Volatility
                "bb_upper": analysis_result.volatility.bb_upper,
                "bb_middle": analysis_result.volatility.bb_middle,
                "bb_lower": analysis_result.volatility.bb_lower,
                "bb_width": analysis_result.volatility.bb_width,
                "bb_signal": analysis_result.volatility.bb_signal,
                "price_position": analysis_result.volatility.price_position,
                "atr": analysis_result.volatility.atr,
                "atr_percent": analysis_result.volatility.atr_percent,
                "volatility_level": analysis_result.volatility.volatility_level,
                "volatility_score": analysis_result.volatility.volatility_score,

                # Volume
                "current_volume": analysis_result.volume.current_volume,
                "avg_volume_20d": analysis_result.volume.avg_volume_20d,
                "volume_ratio": analysis_result.volume.volume_ratio,
                "volume_signal": analysis_result.volume.volume_signal,
                "obv": analysis_result.volume.obv,
                "obv_trend": analysis_result.volume.obv_trend,
                "volume_score": analysis_result.volume.volume_score,

                # Support/Resistance
                "pivot": analysis_result.support_resistance.pivot,
                "resistance_1": analysis_result.support_resistance.resistance_1,
                "resistance_2": analysis_result.support_resistance.resistance_2,
                "resistance_3": analysis_result.support_resistance.resistance_3,
                "support_1": analysis_result.support_resistance.support_1,
                "support_2": analysis_result.support_resistance.support_2,
                "support_3": analysis_result.support_resistance.support_3,
                "support_levels": analysis_result.support_resistance.support_levels,
                "resistance_levels": analysis_result.support_resistance.resistance_levels,
                "nearest_support": analysis_result.support_resistance.nearest_support,
                "nearest_resistance": analysis_result.support_resistance.nearest_resistance,
                "support_distance_pct": analysis_result.support_resistance.support_distance_pct,
                "resistance_distance_pct": analysis_result.support_resistance.resistance_distance_pct,

                # Patterns
                "patterns": analysis_result.patterns.patterns,
                "trend_channel": analysis_result.patterns.trend_channel,
                "consolidation": analysis_result.patterns.consolidation,
                "breakout_signal": analysis_result.patterns.breakout_signal,

                # Overall
                "trend_score": analysis_result.trend_score,
                "price_action_score": analysis_result.price_action_score,
                "composite_technical_score": analysis_result.composite_technical_score,
                "overall_signal": analysis_result.overall_signal,
                "signal_confidence": analysis_result.signal_confidence,

                # Entry Analysis (comprehensive)
                "entry_analysis": {
                    "range_position_pct": analysis_result.entry_analysis.range_position_pct,
                    "range_position_zone": analysis_result.entry_analysis.range_position_zone,
                    "confluence_score": analysis_result.entry_analysis.confluence_score,
                    "confluence_factors": analysis_result.entry_analysis.confluence_factors,
                    "suggested_stop_loss": analysis_result.entry_analysis.suggested_stop_loss,
                    "stop_loss_type": analysis_result.entry_analysis.stop_loss_type,
                    "stop_loss_distance_pct": analysis_result.entry_analysis.stop_loss_distance_pct,
                    "suggested_target": analysis_result.entry_analysis.suggested_target,
                    "target_distance_pct": analysis_result.entry_analysis.target_distance_pct,
                    "risk_reward_ratio": analysis_result.entry_analysis.risk_reward_ratio,
                    "risk_reward_quality": analysis_result.entry_analysis.risk_reward_quality,
                    "is_good_entry": analysis_result.entry_analysis.is_good_entry,
                    "entry_quality": analysis_result.entry_analysis.entry_quality,
                    "entry_quality_score": analysis_result.entry_analysis.entry_quality_score,
                    "suggested_entry_price": analysis_result.entry_analysis.suggested_entry_price,
                    "suggested_entry_zone_low": analysis_result.entry_analysis.suggested_entry_zone_low,
                    "suggested_entry_zone_high": analysis_result.entry_analysis.suggested_entry_zone_high,
                    "wait_for_pullback": analysis_result.entry_analysis.wait_for_pullback,
                    "entry_reasoning": analysis_result.entry_analysis.entry_reasoning,
                    "warning_signals": analysis_result.entry_analysis.warning_signals,
                },

                # Chart data
                "chart_data": analysis_result.chart_data,

                # Data sources
                "data_sources": analysis_result.data_sources,
            })

            # Complete
            await set_job_progress(job_id, "completed", 100, "Technical analysis completed")

            logger.info("Technical analysis task completed",
                       ticker=ticker,
                       job_id=job_id,
                       signal=result["overall_signal"])
            return result

        except Exception as e:
            logger.error("Technical analysis failed", ticker=ticker, error=str(e), exc_info=True)
            error_msg = f"Technical analysis failed: {str(e)}"
            await set_job_progress(job_id, "failed", 0, error_msg)
            raise

    return run_async(run())
