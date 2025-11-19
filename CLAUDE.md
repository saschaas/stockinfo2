# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Powered Stock Research Tool - full-stack application for market sentiment analysis, stock research, and fund tracking with AI-driven insights using FastAPI, React, Celery, and Ollama.

## Development Commands

### Running Services

```bash
# All services with Docker (recommended)
docker-compose up -d

# Individual services for development
make run-backend              # FastAPI on port 8000
make run-frontend             # React/Vite on port 3000
make run-celery               # Celery worker
make run-celery-beat          # Celery scheduler
make run-dagster              # Dagster UI on port 3001
```

### Testing

```bash
make test                     # Run all tests
make test-backend             # pytest backend/tests -v
make test-frontend            # npm test
make test-cov                 # pytest with HTML coverage report
```

### Code Quality

```bash
make lint                     # Run all linters
make format                   # Format all code
make type-check               # Run mypy
```

### Database

```bash
make db-init                  # Initialize with seed data
make db-migrate               # Create new Alembic migration
make db-upgrade               # Apply migrations
make db-reset                 # Reset and reapply all migrations
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │◄───►│  Backend API │◄───►│  PostgreSQL │
│  (React)    │     │  (FastAPI)   │     │             │
│  Port 80    │     │  Port 8000   │     │  Port 5432  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼────┐
        │   Redis   │ │ Celery │ │  Ollama │
        │   Cache   │ │ Worker │ │   LLM   │
        │  Port 6379│ │        │ │Port 11434│
        └───────────┘ └────────┘ └─────────┘
```

### Key Components

**Backend** (`backend/app/`):
- `api/routes/` - REST endpoints (stocks, market, funds, websocket)
- `tasks/` - Celery async tasks (research, market refresh, fund tracking)
- `services/` - External API clients (Alpha Vantage, Yahoo Finance, SEC EDGAR)
- `db/models.py` - SQLAlchemy ORM models (StockAnalysis, Fund, FundHolding, etc.)

**Frontend** (`frontend/src/`):
- `components/` - React components (Dashboard, StockResearch, FundTracker)
- `services/api.ts` - Axios HTTP client
- `hooks/useWebSocket.ts` - WebSocket for real-time progress

**AI Agents** (`agents/`):
- Langgraph-based multi-agent system
- Supervisor orchestrates: Market Sentiment, Stock Research, Investor Tracking, Analysis Engine

## Key Patterns

### Async Database Pattern
```python
async with async_session_factory() as session:
    stmt = select(Model).where(...)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

### Task Progress Tracking
Celery worker writes progress to Redis, WebSocket polls Redis every 500ms:
```python
await set_job_progress(job_id, "running", 50, "Analyzing...")
```

### Data Source Attribution
Every analysis includes source metadata:
```python
{"data_sources": {"price": {"type": "api", "name": "yahoo_finance"}}}
```

### Decimal Serialization
Use `to_float()` helper when returning database Decimal values via JSON/WebSocket.

## Configuration

- **Environment**: `.env` file (copy from `.env.example`)
- **Application config**: `config/config.yaml` (data sources, funds, thresholds)
- **API keys required**: `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`

## Data Flow

1. User submits research request → FastAPI creates job, sends to Celery
2. Celery worker fetches data from APIs (Yahoo, Alpha Vantage, SEC)
3. Worker calculates technicals, runs AI analysis via Ollama
4. Progress updates written to Redis → WebSocket polls → Frontend updates
5. Results stored in PostgreSQL → Returned to client

## Database Models

- `StockAnalysis` - Comprehensive stock analysis results
- `StockPrice` - Historical OHLCV data (partitioned by date)
- `Fund` - Tracked institutional funds (20 funds)
- `FundHolding` - 13F holdings per quarter
- `MarketSentiment` - Daily market sentiment scores
- `ResearchJob` - Async job tracking

## External APIs

- **Alpha Vantage**: Market data, technical indicators (30 req/min)
- **Yahoo Finance**: Fundamentals, prices (no key required)
- **SEC EDGAR**: 13F filings (10 req/sec)
- **Ollama**: Local LLM (llama3.2 or mistral)

## Docker Services

- `stockinfo-postgres` - PostgreSQL 15
- `stockinfo-redis` - Redis 7 (cache + broker)
- `stockinfo-backend` - FastAPI
- `stockinfo-celery-worker` - Task processor
- `stockinfo-celery-beat` - Scheduler
- `stockinfo-frontend` - React (nginx)
- `stockinfo-ollama` - Local LLM
- `stockinfo-dagster` - Pipeline orchestrator

## Troubleshooting

**WebSocket not updating**: Check Redis connection, verify Celery worker logs
**Celery tasks stuck**: Check `docker-compose logs celery-worker`
**Ollama errors**: Run `docker exec stockinfo-ollama ollama pull llama3.2`
**Database issues**: `make db-reset` to reset migrations
