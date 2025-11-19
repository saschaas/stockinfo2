"""Report generation API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundException
from backend.app.db.models import StockAnalysis, MarketSentiment
from backend.app.db.session import get_db

router = APIRouter()


@router.get("/stock/{ticker}")
async def get_stock_report(
    ticker: Annotated[str, Path(min_length=1, max_length=10)],
    format: str = Query(default="html", pattern="^(html|pdf)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a comprehensive stock analysis report.

    Returns either HTML preview or PDF download.
    """
    ticker = ticker.upper()

    # Get latest analysis
    stmt = (
        select(StockAnalysis)
        .where(StockAnalysis.ticker == ticker)
        .order_by(StockAnalysis.analysis_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise NotFoundException("Stock analysis", ticker)

    # Generate report content
    html_content = _generate_stock_report_html(analysis)

    if format == "html":
        return Response(
            content=html_content,
            media_type="text/html",
        )
    else:
        # Generate PDF using WeasyPrint
        # TODO: Implement PDF generation
        pdf_content = b"PDF generation not yet implemented"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{ticker}_report.pdf"'
            },
        )


@router.get("/market")
async def get_market_report(
    format: str = Query(default="html", pattern="^(html|pdf)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a market sentiment report."""
    # Get latest sentiment
    stmt = select(MarketSentiment).order_by(MarketSentiment.date.desc()).limit(1)
    result = await db.execute(stmt)
    sentiment = result.scalar_one_or_none()

    if not sentiment:
        return Response(
            content="<h1>No market sentiment data available</h1>",
            media_type="text/html",
        )

    html_content = _generate_market_report_html(sentiment)

    if format == "html":
        return Response(
            content=html_content,
            media_type="text/html",
        )
    else:
        pdf_content = b"PDF generation not yet implemented"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="market_report_{sentiment.date}.pdf"'
            },
        )


def _fmt(val, fmt: str = ".2f", prefix: str = "", suffix: str = "") -> str:
    """Format a numeric value or return N/A if None."""
    if val is None:
        return "N/A"
    return f"{prefix}{float(val):{fmt}}{suffix}"


def _fmt_pct(val) -> str:
    """Format a value as percentage."""
    if val is None:
        return "N/A"
    return f"{float(val)*100:.2f}%"


def _pct_class(val) -> str:
    """Return CSS class based on positive/negative value."""
    if val and val > 0:
        return "positive"
    return "negative"


def _generate_stock_report_html(analysis: StockAnalysis) -> str:
    """Generate HTML report for stock analysis."""
    recommendation_colors = {
        "strong_buy": "#22c55e",
        "buy": "#84cc16",
        "hold": "#eab308",
        "sell": "#f97316",
        "strong_sell": "#ef4444",
    }

    rec_color = recommendation_colors.get(analysis.recommendation or "", "#666")

    # Pre-format values to avoid f-string issues
    confidence = _fmt(analysis.confidence_score, ".1f", suffix="%") if analysis.confidence_score else "N/A"
    if analysis.confidence_score:
        confidence = f"{float(analysis.confidence_score)*100:.1f}%"

    pe_ratio = _fmt(analysis.pe_ratio)
    forward_pe = _fmt(analysis.forward_pe)
    peg_ratio = _fmt(analysis.peg_ratio)
    price_to_book = _fmt(analysis.price_to_book)
    debt_to_equity = _fmt(analysis.debt_to_equity)
    market_cap = f"${analysis.market_cap/1e9:.1f}B" if analysis.market_cap else "N/A"
    rsi = _fmt(analysis.rsi, ".1f")
    macd = _fmt(analysis.macd)
    current_price = _fmt(analysis.current_price, ".2f", prefix="$")
    target_price = _fmt(analysis.target_price_6m, ".2f", prefix="$")

    change_1d = _fmt_pct(analysis.price_change_1d)
    change_1w = _fmt_pct(analysis.price_change_1w)
    change_1m = _fmt_pct(analysis.price_change_1m)
    change_ytd = _fmt_pct(analysis.price_change_ytd)

    class_1d = _pct_class(analysis.price_change_1d)
    class_1w = _pct_class(analysis.price_change_1w)
    class_1m = _pct_class(analysis.price_change_1m)
    class_ytd = _pct_class(analysis.price_change_ytd)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{analysis.ticker} Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
            h2 {{ color: #374151; margin-top: 30px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; }}
            .recommendation {{
                font-size: 24px;
                font-weight: bold;
                color: {rec_color};
                text-transform: uppercase;
            }}
            .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
            .metric {{ background: #f3f4f6; padding: 15px; border-radius: 8px; }}
            .metric-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
            .metric-value {{ font-size: 20px; font-weight: bold; margin-top: 5px; }}
            .reasoning {{ background: #eff6ff; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            .confidence {{ font-size: 14px; color: #6b7280; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
            th {{ background: #f9fafb; font-weight: 600; }}
            .positive {{ color: #22c55e; }}
            .negative {{ color: #ef4444; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>{analysis.ticker} - {analysis.company_name or 'Stock Analysis'}</h1>
                <p>Sector: {analysis.sector or 'N/A'} | Industry: {analysis.industry or 'N/A'}</p>
                <p>Analysis Date: {analysis.analysis_date}</p>
            </div>
            <div>
                <div class="recommendation">{analysis.recommendation or 'N/A'}</div>
                <div class="confidence">Confidence: {confidence}</div>
            </div>
        </div>

        <h2>Valuation Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">P/E Ratio</div>
                <div class="metric-value">{pe_ratio}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Forward P/E</div>
                <div class="metric-value">{forward_pe}</div>
            </div>
            <div class="metric">
                <div class="metric-label">PEG Ratio</div>
                <div class="metric-value">{peg_ratio}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Price to Book</div>
                <div class="metric-value">{price_to_book}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Debt to Equity</div>
                <div class="metric-value">{debt_to_equity}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Market Cap</div>
                <div class="metric-value">{market_cap}</div>
            </div>
        </div>

        <h2>Technical Indicators</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">RSI (14)</div>
                <div class="metric-value">{rsi}</div>
            </div>
            <div class="metric">
                <div class="metric-label">MACD</div>
                <div class="metric-value">{macd}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Current Price</div>
                <div class="metric-value">{current_price}</div>
            </div>
        </div>

        <h2>Price Performance</h2>
        <table>
            <tr>
                <th>Period</th>
                <th>Change</th>
            </tr>
            <tr>
                <td>1 Day</td>
                <td class="{class_1d}">{change_1d}</td>
            </tr>
            <tr>
                <td>1 Week</td>
                <td class="{class_1w}">{change_1w}</td>
            </tr>
            <tr>
                <td>1 Month</td>
                <td class="{class_1m}">{change_1m}</td>
            </tr>
            <tr>
                <td>YTD</td>
                <td class="{class_ytd}">{change_ytd}</td>
            </tr>
        </table>

        <h2>6-Month Price Target</h2>
        <p style="font-size: 24px; font-weight: bold;">{target_price}</p>

        <h2>Investment Reasoning</h2>
        <div class="reasoning">
            {analysis.recommendation_reasoning or 'No reasoning available.'}
        </div>

        <p style="margin-top: 40px; font-size: 12px; color: #9ca3af;">
            Generated by Stock Research Tool | {analysis.created_at}
        </p>
    </body>
    </html>
    """

    return html


def _generate_market_report_html(sentiment: MarketSentiment) -> str:
    """Generate HTML report for market sentiment."""
    # Pre-format values
    sp500_close = f"{float(sentiment.sp500_close):,.2f}" if sentiment.sp500_close else "N/A"
    sp500_change = _fmt_pct(sentiment.sp500_change_pct)
    sp500_class = _pct_class(sentiment.sp500_change_pct)

    nasdaq_close = f"{float(sentiment.nasdaq_close):,.2f}" if sentiment.nasdaq_close else "N/A"
    nasdaq_change = _fmt_pct(sentiment.nasdaq_change_pct)
    nasdaq_class = _pct_class(sentiment.nasdaq_change_pct)

    dow_close = f"{float(sentiment.dow_close):,.2f}" if sentiment.dow_close else "N/A"
    dow_change = _fmt_pct(sentiment.dow_change_pct)
    dow_class = _pct_class(sentiment.dow_change_pct)

    overall = f"{float(sentiment.overall_sentiment)*100:.0f}%" if sentiment.overall_sentiment else "N/A"
    overall_class = "positive" if sentiment.overall_sentiment and sentiment.overall_sentiment > 0.5 else "negative"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Market Sentiment Report - {sentiment.date}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
            h2 {{ color: #374151; margin-top: 30px; }}
            .indices {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
            .index {{ background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; }}
            .index-name {{ font-size: 14px; color: #6b7280; }}
            .index-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
            .positive {{ color: #22c55e; }}
            .negative {{ color: #ef4444; }}
            .sentiment-score {{ font-size: 48px; font-weight: bold; text-align: center; margin: 30px 0; }}
        </style>
    </head>
    <body>
        <h1>Market Sentiment Report</h1>
        <p>Date: {sentiment.date}</p>

        <h2>Major Indices</h2>
        <div class="indices">
            <div class="index">
                <div class="index-name">S&P 500</div>
                <div class="index-value">{sp500_close}</div>
                <div class="{sp500_class}">
                    {sp500_change}
                </div>
            </div>
            <div class="index">
                <div class="index-name">NASDAQ</div>
                <div class="index-value">{nasdaq_close}</div>
                <div class="{nasdaq_class}">
                    {nasdaq_change}
                </div>
            </div>
            <div class="index">
                <div class="index-name">Dow Jones</div>
                <div class="index-value">{dow_close}</div>
                <div class="{dow_class}">
                    {dow_change}
                </div>
            </div>
        </div>

        <h2>Overall Sentiment</h2>
        <div class="sentiment-score {overall_class}">
            {overall}
        </div>

        <p style="margin-top: 40px; font-size: 12px; color: #9ca3af;">
            Generated by Stock Research Tool | {sentiment.created_at}
        </p>
    </body>
    </html>
    """

    return html
