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
) -> dict[str, Any]:
    """Perform comprehensive stock research.

    Args:
        ticker: Stock ticker symbol
        include_peers: Include peer comparison
        include_technical: Include technical analysis
        include_ai_analysis: Include AI-powered analysis

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
            if include_technical:
                await set_job_progress(job_id, "running", 50, "Calculating technical indicators...")
                await update_job_status(job_id, ticker, "running", 50, "Calculating technical indicators...")

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

            # Step 5: Growth Stock Analysis (80%)
            await set_job_progress(job_id, "running", 70, "Running growth stock analysis...")
            await update_job_status(job_id, ticker, "running", 70, "Running growth stock analysis...")

            try:
                from backend.app.agents.growth_analysis_agent import GrowthAnalysisAgent

                growth_agent = GrowthAnalysisAgent()

                # Prepare stock data for growth analysis
                stock_data_for_growth = {
                    "info": stock_info,
                    "technicals": technical if include_technical else {},
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
                })

                data_sources["growth_analysis"] = {"type": "ai", "name": "growth_analysis_agent"}

                logger.info("Growth analysis completed", ticker=ticker, composite_score=growth_result.composite_score)

            except Exception as e:
                logger.warning("Growth analysis failed", ticker=ticker, error=str(e))
                # Continue without growth analysis

            # Step 6: AI Analysis (90%)
            if include_ai_analysis:
                await set_job_progress(job_id, "running", 75, "Running AI analysis...")
                await update_job_status(job_id, ticker, "running", 75, "Running AI analysis...")

                ai_analysis = await run_ai_analysis(ticker, result)
                result.update(ai_analysis)
                data_sources["ai_analysis"] = {"type": "ai", "name": "ollama"}

            # Step 7: Save to database (100%)
            await set_job_progress(job_id, "running", 90, "Saving results...")

            result["data_sources"] = data_sources
            analysis_id = await save_analysis_to_db(result)
            result["analysis_id"] = analysis_id

            # Complete
            await set_job_progress(job_id, "completed", 100, "Research completed")
            await update_job_status(job_id, ticker, "completed", 100, "Research completed")

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
        else:
            job = ResearchJob(
                job_id=job_id,
                job_type="stock_research",
                status=status,
                progress=progress,
                current_step=current_step,
                input_data={"ticker": ticker},
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


async def run_ai_analysis(ticker: str, data: dict) -> dict[str, Any]:
    """Run AI analysis on stock data."""
    import ollama
    import json
    from backend.app.config import get_settings

    settings = get_settings()

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
        response = ollama.chat(
            model=settings.ollama_model,
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
        logger.error("AI analysis failed", error=str(e))

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
