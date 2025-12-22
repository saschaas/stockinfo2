"""Stock research Celery tasks."""

import asyncio
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import structlog

from backend.app.celery_app import celery_app
from backend.app.db.session import async_session_factory
from backend.app.db.models import StockAnalysis, ResearchJob, DataSource

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


@celery_app.task(bind=True, name="backend.app.tasks.research.research_stock")
def research_stock(
    self,
    ticker: str,
    include_peers: bool = True,
    include_technical: bool = True,
    include_ai_analysis: bool = True,
    llm_model: str | None = None,
) -> dict[str, Any]:
    """Perform comprehensive stock research.

    Args:
        ticker: Stock ticker symbol
        include_peers: Include peer comparison
        include_technical: Include technical analysis
        include_ai_analysis: Include AI-powered analysis
        llm_model: Optional Ollama model to use for AI analysis (defaults to settings.ollama_model)

    Returns:
        Research results
    """
    job_id = self.request.id or str(uuid.uuid4())
    ticker = ticker.upper()

    async def run():
        from backend.app.services.alpha_vantage import get_alpha_vantage_client
        from backend.app.services.yahoo_finance import get_yahoo_finance_client
        from backend.app.services.cache import set_job_progress

        logger.info("Starting stock research", ticker=ticker, job_id=job_id)

        # Update job status
        await set_job_progress(job_id, "running", 0, "Initializing research...")
        await update_job_status(job_id, ticker, "running", 0, "Initializing research...")

        try:
            data_sources = {}
            result = {"ticker": ticker}

            # Step 1: Fetch basic stock info (20%)
            await set_job_progress(job_id, "running", 10, "Fetching stock information...")
            await update_job_status(job_id, ticker, "running", 10, "Fetching stock information...")

            yf_client = get_yahoo_finance_client()
            stock_info = await yf_client.get_stock_info(ticker)
            result.update({
                "company_name": stock_info.get("name"),
                "sector": stock_info.get("sector"),
                "industry": stock_info.get("industry"),
                "market_cap": stock_info.get("market_cap"),
                "current_price": stock_info.get("current_price"),
            })
            data_sources["stock_info"] = {"type": "api", "name": "yahoo_finance"}

            # Fetch company description
            description = stock_info.get("description")

            # TODO: Add web scraping fallback when MCP server integration is available
            # If Yahoo Finance doesn't return description, could fallback to web scraping
            # from configurable URL (see web_scraping section in config.yaml)
            # This requires MCP Playwright server to be running and accessible from backend

            result["description"] = description
            if description:
                data_sources["company_description"] = {"type": "api", "name": "yahoo_finance"}
            else:
                logger.info("No company description available from API", ticker=ticker)

            # Step 2: Fetch fundamentals (40%)
            await set_job_progress(job_id, "running", 30, "Fetching fundamentals...")
            await update_job_status(job_id, ticker, "running", 30, "Fetching fundamentals...")

            av_client = await get_alpha_vantage_client()

            try:
                overview = await av_client.get_company_overview(ticker)
                result.update({
                    "pe_ratio": overview.get("pe_ratio"),
                    "forward_pe": overview.get("forward_pe"),
                    "peg_ratio": overview.get("peg_ratio"),
                    "price_to_book": overview.get("price_to_book"),
                    "debt_to_equity": stock_info.get("debt_to_equity"),
                })
                data_sources["fundamentals"] = {"type": "api", "name": "alpha_vantage"}
            except Exception as e:
                logger.warning("Failed to fetch fundamentals", error=str(e))
                # Use Yahoo Finance as fallback
                result.update({
                    "pe_ratio": stock_info.get("pe_ratio"),
                    "forward_pe": stock_info.get("forward_pe"),
                    "peg_ratio": stock_info.get("peg_ratio"),
                    "price_to_book": stock_info.get("price_to_book"),
                })
                data_sources["fundamentals"] = {"type": "api", "name": "yahoo_finance"}

            # Step 3: Technical analysis (60%)
            technical_analysis_result = None
            if include_technical:
                await set_job_progress(job_id, "running", 50, "Running comprehensive technical analysis...")
                await update_job_status(job_id, ticker, "running", 50, "Running comprehensive technical analysis...")

                try:
                    from backend.app.agents.technical_analysis_agent import TechnicalAnalysisAgent

                    # Fetch daily data (1 year for proper indicator calculation)
                    prices = await yf_client.get_historical_prices(ticker, period="1y", interval="1d")
                    current_price = stock_info.get("current_price")

                    # Fetch 60-minute data for multi-timeframe analysis (last 5 days)
                    prices_60min = None
                    try:
                        prices_60min = await yf_client.get_historical_prices(ticker, period="5d", interval="60m")
                        logger.info("Fetched 60-minute data", ticker=ticker, data_points=len(prices_60min))
                    except Exception as e:
                        logger.warning("Failed to fetch 60-minute data", ticker=ticker, error=str(e))

                    # Fetch 5-minute data for execution timing (last 1 day)
                    prices_5min = None
                    try:
                        prices_5min = await yf_client.get_historical_prices(ticker, period="1d", interval="5m")
                        logger.info("Fetched 5-minute data", ticker=ticker, data_points=len(prices_5min))
                    except Exception as e:
                        logger.warning("Failed to fetch 5-minute data", ticker=ticker, error=str(e))

                    # Fetch NASDAQ benchmark data for Beta calculation
                    benchmark_data = None
                    try:
                        benchmark_data = await yf_client.get_historical_prices("^IXIC", period="1y", interval="1d")
                        logger.info("Fetched NASDAQ benchmark data", data_points=len(benchmark_data))
                    except Exception as e:
                        logger.warning("Failed to fetch NASDAQ benchmark data", error=str(e))

                    tech_agent = TechnicalAnalysisAgent()
                    technical_analysis_result = await tech_agent.analyze(
                        ticker=ticker,
                        price_data=prices,
                        current_price=current_price,
                        price_data_60min=prices_60min,
                        price_data_5min=prices_5min,
                        benchmark_data=benchmark_data,
                    )

                    # Store basic technical indicators for backward compatibility
                    technical = {
                        "rsi": technical_analysis_result.momentum.rsi,
                        "sma_20": technical_analysis_result.trend.sma_20,
                        "sma_50": technical_analysis_result.trend.sma_50,
                        "bollinger_upper": technical_analysis_result.volatility.bb_upper,
                        "bollinger_lower": technical_analysis_result.volatility.bb_lower,
                    }
                    result.update(technical)
                    data_sources["technical"] = {"type": "api", "name": "yahoo_finance"}

                    logger.info("Technical analysis completed", ticker=ticker, signal=technical_analysis_result.overall_signal)

                except Exception as e:
                    logger.warning("Comprehensive technical analysis failed, using basic indicators", ticker=ticker, error=str(e))
                    # Fallback to basic technical indicators
                    prices = await yf_client.get_historical_prices(ticker, period="3mo", interval="1d")
                    technical = calculate_technical_indicators(prices)
                    result.update(technical)
                    data_sources["technical"] = {"type": "api", "name": "yahoo_finance"}

            # Step 4: Price performance (65%)
            await set_job_progress(job_id, "running", 60, "Calculating price performance...")

            result.update({
                "target_price_6m": stock_info.get("target_mean_price"),
                "price_change_1d": calculate_change(stock_info.get("current_price"), stock_info.get("previous_close")),
            })

            # Step 4.5: Fetch analyst recommendations (65%)
            recommendations = None
            try:
                recommendations = await yf_client.get_recommendations(ticker)
                logger.info("Fetched analyst recommendations", ticker=ticker, count=len(recommendations))
            except Exception as e:
                logger.warning("Failed to fetch analyst recommendations", ticker=ticker, error=str(e))

            # Step 5: Growth Stock Analysis (80%)
            await set_job_progress(job_id, "running", 70, "Running growth stock analysis...")
            await update_job_status(job_id, ticker, "running", 70, "Running growth stock analysis...")

            try:
                from backend.app.agents.growth_analysis_agent import GrowthAnalysisAgent

                growth_agent = GrowthAnalysisAgent(llm_model=llm_model)

                # Prepare stock data for growth analysis
                stock_data_for_growth = {
                    "info": stock_info,
                    "technicals": technical if include_technical else {},
                    "recommendations": recommendations if recommendations else None,
                    "data_sources": data_sources
                }

                growth_result = await growth_agent.analyze(
                    ticker=ticker,
                    stock_data=stock_data_for_growth,
                    market_context=None,
                    fund_ownership=None
                )

                # Store growth analysis results
                result.update({
                    "portfolio_allocation": growth_result.portfolio_allocation,
                    "price_target_base": growth_result.price_target_base,
                    "price_target_optimistic": growth_result.price_target_optimistic,
                    "price_target_pessimistic": growth_result.price_target_pessimistic,
                    "upside_potential": growth_result.upside_potential,
                    # Price target calculation methods (for transparency)
                    "price_targets": {
                        "base": growth_result.price_target_base,
                        "optimistic": growth_result.price_target_optimistic,
                        "pessimistic": growth_result.price_target_pessimistic,
                        "analyst": growth_result.price_target_analyst,
                        "pe_based": growth_result.price_target_pe_based,
                        "growth_based": growth_result.price_target_growth_based,
                        "method": growth_result.price_target_method,
                        "upside_potential": growth_result.upside_potential,
                    },
                    "composite_score": growth_result.composite_score,
                    "fundamental_score": growth_result.fundamental_score,
                    "sentiment_score": growth_result.sentiment_score,
                    "technical_score": growth_result.technical_score,
                    "competitive_score": growth_result.competitive_score,
                    "risk_score": growth_result.risk_analysis.risk_score,
                    "risk_level": growth_result.risk_analysis.risk_level,
                    "key_strengths": growth_result.key_strengths,
                    "key_risks": growth_result.key_risks,
                    "catalyst_points": growth_result.catalyst_points,
                    "monitoring_points": growth_result.monitoring_points,
                    "data_completeness_score": growth_result.data_completeness.completeness_score,
                    "missing_data_categories": growth_result.data_completeness.missing_critical,
                    "ai_summary": growth_result.ai_summary,
                    "ai_reasoning": growth_result.ai_reasoning,
                    # Valuation Engine fields
                    "intrinsic_value": growth_result.intrinsic_value,
                    "intrinsic_value_low": growth_result.intrinsic_value_low,
                    "intrinsic_value_high": growth_result.intrinsic_value_high,
                    "margin_of_safety": growth_result.margin_of_safety,
                    "valuation_status": growth_result.valuation_status,
                    "valuation_company_type": growth_result.valuation_company_type,
                    "valuation_classification_confidence": growth_result.valuation_classification_confidence,
                    "valuation_classification_reasons": growth_result.valuation_classification_reasons,
                    "valuation_wacc": growth_result.valuation_wacc,
                    "valuation_cost_of_equity": growth_result.valuation_cost_of_equity,
                    "valuation_risk_free_rate": growth_result.valuation_risk_free_rate,
                    "valuation_methods_used": growth_result.valuation_methods_used,
                    "valuation_primary_method": growth_result.valuation_primary_method,
                    "valuation_method_results": growth_result.valuation_method_results,
                    "valuation_confidence": growth_result.valuation_confidence,
                    "valuation_data_quality": growth_result.valuation_data_quality,
                })

                data_sources["growth_analysis"] = {"type": "ai", "name": "growth_analysis_agent"}

                logger.info("Growth analysis completed", ticker=ticker, composite_score=growth_result.composite_score)

            except Exception as e:
                logger.warning("Growth analysis failed", ticker=ticker, error=str(e))
                # Continue without growth analysis

            # Step 6: AI Analysis (75%)
            if include_ai_analysis:
                await set_job_progress(job_id, "running", 75, "Running AI analysis...")
                await update_job_status(job_id, ticker, "running", 75, "Running AI analysis...")

                ai_analysis = await run_ai_analysis(ticker, result, llm_model=llm_model)
                result.update(ai_analysis)
                data_sources["ai_analysis"] = {"type": "ai", "name": "ollama", "model": llm_model or "default"}

            # Helper to clean NaN values and Decimals for JSON serialization
            def clean_nan(obj):
                import math
                from decimal import Decimal
                if isinstance(obj, dict):
                    return {k: clean_nan(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_nan(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                    return None
                return obj

            # Step 7: Add comprehensive technical analysis to result
            if technical_analysis_result:

                # Serialize the technical analysis result for JSON response
                ta = technical_analysis_result
                result["technical_analysis"] = clean_nan({
                    # Basic info
                    "ticker": ta.ticker,
                    "analysis_date": ta.analysis_date.isoformat(),
                    "current_price": ta.current_price,

                    # Scores
                    "trend_score": ta.trend_score,
                    "momentum_score": ta.momentum_score,
                    "volatility_score": ta.volatility_score,
                    "volume_score": ta.volume_score,
                    "price_action_score": ta.price_action_score,
                    "composite_technical_score": ta.composite_technical_score,

                    # Trend
                    "trend_direction": ta.trend.trend_direction,
                    "sma_20": ta.trend.sma_20,
                    "sma_50": ta.trend.sma_50,
                    "sma_200": ta.trend.sma_200,
                    "price_above_sma_20": ta.trend.price_above_sma_20,
                    "price_above_sma_50": ta.trend.price_above_sma_50,
                    "price_above_sma_200": ta.trend.price_above_sma_200,
                    "golden_cross": ta.trend.golden_cross,
                    "death_cross": ta.trend.death_cross,
                    "adx": ta.trend.adx,
                    "adx_signal": ta.trend.adx_signal,

                    # Momentum
                    "rsi": ta.momentum.rsi,
                    "rsi_signal": ta.momentum.rsi_signal,
                    "rsi_weighted_signal": ta.momentum.rsi_weighted_signal,
                    "rsi_weight": ta.momentum.rsi_weight,
                    "macd": ta.momentum.macd,
                    "macd_signal": ta.momentum.macd_signal,
                    "macd_histogram": ta.momentum.macd_histogram,
                    "macd_cross": ta.momentum.macd_cross,
                    "stoch_k": ta.momentum.stoch_k,
                    "stoch_d": ta.momentum.stoch_d,
                    "stoch_signal": ta.momentum.stoch_signal,
                    "roc": ta.momentum.roc,
                    "roc_signal": ta.momentum.roc_signal,

                    # Volatility
                    "bb_upper": ta.volatility.bb_upper,
                    "bb_middle": ta.volatility.bb_middle,
                    "bb_lower": ta.volatility.bb_lower,
                    "bb_signal": ta.volatility.bb_signal,
                    "price_position": ta.volatility.price_position,
                    "atr": ta.volatility.atr,
                    "atr_percent": ta.volatility.atr_percent,
                    "volatility_level": ta.volatility.volatility_level,

                    # Volume
                    "current_volume": ta.volume.current_volume,
                    "avg_volume_20d": ta.volume.avg_volume_20d,
                    "volume_ratio": ta.volume.volume_ratio,
                    "volume_signal": ta.volume.volume_signal,
                    "obv": ta.volume.obv,
                    "obv_trend": ta.volume.obv_trend,

                    # Support/Resistance
                    "pivot": ta.support_resistance.pivot,
                    "resistance_1": ta.support_resistance.resistance_1,
                    "resistance_2": ta.support_resistance.resistance_2,
                    "resistance_3": ta.support_resistance.resistance_3,
                    "support_1": ta.support_resistance.support_1,
                    "support_2": ta.support_resistance.support_2,
                    "support_3": ta.support_resistance.support_3,
                    "support_levels": ta.support_resistance.support_levels,
                    "resistance_levels": ta.support_resistance.resistance_levels,
                    "nearest_support": ta.support_resistance.nearest_support,
                    "nearest_resistance": ta.support_resistance.nearest_resistance,
                    "support_distance_pct": ta.support_resistance.support_distance_pct,
                    "resistance_distance_pct": ta.support_resistance.resistance_distance_pct,

                    # Patterns
                    "patterns": ta.patterns.patterns,

                    # Overall signal
                    "overall_signal": ta.overall_signal,
                    "signal_confidence": ta.signal_confidence,

                    # Multi-timeframe analysis
                    "multi_timeframe": {
                        "primary_trend": {
                            "timeframe": ta.multi_timeframe.primary_trend.timeframe,
                            "trend_direction": ta.multi_timeframe.primary_trend.trend_direction,
                            "trend_strength": ta.multi_timeframe.primary_trend.trend_strength,
                            "ema_200_trend": ta.multi_timeframe.primary_trend.ema_200_trend,
                            "momentum_signal": ta.multi_timeframe.primary_trend.momentum_signal,
                            "entry_signal": ta.multi_timeframe.primary_trend.entry_signal,
                        } if ta.multi_timeframe.primary_trend else None,
                        "confirmation_trend": {
                            "timeframe": ta.multi_timeframe.confirmation_trend.timeframe,
                            "trend_direction": ta.multi_timeframe.confirmation_trend.trend_direction,
                            "trend_strength": ta.multi_timeframe.confirmation_trend.trend_strength,
                            "ema_200_trend": ta.multi_timeframe.confirmation_trend.ema_200_trend,
                            "momentum_signal": ta.multi_timeframe.confirmation_trend.momentum_signal,
                            "entry_signal": ta.multi_timeframe.confirmation_trend.entry_signal,
                        } if ta.multi_timeframe.confirmation_trend else None,
                        "execution_trend": {
                            "timeframe": ta.multi_timeframe.execution_trend.timeframe,
                            "trend_direction": ta.multi_timeframe.execution_trend.trend_direction,
                            "trend_strength": ta.multi_timeframe.execution_trend.trend_strength,
                            "ema_200_trend": ta.multi_timeframe.execution_trend.ema_200_trend,
                            "momentum_signal": ta.multi_timeframe.execution_trend.momentum_signal,
                            "entry_signal": ta.multi_timeframe.execution_trend.entry_signal,
                        } if ta.multi_timeframe.execution_trend else None,
                        "trend_alignment": ta.multi_timeframe.trend_alignment,
                        "signal_quality": ta.multi_timeframe.signal_quality,
                        "recommended_action": ta.multi_timeframe.recommended_action,
                        "confidence": ta.multi_timeframe.confidence,
                    },

                    # Beta analysis
                    "beta_analysis": {
                        "beta": ta.beta_analysis.beta,
                        "benchmark": ta.beta_analysis.benchmark,
                        "correlation": ta.beta_analysis.correlation,
                        "alpha": ta.beta_analysis.alpha,
                        "r_squared": ta.beta_analysis.r_squared,
                        "volatility_vs_market": ta.beta_analysis.volatility_vs_market,
                        "risk_profile": ta.beta_analysis.risk_profile,
                    },

                    # Entry Analysis (comprehensive)
                    "entry_analysis": {
                        "range_position_pct": ta.entry_analysis.range_position_pct,
                        "range_position_zone": ta.entry_analysis.range_position_zone,
                        "confluence_score": ta.entry_analysis.confluence_score,
                        "confluence_factors": ta.entry_analysis.confluence_factors,
                        "suggested_stop_loss": ta.entry_analysis.suggested_stop_loss,
                        "stop_loss_type": ta.entry_analysis.stop_loss_type,
                        "stop_loss_distance_pct": ta.entry_analysis.stop_loss_distance_pct,
                        "suggested_target": ta.entry_analysis.suggested_target,
                        "target_distance_pct": ta.entry_analysis.target_distance_pct,
                        "risk_reward_ratio": ta.entry_analysis.risk_reward_ratio,
                        "risk_reward_quality": ta.entry_analysis.risk_reward_quality,
                        "is_good_entry": ta.entry_analysis.is_good_entry,
                        "entry_quality": ta.entry_analysis.entry_quality,
                        "entry_quality_score": ta.entry_analysis.entry_quality_score,
                        "suggested_entry_price": ta.entry_analysis.suggested_entry_price,
                        "suggested_entry_zone_low": ta.entry_analysis.suggested_entry_zone_low,
                        "suggested_entry_zone_high": ta.entry_analysis.suggested_entry_zone_high,
                        "wait_for_pullback": ta.entry_analysis.wait_for_pullback,
                        "entry_reasoning": ta.entry_analysis.entry_reasoning,
                        "warning_signals": ta.entry_analysis.warning_signals,
                    },

                    # Chart data
                    "chart_data": ta.chart_data,
                })
                logger.info("Added comprehensive technical analysis to result", ticker=ticker, signal=ta.overall_signal)

            # Step 8: Risk Assessment (85%)
            risk_assessment_result = None
            await set_job_progress(job_id, "running", 85, "Running risk assessment...")
            await update_job_status(job_id, ticker, "running", 85, "Running risk assessment...")

            try:
                from backend.app.agents.risk_assessment_agent import RiskAssessmentAgent

                risk_agent = RiskAssessmentAgent()

                # Prepare growth analysis data for risk assessment
                growth_data_for_risk = None
                if 'composite_score' in result:
                    growth_data_for_risk = {
                        "composite_score": result.get("composite_score"),
                        "fundamental_score": result.get("fundamental_score"),
                        "sentiment_score": result.get("sentiment_score"),
                        "technical_score": result.get("technical_score"),
                        "competitive_score": result.get("competitive_score"),
                        "risk_score": result.get("risk_score"),
                        "risk_level": result.get("risk_level"),
                        "upside_potential": result.get("upside_potential"),
                        "key_strengths": result.get("key_strengths", []),
                        "key_risks": result.get("key_risks", []),
                        "data_completeness_score": result.get("data_completeness_score"),
                        # Valuation data for decision-making
                        "price_target_base": result.get("price_target_base"),
                        "price_target_method": result.get("price_target_method"),
                        # Valuation Analysis results (if available)
                        "intrinsic_value": result.get("valuation_analysis", {}).get("intrinsic_value") if result.get("valuation_analysis") else None,
                        "margin_of_safety": result.get("valuation_analysis", {}).get("margin_of_safety") if result.get("valuation_analysis") else None,
                        "valuation_status": result.get("valuation_analysis", {}).get("valuation_status") if result.get("valuation_analysis") else None,
                    }

                # Get technical analysis data (already serialized format)
                tech_data_for_risk = result.get("technical_analysis")

                risk_assessment_result = await risk_agent.analyze(
                    ticker=ticker,
                    technical_analysis=tech_data_for_risk,
                    growth_analysis=growth_data_for_risk,
                    stock_info=stock_info,
                )

                logger.info(
                    "Risk assessment completed",
                    ticker=ticker,
                    risk_score=risk_assessment_result.risk_score,
                    decision=risk_assessment_result.investment_decision
                )

            except Exception as e:
                logger.warning("Risk assessment failed", ticker=ticker, error=str(e))
                import traceback
                logger.warning("Risk assessment traceback", traceback=traceback.format_exc())

            # Step 8b: Add risk assessment to result
            if risk_assessment_result:
                ra = risk_assessment_result
                result["risk_assessment"] = clean_nan({
                    # Basic info
                    "ticker": ra.ticker,
                    "assessment_date": ra.assessment_date.isoformat(),
                    "current_price": ra.current_price,

                    # Main Risk Score
                    "risk_score": ra.risk_score,
                    "risk_level": ra.risk_level,

                    # Weighted subscores
                    "market_structure_weighted": ra.market_structure_weighted,
                    "momentum_weighted": ra.momentum_weighted,
                    "overextension_penalty_weighted": ra.overextension_penalty_weighted,
                    "volatility_penalty_weighted": ra.volatility_penalty_weighted,
                    "volume_confirmation_weighted": ra.volume_confirmation_weighted,

                    # Subscore breakdown
                    "subscore_breakdown": {
                        # Market structure
                        "support_proximity_score": ra.subscore_breakdown.support_proximity_score,
                        "resistance_distance_score": ra.subscore_breakdown.resistance_distance_score,
                        "trend_alignment_score": ra.subscore_breakdown.trend_alignment_score,
                        "market_structure_total": ra.subscore_breakdown.market_structure_total,
                        # Momentum
                        "macd_momentum_score": ra.subscore_breakdown.macd_momentum_score,
                        "rsi_direction_score": ra.subscore_breakdown.rsi_direction_score,
                        "momentum_total": ra.subscore_breakdown.momentum_total,
                        # Overextension
                        "rsi_overbought_penalty": ra.subscore_breakdown.rsi_overbought_penalty,
                        "bollinger_penalty": ra.subscore_breakdown.bollinger_penalty,
                        "ema_distance_penalty": ra.subscore_breakdown.ema_distance_penalty,
                        "overextension_total": ra.subscore_breakdown.overextension_total,
                        # Volatility
                        "atr_volatility_penalty": ra.subscore_breakdown.atr_volatility_penalty,
                        "stop_distance_penalty": ra.subscore_breakdown.stop_distance_penalty,
                        "volatility_total": ra.subscore_breakdown.volatility_total,
                        # Volume
                        "volume_ratio_score": ra.subscore_breakdown.volume_ratio_score,
                        "volume_total": ra.subscore_breakdown.volume_total,
                    },

                    # MFTA
                    "mfta_multiplier": ra.mfta_multiplier,
                    "mfta_alignment": ra.mfta_alignment,
                    "pre_mfta_score": ra.pre_mfta_score,

                    # Risk/Reward Analysis
                    "risk_reward": {
                        "current_price": ra.risk_reward.current_price,
                        "nearest_support": ra.risk_reward.nearest_support,
                        "nearest_resistance": ra.risk_reward.nearest_resistance,
                        "risk_distance_pct": ra.risk_reward.risk_distance_pct,
                        "reward_distance_pct": ra.risk_reward.reward_distance_pct,
                        "risk_reward_ratio": ra.risk_reward.risk_reward_ratio,
                        "is_favorable": ra.risk_reward.is_favorable,
                        "suggested_entry": ra.risk_reward.suggested_entry,
                        "suggested_stop": ra.risk_reward.suggested_stop,
                        "suggested_target": ra.risk_reward.suggested_target,
                    },

                    # Investment Decision
                    "investment_decision": ra.investment_decision,
                    "decision_confidence": ra.decision_confidence,
                    "entry_quality": ra.entry_quality,
                    "decision_composite_score": ra.decision_composite_score,
                    "decision_components": ra.decision_components,

                    # Key Factors
                    "bullish_factors": ra.bullish_factors,
                    "bearish_factors": ra.bearish_factors,
                    "key_risks": ra.key_risks,

                    # Analysis
                    "summary": ra.summary,
                    "detailed_analysis": ra.detailed_analysis,
                    "position_sizing_suggestion": ra.position_sizing_suggestion,

                    # Data Sources
                    "data_sources": ra.data_sources,
                })
                data_sources["risk_assessment"] = {"type": "agent", "name": "risk_assessment_agent"}
                logger.info("Added risk assessment to result", ticker=ticker, decision=ra.investment_decision)

            # Step 9: Save to database (90%)
            await set_job_progress(job_id, "running", 90, "Saving results...")

            result["data_sources"] = data_sources
            analysis_id = await save_analysis_to_db(result)
            result["analysis_id"] = analysis_id

            # Step 8: Add sector comparison (95%)
            if result.get("sector"):
                await set_job_progress(job_id, "running", 95, "Calculating sector comparison...")
                await update_job_status(job_id, ticker, "running", 95, "Calculating sector comparison...")

                try:
                    from backend.app.services.sector_comparison import get_sector_comparison_service
                    sector_service = get_sector_comparison_service()
                    sector_comp = await sector_service.compare_stock_to_sector(
                        ticker=ticker,
                        sector=result["sector"],
                        lookback_days=180
                    )
                    result["sector_comparison"] = sector_comp
                    logger.info("Added sector comparison", ticker=ticker, sector=result["sector"])
                except Exception as e:
                    logger.warning("Failed to add sector comparison", ticker=ticker, error=str(e))
                    # Don't fail the entire job if sector comparison fails
                    result["sector_comparison"] = None

            # Complete - clean result for JSON serialization
            cleaned_result = clean_nan(result)
            await set_job_progress(job_id, "completed", 100, "Research completed", result=cleaned_result)
            await update_job_status(job_id, ticker, "completed", 100, "Research completed", result_data=cleaned_result)

            logger.info("Stock research completed", ticker=ticker, job_id=job_id)
            return result

        except Exception as e:
            logger.error("Stock research failed", ticker=ticker, error=str(e))
            suggestion = generate_error_suggestion(str(e))
            await set_job_progress(job_id, "failed", 0, str(e))
            await update_job_status(job_id, ticker, "failed", 0, str(e), suggestion)
            raise

    return run_async(run())


async def update_job_status(
    job_id: str,
    ticker: str,
    status: str,
    progress: int,
    current_step: str,
    error_suggestion: str | None = None,
    result_data: dict | None = None,
) -> None:
    """Update research job status in database."""
    from datetime import datetime
    from sqlalchemy import select

    async with async_session_factory() as session:
        stmt = select(ResearchJob).where(ResearchJob.job_id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if job:
            job.status = status
            job.progress = progress
            job.current_step = current_step
            if status == "running" and not job.started_at:
                job.started_at = datetime.utcnow()
            if status in ("completed", "failed"):
                job.completed_at = datetime.utcnow()
            if error_suggestion:
                job.error_suggestion = error_suggestion
            if result_data:
                job.result_data = result_data
        else:
            job = ResearchJob(
                job_id=job_id,
                job_type="stock_research",
                status=status,
                progress=progress,
                current_step=current_step,
                input_data={"ticker": ticker},
                result_data=result_data,
                started_at=datetime.utcnow() if status == "running" else None,
            )
            session.add(job)

        await session.commit()


def calculate_technical_indicators(prices: list[dict]) -> dict[str, Any]:
    """Calculate technical indicators from price data."""
    if not prices or len(prices) < 14:
        return {}

    closes = [float(p["close"]) for p in prices]

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
            result["rsi"] = Decimal(str(round(100 - (100 / (1 + rs)), 2)))
        else:
            result["rsi"] = Decimal("100")

    # Moving averages
    if len(closes) >= 20:
        result["sma_20"] = Decimal(str(round(sum(closes[-20:]) / 20, 2)))
    if len(closes) >= 50:
        result["sma_50"] = Decimal(str(round(sum(closes[-50:]) / 50, 2)))

    # Bollinger Bands (20-day)
    if len(closes) >= 20:
        sma = sum(closes[-20:]) / 20
        variance = sum((x - sma) ** 2 for x in closes[-20:]) / 20
        std = variance ** 0.5
        result["bollinger_upper"] = Decimal(str(round(sma + 2 * std, 2)))
        result["bollinger_lower"] = Decimal(str(round(sma - 2 * std, 2)))

    return result


def calculate_change(current: Any, previous: Any) -> Decimal | None:
    """Calculate percentage change."""
    if current is None or previous is None or previous == 0:
        return None
    try:
        change = (float(current) - float(previous)) / float(previous)
        return Decimal(str(round(change, 4)))
    except Exception:
        return None


async def run_ai_analysis(ticker: str, data: dict, llm_model: str | None = None) -> dict[str, Any]:
    """Run AI analysis on stock data.

    Args:
        ticker: Stock ticker symbol
        data: Stock data dictionary
        llm_model: Optional Ollama model to use (defaults to settings.ollama_model)
    """
    import os
    from ollama import Client
    import json
    from backend.app.config import get_settings

    settings = get_settings()
    model_to_use = llm_model if llm_model else settings.ollama_model

    # Use OLLAMA_BASE_URL from settings, or OLLAMA_HOST env var as fallback
    ollama_url = settings.ollama_base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    client = Client(host=ollama_url)

    context = f"""
    Analyze the following stock data for {ticker} and provide an investment recommendation.

    Company: {data.get('company_name', 'Unknown')}
    Sector: {data.get('sector', 'Unknown')}
    Industry: {data.get('industry', 'Unknown')}

    Current Price: ${data.get('current_price', 'N/A')}
    Market Cap: ${data.get('market_cap', 0):,}

    Valuation Metrics:
    - P/E Ratio: {data.get('pe_ratio', 'N/A')}
    - Forward P/E: {data.get('forward_pe', 'N/A')}
    - PEG Ratio: {data.get('peg_ratio', 'N/A')}
    - Price to Book: {data.get('price_to_book', 'N/A')}

    Technical Indicators:
    - RSI (14): {data.get('rsi', 'N/A')}
    - 20-day SMA: ${data.get('sma_20', 'N/A')}

    Provide:
    1. Recommendation: strong_buy, buy, hold, sell, or strong_sell
    2. Confidence score (0-1)
    3. Detailed reasoning (2-3 sentences)
    4. Top 3 risks
    5. Top 3 opportunities

    Respond in JSON format:
    {{
        "recommendation": "hold",
        "confidence_score": 0.7,
        "recommendation_reasoning": "...",
        "risks": ["risk1", "risk2", "risk3"],
        "opportunities": ["opp1", "opp2", "opp3"]
    }}
    """

    try:
        logger.info("Running AI analysis", ticker=ticker, model=model_to_use, ollama_url=ollama_url)
        response = client.chat(
            model=model_to_use,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst providing objective stock analysis. Respond only with valid JSON.",
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
        logger.error("AI analysis failed", error=str(e), model=model_to_use, ollama_url=ollama_url)

    return {
        "recommendation": "hold",
        "confidence_score": 0.5,
        "recommendation_reasoning": "Unable to complete AI analysis.",
        "risks": [],
        "opportunities": [],
    }


async def save_analysis_to_db(data: dict) -> int:
    """Save stock analysis to database."""
    from sqlalchemy import select

    async with async_session_factory() as session:
        today = date.today()
        ticker = data["ticker"]

        # Check for existing analysis today
        stmt = select(StockAnalysis).where(
            StockAnalysis.ticker == ticker,
            StockAnalysis.analysis_date == today,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            for key, value in data.items():
                if hasattr(existing, key) and key != "ticker":
                    setattr(existing, key, value)
            analysis_id = existing.id
        else:
            analysis = StockAnalysis(
                ticker=ticker,
                analysis_date=today,
                **{k: v for k, v in data.items() if k != "ticker" and hasattr(StockAnalysis, k)},
            )
            session.add(analysis)
            await session.flush()
            analysis_id = analysis.id

        await session.commit()
        return analysis_id


def generate_error_suggestion(error: str) -> str:
    """Generate AI-powered error suggestion."""
    error_lower = error.lower()

    if "rate limit" in error_lower:
        return "The API rate limit was exceeded. Wait a few minutes and try again, or upgrade your API plan for higher limits."
    elif "api key" in error_lower:
        return "Check that your API keys are correctly configured in the .env file and have not expired."
    elif "timeout" in error_lower:
        return "The request timed out. This may be due to network issues or high server load. Try again in a few moments."
    elif "not found" in error_lower:
        return "The stock ticker may be invalid or delisted. Verify the ticker symbol is correct."
    else:
        return "An unexpected error occurred. Check the logs for more details or contact support."
