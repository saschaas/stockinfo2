"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient
from decimal import Decimal

from backend.app.db.models import MarketSentiment, StockAnalysis, Fund


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestMarketEndpoints:
    """Test market sentiment endpoints."""

    @pytest.mark.asyncio
    async def test_get_sentiment_empty(self, client: AsyncClient):
        """Test get sentiment when no data exists."""
        response = await client.get("/api/v1/market/sentiment")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "overall_sentiment" in data

    @pytest.mark.asyncio
    async def test_get_sentiment_with_data(
        self,
        client: AsyncClient,
        sample_sentiment: MarketSentiment,
    ):
        """Test get sentiment with existing data."""
        response = await client.get("/api/v1/market/sentiment")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_sentiment"] == pytest.approx(0.65, rel=0.01)
        assert data["bullish_score"] == pytest.approx(0.70, rel=0.01)
        assert len(data["hot_sectors"]) == 2

    @pytest.mark.asyncio
    async def test_get_sentiment_history(self, client: AsyncClient):
        """Test get sentiment history."""
        response = await client.get("/api/v1/market/sentiment/history?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 7
        assert "history" in data


class TestStockEndpoints:
    """Test stock research endpoints."""

    @pytest.mark.asyncio
    async def test_get_stock_not_found(self, client: AsyncClient):
        """Test get stock analysis for non-existent ticker."""
        response = await client.get("/api/v1/stocks/INVALID")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stock_with_data(
        self,
        client: AsyncClient,
        sample_analysis: StockAnalysis,
    ):
        """Test get stock analysis with existing data."""
        response = await client.get("/api/v1/stocks/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["company_name"] == "Apple Inc."
        assert data["recommendation"] == "buy"
        assert data["confidence_score"] == pytest.approx(0.75, rel=0.01)

    @pytest.mark.asyncio
    async def test_start_research(self, client: AsyncClient):
        """Test starting a stock research job."""
        response = await client.post(
            "/api/v1/stocks/research",
            json={"ticker": "MSFT"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert data["status"] == "queued"
        assert "job_id" in data

    @pytest.mark.asyncio
    async def test_start_research_invalid_ticker(self, client: AsyncClient):
        """Test starting research with invalid ticker."""
        response = await client.post(
            "/api/v1/stocks/research",
            json={"ticker": ""},
        )
        assert response.status_code == 422  # Validation error


class TestFundEndpoints:
    """Test fund tracking endpoints."""

    @pytest.mark.asyncio
    async def test_list_funds_empty(self, client: AsyncClient):
        """Test list funds when none exist."""
        response = await client.get("/api/v1/funds/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_funds_with_data(
        self,
        client: AsyncClient,
        sample_fund: Fund,
    ):
        """Test list funds with existing data."""
        response = await client.get("/api/v1/funds/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["funds"][0]["name"] == "Test Technology ETF"

    @pytest.mark.asyncio
    async def test_get_fund_holdings_not_found(self, client: AsyncClient):
        """Test get holdings for non-existent fund."""
        response = await client.get("/api/v1/funds/999/holdings")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_fund_holdings(
        self,
        client: AsyncClient,
        sample_fund: Fund,
    ):
        """Test get holdings for existing fund."""
        response = await client.get(f"/api/v1/funds/{sample_fund.id}/holdings")
        assert response.status_code == 200
        data = response.json()
        assert data["fund_id"] == sample_fund.id
        assert data["fund_name"] == "Test Technology ETF"


class TestReportEndpoints:
    """Test report generation endpoints."""

    @pytest.mark.asyncio
    async def test_get_stock_report_not_found(self, client: AsyncClient):
        """Test get report for non-existent stock."""
        response = await client.get("/api/v1/reports/stock/INVALID")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stock_report_html(
        self,
        client: AsyncClient,
        sample_analysis: StockAnalysis,
    ):
        """Test get stock report as HTML."""
        response = await client.get("/api/v1/reports/stock/AAPL?format=html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Apple Inc." in response.text
