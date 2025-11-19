# Claude Code Development Prompt: AI-Powered Stock Research Tool

## Project Objective
Create a comprehensive stock research tool that analyzes stocks based on investments by popular funds, performs detailed stock analysis, and provides actionable reports through a modern web interface.

## Core Technology Stack (Based on Research)

### Backend
- **Framework**: FastAPI (chosen for async support, automatic API documentation, WebSocket capabilities)
- **Database**: PostgreSQL 15+ (transactional data) with time-series partitioning
- **Cache**: Redis 7+ (caching only, never for transactional data)
- **Orchestration**: Dagster (asset-oriented, better than Airflow for financial data)
- **Task Queue**: Celery with Redis broker
- **AI/LLM**: Ollama (pre-installed) with Langchain/Langraph integration

### MCP Servers (Critical for Data Gathering)
- **Playwright MCP**: Web automation via accessibility trees (50-200ms response)
- **Chrome DevTools MCP**: Performance analysis and debugging
- **Context7 MCP**: Current documentation access
*YOUR_API_KEY should be saved in a config file*

Installation commands:
```bash
npx @playwright/mcp@latest
npx chrome-devtools-mcp@latest  
npx -y @upstash/context7-mcp
uvx av-mcp YOUR_API_KEY
```

### Frontend
- **Framework**: React with TypeScript
- **State Management**: Zustand Toolkit
- **Data Fetching**: TanStack Query
- **Charts**: Plotly.js (financial charts)
- **CSS**: Tailwind CSS or Material-UI
- **WebSocket**: Socket.io for real-time updates

### Data Sources (Prioritized)
1. **Alpha Vantage**: Primary ($29.99/month production tier)
2. **Financial Modeling Prep**: Fundamentals
3. **SEC EDGAR API**: Free regulatory filings
4. **Yahoo Finance (yfinance)**: via API


## Functional Requirements

### 1. Overall Market Sentiment (Daily once or on request by user but only current day sentiment)
- Track NASDAQ, S&P 500, Dow Jones (7-day history + current)
- Identify hot sectors and negative positions
- Aggregate market-affecting news
- Sentiment analysis using Ollama
- Top news

### 2. Stock Research Data Collection
- Implement progressive fallback pattern:
  - Tier 1: Direct API access (80% target)
  - Tier 2: MCP Playwright extraction (8% target)
  - Tier 3: Screenshot + AI vision analysis (2% target)
- Download and parse annual financial statements
- Track upcoming earnings dates
- Maintain decision transparency in UI

### 3. Stock Analysis Engine
- Calculate valuation metrics (P/E, PEG, P/B, debt-to-equity, forward P/E)
- Technical indicators (RSI, MACD, moving averages, Bollinger Bands)
- Industry comparison against peers
- 6-month price estimates
- Investment recommendations with reasoning

### 4. Investor Research (Top 20 Funds)
- Daily (once) monitoring of 13F filings via SEC EDGAR
- Track buy/sell changes in portfolios
- Show percentage allocation in funds
- Prioritize 10 tech-focused funds
- Allow user-configurable fund list

### 5. User Interface Requirements
- Configuration wizard for fund selection and parameters
- Real-time progress tracking via WebSocket
- Data source transparency badges:
  - Green: Direct API
  - Blue: AI Analysis  
  - Orange: Web Extract
- One-click research initiation
- Mobile-responsive design
- Dispaly meaningful error messages if tool runs into problems, a button should appear to give the user the ability to get a suggestion from the tools AI to solve the issue.

### 6. AI Agent Architecture (Langraph)
Create supervisor agent pattern with specialized sub-agents:
- **Supervisor Agent**: Coordinates workflow and routing
- **Market Sentiment Agent**: Daily market analysis
- **Stock Research Agent**: Data gathering via MCP
- **Investor Tracking Agent**: 13F monitoring
- **Analysis Engine Agent**: Calculations and recommendations

### 7. Reporting System
- HTML-to-PDF using WeasyPrint
- Include charts, analysis, recommendations
- Web-based preview and PDF download
- Executive summary format

## Implementation Phases

### Phase 1: Foundation Setup (Priority: HIGH)
```
1. Initialize project structure:
   - /backend (FastAPI)
   - /frontend (React)
   - /agents (Langchain/Langraph)
   - /pipelines (Dagster)
   - /config (YAML configurations)

2. Set up databases:
   - PostgreSQL with pgcrypto extension
   - Redis with LRU eviction
   - Alembic migrations

3. Install and verify MCP servers
4. Create base FastAPI application
```

### Phase 2: Data Pipeline (Priority: HIGH)
```
1. Implement API clients with rate limiting:
   - Alpha Vantage (30 req/min limit)
   - SEC EDGAR (fair use compliance)
   
2. Create Dagster assets:
   - market_sentiment (daily @ 16:00 EST)
   - fund_holdings (sensor-triggered)
   - stock_prices (partitioned by date/ticker)
   
3. Set up MCP integration via Langchain:
   - MultiServerMCPClient configuration
   - Progressive fallback implementation
```

### Phase 3: Agent Development (Priority: HIGH)
```
1. Implement Langraph supervisor pattern
2. Create specialized agents with error handling
3. Add retry logic with exponential backoff
4. Implement caching strategies
```

### Phase 4: UI Development (Priority: MEDIUM)
```
1. React setup with TypeScript
2. Configuration interface with validation
3. Dashboard with real-time updates
4. Progress tracking via WebSocket
```

### Phase 5: Testing & Security (Priority: HIGH)
```
1. Pytest with 85%+ coverage target
2. Financial accuracy validation
3. Security scanning (Bandit, Safety CLI)
4. Input validation and SQL injection prevention
```

## Critical Configuration Management

### Configuration Structure (config.yaml)
```yaml
data_sources:
  alpha_vantage:
    api_key: ${ALPHA_VANTAGE_API_KEY}  # Environment variable
    rate_limit: 30
    timeout: 10
  
  sec_edgar:
    user_agent: "CompanyName/1.0"
    rate_limit: 10
    
funds:
  tech_focused:
    - "ARK Innovation ETF"
    - "Technology Select Sector SPDR"
    - "Vanguard Information Technology ETF (VGT)"
    - "iShares Global Tech ETF (IXN)"
    - "Global X Robotics & Artificial Intelligence ETF (BOTZ)"
    - "BGF Next Generation Technology Fund (BlackRock)"
    - "Janus Henderson Global Technology Leaders Fund"
    - "Polar Capital Global Technology Fund"
    - "iShares U.S. Technology ETF (IYW)"
    - "Global X Artificial Intelligence & Technology ETF (AIQ)"
  general:
    - "Berkshire Hathaway"
    - "Bridgewater Associates"
    - "Health Care Select Sector SPDR Fund (XLV)"
    - "Energy Select Sector SPDR Fund (XLE)"
    - "Financial Select Sector SPDR Fund (XLF)"
    - "Industrial Select Sector SPDR Fund (XLI)"
    - "Consumer Discretionary Select Sector SPDR Fund (XLY)"
    - "Consumer Staples Select Sector SPDR Fund (XLP)"
    - "Utilities Select Sector SPDR Fund (XLU)"
    - "Materials Select Sector SPDR Fund (XLB)"
    
analysis:
  confidence_thresholds:
    high: 0.8
    medium: 0.6
    low: 0.4
```

### Environment Variables (.env)
```
ALPHA_VANTAGE_API_KEY=xxx
SEC_API_KEY=xxx
POSTGRES_URL=postgresql://user:pass@localhost/stockdb
REDIS_URL=redis://localhost:6379
OLLAMA_BASE_URL=http://localhost:11434
```

## Database Schema Design

```sql
-- Time-series optimized schema
CREATE TABLE stock_prices (
    ticker VARCHAR(10),
    date DATE,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    PRIMARY KEY (ticker, date)
) PARTITION BY RANGE (date);

CREATE TABLE fund_holdings (
    fund_id INTEGER,
    ticker VARCHAR(10),
    filing_date DATE,
    shares BIGINT,
    value DECIMAL(15,2),
    percentage DECIMAL(5,2)
);

CREATE INDEX idx_holdings_fund_date ON fund_holdings(fund_id, filing_date);
```

## Performance Requirements
- Initial load time: <3 seconds
- Data accuracy: 99.9% validated
- API vs Vision ratio: 90/8/2 target
- Research completion: <5 minutes per stock
- Memory usage: <2GB for 10,000 stocks
- Cache hit rate: >60%

## Security Requirements
- API keys in environment variables only
- Rate limiting: 100 req/hour/user
- Input validation on all endpoints

## Error Handling Strategy
```python
# Implement retry with exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def fetch_stock_data(ticker: str):
    # Implementation with fallback pattern
    pass
```

## Monitoring Requirements
- Structured JSON logging
- Prometheus metrics (latency, throughput, errors)
- Sentry error tracking
- Health check endpoints
- Critical alerts for:
  - API failures >10%
  - Memory usage >80%
  - Database connection exhaustion

## Development Best Practices

1. **Start with market sentiment module** as proof-of-concept
2. **Use Decimal type** for financial calculations
3. **Implement caching aggressively** (60-80% API cost reduction)
4. **Track data provenance** for every piece of information
5. **Version control configurations** with schema migrations
6. **Document all financial formulas** and calculations
7. **Use pytest.approx** for floating-point test comparisons
8. **Profile before optimizing** with cProfile
9. **Batch API requests** when possible
10. **Monitor rate limits** proactively

## Known Pitfalls to Avoid
- Storing secrets in code
- Ignoring rate limits
- Not handling market holidays
- Assuming API availability
- Skipping data validation
- Hardcoding configurations

## Success Metrics
- [ ] Market sentiment updates daily at 4 PM EST
- [ ] 20 funds tracked with portfolio changes
- [ ] Sub-5 minute comprehensive stock analysis
- [ ] 90% data from direct APIs
- [ ] Real-time progress tracking functional
- [ ] PDF reports generating correctly
- [ ] All tests passing with >85% coverage

## Next Steps for Development
1. Create project directory structure
2. Initialize Git repository
3. Set up Python virtual environment (3.11+)
4. Install core dependencies
5. Configure PostgreSQL and Redis
6. Implement basic FastAPI skeleton
7. Add first MCP server integration
8. Create market sentiment agent as MVP
9. Build minimal React dashboard
10. Deploy locally for testing

## Questions to Clarify Before Starting
1. Confirm Ollama model selection (Mistral 7B recommended)
2. Verify fund list priorities (top 20 selections)

---

**Note**: This tool architecture is based on extensive research into best practices for financial data processing, MCP server capabilities, and production-grade Python applications. The progressive fallback pattern and multi-agent orchestration via Langraph represent cutting-edge approaches to reliable data aggregation.

Start development with the market sentiment module to validate the core architecture before expanding to full functionality. The modular design allows incremental feature addition while maintaining system stability.