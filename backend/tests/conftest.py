"""Pytest fixtures for testing."""

import asyncio
from decimal import Decimal
from datetime import date, datetime
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app.main import app
from backend.app.db.session import Base, get_db
from backend.app.db.models import Fund, MarketSentiment, StockAnalysis


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

# Create test session factory
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with test_session_factory() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_fund(db_session: AsyncSession) -> Fund:
    """Create a sample fund for testing."""
    fund = Fund(
        name="Test Technology ETF",
        ticker="TEST",
        cik="0001234567",
        category="tech_focused",
        priority=1,
    )
    db_session.add(fund)
    await db_session.commit()
    await db_session.refresh(fund)
    return fund


@pytest_asyncio.fixture
async def sample_sentiment(db_session: AsyncSession) -> MarketSentiment:
    """Create sample market sentiment for testing."""
    sentiment = MarketSentiment(
        date=date.today(),
        sp500_close=Decimal("4500.00"),
        sp500_change_pct=Decimal("0.0150"),
        nasdaq_close=Decimal("14000.00"),
        nasdaq_change_pct=Decimal("0.0200"),
        dow_close=Decimal("35000.00"),
        dow_change_pct=Decimal("0.0100"),
        overall_sentiment=Decimal("0.65"),
        bullish_score=Decimal("0.70"),
        bearish_score=Decimal("0.30"),
        hot_sectors=[{"name": "Technology"}, {"name": "Healthcare"}],
        negative_sectors=[{"name": "Energy"}],
        top_news=[{"title": "Test News", "source": "Test"}],
        news_count=1,
    )
    db_session.add(sentiment)
    await db_session.commit()
    await db_session.refresh(sentiment)
    return sentiment


@pytest_asyncio.fixture
async def sample_analysis(db_session: AsyncSession) -> StockAnalysis:
    """Create sample stock analysis for testing."""
    analysis = StockAnalysis(
        ticker="AAPL",
        analysis_date=date.today(),
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        pe_ratio=Decimal("28.50"),
        forward_pe=Decimal("25.00"),
        peg_ratio=Decimal("1.80"),
        price_to_book=Decimal("45.00"),
        debt_to_equity=Decimal("1.50"),
        market_cap=2800000000000,
        rsi=Decimal("55.00"),
        macd=Decimal("2.50"),
        sma_20=Decimal("175.00"),
        sma_50=Decimal("170.00"),
        current_price=Decimal("180.00"),
        target_price_6m=Decimal("200.00"),
        price_change_1d=Decimal("0.0150"),
        recommendation="buy",
        confidence_score=Decimal("0.75"),
        recommendation_reasoning="Strong fundamentals with growth potential.",
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)
    return analysis
