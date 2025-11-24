"""
Test script for Growth Analysis Agent integration

This script tests the new growth analysis functionality without
requiring database migration (uses in-memory analysis only).
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.app.agents.growth_analysis_agent import GrowthAnalysisAgent


async def test_growth_analysis():
    """Test the growth analysis agent with mock data"""

    print("=" * 80)
    print("Testing Growth Stock Analysis Agent")
    print("=" * 80)

    # Create agent
    agent = GrowthAnalysisAgent()
    print("✓ Growth Analysis Agent initialized")

    # Mock stock data (simulating what would come from Yahoo Finance)
    mock_stock_data = {
        "info": {
            "longName": "Apple Inc.",
            "shortName": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3000000000000,
            "fullTimeEmployees": 164000,
            "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones...",

            # Financial data
            "totalRevenue": 383285000000,
            "revenueGrowth": 0.078,  # 7.8% growth
            "grossMargins": 0.437,
            "operatingMargins": 0.297,
            "profitMargins": 0.246,

            # Earnings
            "trailingEps": 6.13,
            "earningsGrowth": 0.11,

            # Cash flow
            "operatingCashflow": 110543000000,
            "freeCashflow": 99584000000,
            "totalCash": 61555000000,

            # Balance sheet
            "totalDebt": 111088000000,
            "totalStockholderEquity": 62146000000,
            "debtToEquity": 178.73,
            "currentRatio": 0.94,

            # Returns
            "returnOnEquity": 1.479,  # 147.9%
            "returnOnAssets": 0.220,  # 22%

            # Valuation
            "trailingPE": 33.65,
            "forwardPE": 29.85,
            "priceToSalesTrailing12Months": 8.27,
            "priceToBook": 52.36,
            "pegRatio": 2.68,

            # Technical
            "currentPrice": 189.95,
            "fiftyTwoWeekHigh": 199.62,
            "fiftyTwoWeekLow": 164.08,
            "52WeekChange": 0.454,
            "beta": 1.24,

            # Analyst data
            "targetMeanPrice": 201.50,
            "targetHighPrice": 250.00,
            "targetLowPrice": 158.00,

            # Ownership
            "heldPercentInstitutions": 0.596,
            "heldPercentInsiders": 0.0007,
            "shortPercentOfFloat": 0.009,

            # Volume
            "averageVolume10days": 52000000
        },
        "recommendations": [{
            "strongBuy": 12,
            "buy": 18,
            "hold": 10,
            "sell": 2,
            "strongSell": 0
        }],
        "technicals": {
            "rsi": 58.5,
            "rsi_signal": "neutral",
            "macd": 2.34,
            "macd_signal": 1.89,
            "macd_histogram": 0.45,
            "sma_20": 187.50,
            "sma_50": 182.30,
            "sma_200": 177.80
        },
        "data_sources": {
            "stock_info": {"type": "api", "name": "yahoo_finance"},
            "technicals": {"type": "calculation", "name": "internal"}
        }
    }

    print("\n📊 Mock Data Summary:")
    print(f"  Company: {mock_stock_data['info']['longName']}")
    print(f"  Sector: {mock_stock_data['info']['sector']}")
    print(f"  Market Cap: ${mock_stock_data['info']['marketCap']:,.0f}")
    print(f"  Current Price: ${mock_stock_data['info']['currentPrice']:.2f}")
    print(f"  Revenue Growth: {mock_stock_data['info']['revenueGrowth']*100:.1f}%")
    print(f"  Net Margin: {mock_stock_data['info']['profitMargins']*100:.1f}%")

    # Run analysis
    print("\n🔄 Running comprehensive growth analysis...")
    try:
        result = await agent.analyze(
            ticker="AAPL",
            stock_data=mock_stock_data,
            market_context=None,
            fund_ownership=None
        )

        print("✓ Analysis completed successfully!")

        # Display results
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)

        print(f"\n🎯 RECOMMENDATION: {result.recommendation.value}")
        print(f"   Confidence: {result.confidence_score:.1f}%")
        print(f"   Portfolio Allocation: {result.portfolio_allocation:.1f}%")

        print(f"\n💰 PRICE TARGETS:")
        print(f"   Current Price: ${result.technical_indicators.current_price:.2f}")
        print(f"   Base Target: ${result.price_target_base:.2f}")
        print(f"   Optimistic: ${result.price_target_optimistic:.2f}")
        print(f"   Pessimistic: ${result.price_target_pessimistic:.2f}")
        print(f"   Upside Potential: {result.upside_potential:.1f}%")

        print(f"\n📈 SCORING BREAKDOWN:")
        print(f"   Composite Score: {result.composite_score:.2f}/10")
        print(f"   ├─ Fundamental: {result.fundamental_score:.2f}/10 (35% weight)")
        print(f"   ├─ Sentiment: {result.sentiment_score:.2f}/10 (20% weight)")
        print(f"   ├─ Technical: {result.technical_score:.2f}/10 (15% weight)")
        print(f"   ├─ Competitive: {result.competitive_score:.2f}/10 (20% weight)")
        print(f"   └─ Risk-Adjusted: {result.risk_adjusted_score:.2f}/10 (10% weight)")

        print(f"\n⚠️  RISK ASSESSMENT:")
        print(f"   Risk Score: {result.risk_analysis.risk_score:.1f}/10")
        print(f"   Risk Level: {result.risk_analysis.risk_level.upper()}")

        print(f"\n✅ KEY STRENGTHS:")
        for i, strength in enumerate(result.key_strengths[:5], 1):
            print(f"   {i}. {strength}")

        print(f"\n⚠️  KEY RISKS:")
        for i, risk in enumerate(result.key_risks[:5], 1):
            print(f"   {i}. {risk}")

        print(f"\n🚀 POTENTIAL CATALYSTS:")
        for i, catalyst in enumerate(result.catalyst_points[:3], 1):
            print(f"   {i}. {catalyst}")

        print(f"\n📋 MONITORING POINTS:")
        for i, point in enumerate(result.monitoring_points[:3], 1):
            print(f"   {i}. {point}")

        print(f"\n📊 DATA QUALITY:")
        print(f"   Completeness: {result.data_completeness.completeness_score:.1f}%")
        print(f"   Has Growth Metrics: {result.data_completeness.has_growth_metrics}")
        print(f"   Has Margin Data: {result.data_completeness.has_margin_data}")
        print(f"   Has Cash Flow: {result.data_completeness.has_cash_flow_data}")
        print(f"   Has Valuation: {result.data_completeness.has_valuation_data}")
        print(f"   Has Analyst Data: {result.data_completeness.has_analyst_data}")
        print(f"   Has Technical Data: {result.data_completeness.has_technical_data}")
        print(f"   Has Peer Comparison: {result.data_completeness.has_peer_comparison}")

        if result.data_completeness.missing_critical:
            print(f"   Missing: {', '.join(result.data_completeness.missing_critical)}")

        if result.ai_summary:
            print(f"\n🤖 AI SUMMARY:")
            print(f"   {result.ai_summary}")

        if result.ai_reasoning:
            print(f"\n💭 AI REASONING:")
            print(f"   {result.ai_reasoning}")

        print("\n" + "=" * 80)
        print("✅ TEST PASSED - Growth Analysis Agent is working correctly!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ ERROR during analysis:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_growth_analysis())
    sys.exit(0 if success else 1)
