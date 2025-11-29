# Stock Research Tool

AI-Powered Stock Research Tool with fund tracking and comprehensive analysis.

## Features

- **Market Sentiment Analysis**: Daily analysis of NASDAQ, S&P 500, Dow Jones with AI-powered sentiment scoring
- **Stock Research**: Comprehensive stock analysis with valuation metrics, technical indicators, and AI recommendations
- **Fund Tracking**: Monitor 20 top funds (10 tech-focused, 10 general) for portfolio changes via SEC 13F filings
- **Real-time Updates**: WebSocket-based progress tracking for research jobs
- **PDF Reports**: Generate comprehensive analysis reports

## Tech Stack

### Backend
- FastAPI (async Python web framework)
- PostgreSQL 15+ (with time-series partitioning)
- Redis 7+ (caching)
- Celery (task queue)
- Dagster (data pipelines)

### AI/LLM
- Ollama with Mistral 7B
- Langchain/Langgraph for agent orchestration

### Frontend
- React with TypeScript
- Zustand (state management)
- TanStack Query (data fetching)
- Plotly.js (financial charts)
- Tailwind CSS

### Data Sources
- Alpha Vantage (primary)
- SEC EDGAR (13F filings)
- Yahoo Finance
- Financial Modeling Prep

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Ollama (with Mistral 7B model)

### Quick Start with Docker

1. **Clone and configure**
   ```bash
   cd StockInfo
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**
   ```bash
   docker-compose --profile init up db-init
   ```

4. **Pull Ollama model**
   ```bash
   docker exec stockinfo-ollama ollama pull llama3.2
   docker exec stockinfo-ollama ollama pull deepseek-ocr
   docker exec stockinfo-ollama ollama pull mistral
   docker exec stockinfo-ollama ollama pull gpt-oss
   docker exec stockinfo-ollama ollama pull phi4-reasoning
   docker exec stockinfo-ollama ollama pull qwen3
   ```

5. **Access the application**
   - Frontend: http://localhost
   - API Docs: http://localhost:8000/docs
   - Dagster UI: http://localhost:3001

### Manual Installation

1. **Set up Python environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Unix/macOS
   source venv/bin/activate

   pip install -e ".[dev,dagster]"
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

3. **Set up database**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis

   # Initialize database
   python backend/scripts/init_db.py
   ```

4. **Install Ollama model**
   ```bash
   ollama pull llama3.2
   ```

5. **Set up frontend**
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

**Development mode:**

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm start

# Terminal 3: Celery worker
celery -A backend.app.celery_app worker --loglevel=info
```

**Using Docker Compose:**

```bash
docker-compose up -d
```

Access the application:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Dagster UI: http://localhost:3001

## API Endpoints

### Market
- `GET /api/v1/market/sentiment` - Get current market sentiment
- `GET /api/v1/market/sentiment/history` - Get sentiment history
- `POST /api/v1/market/sentiment/refresh` - Trigger sentiment refresh

### Stocks
- `GET /api/v1/stocks/{ticker}` - Get stock analysis
- `GET /api/v1/stocks/{ticker}/prices` - Get price history
- `POST /api/v1/stocks/research` - Start research job
- `GET /api/v1/stocks/{ticker}/peers` - Get peer comparison
- `GET /api/v1/stocks/{ticker}/fund-ownership` - Get fund ownership

### Funds
- `GET /api/v1/funds` - List tracked funds
- `GET /api/v1/funds/{fund_id}/holdings` - Get fund holdings
- `GET /api/v1/funds/{fund_id}/changes` - Get holdings changes
- `POST /api/v1/funds/refresh` - Refresh fund data

### Reports
- `GET /api/v1/reports/stock/{ticker}` - Generate stock report
- `GET /api/v1/reports/market` - Generate market report

### WebSocket
- `WS /api/v1/ws/progress/{job_id}` - Job progress updates
- `WS /api/v1/ws/market` - Market updates
- `WS /api/v1/ws/notifications` - System notifications

## Configuration

### config/config.yaml

Main configuration file with:
- Data source settings
- Fund list (20 funds)
- Analysis parameters
- Scheduling

### .env

Environment variables for:
- API keys
- Database credentials
- Redis connection
- Ollama settings

## Project Structure

```
StockInfo/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── core/        # Core utilities
│   │   ├── db/          # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # External services
│   ├── migrations/      # Alembic migrations
│   └── tests/
├── agents/               # AI agents (Langgraph)
├── pipelines/            # Dagster pipelines
├── frontend/             # React application
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── stores/
│       └── services/
└── config/               # Configuration files
```

## Data Source Transparency

Each piece of data includes source tracking:
- 🟢 **Green**: Direct API
- 🔵 **Blue**: AI Analysis
- 🟠 **Orange**: Web Extraction

## Performance Targets

- Initial load: <3 seconds
- Research completion: <5 minutes per stock
- Cache hit rate: >60%
- Data accuracy: 99.9%

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License
