-- Migration: Add ETF Tables
-- Created: 2025-12-22
-- Description: Adds etfs and etf_holdings tables for tracking ETF holdings
--              extracted from provider websites via web scraping

-- Create etfs table
CREATE TABLE IF NOT EXISTS etfs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    ticker VARCHAR(20) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL,
    agent_command TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    priority INTEGER NOT NULL DEFAULT 10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_scrape_at TIMESTAMPTZ,
    last_scrape_success BOOLEAN,
    last_scrape_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for etfs table
CREATE INDEX IF NOT EXISTS ix_etfs_ticker ON etfs(ticker);
CREATE INDEX IF NOT EXISTS ix_etfs_category ON etfs(category);
CREATE INDEX IF NOT EXISTS ix_etfs_active ON etfs(is_active);

-- Create etf_holdings table
CREATE TABLE IF NOT EXISTS etf_holdings (
    id SERIAL PRIMARY KEY,
    etf_id INTEGER NOT NULL REFERENCES etfs(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    company_name VARCHAR(200),
    cusip VARCHAR(20),
    holding_date DATE NOT NULL,
    shares BIGINT,
    market_value NUMERIC(18, 2),
    weight_pct NUMERIC(7, 4),
    shares_change BIGINT,
    weight_change NUMERIC(7, 4),
    change_type VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for etf_holdings table
CREATE INDEX IF NOT EXISTS ix_etf_holdings_etf_id ON etf_holdings(etf_id);
CREATE INDEX IF NOT EXISTS ix_etf_holdings_ticker ON etf_holdings(ticker);
CREATE INDEX IF NOT EXISTS ix_etf_holdings_holding_date ON etf_holdings(holding_date);
CREATE INDEX IF NOT EXISTS idx_etf_holding_etf_date ON etf_holdings(etf_id, holding_date);
CREATE INDEX IF NOT EXISTS idx_etf_holding_ticker_date ON etf_holdings(ticker, holding_date);

-- Add helpful comments
COMMENT ON TABLE etfs IS 'ETF configuration for tracking holdings from provider websites';
COMMENT ON COLUMN etfs.name IS 'Display name of the ETF';
COMMENT ON COLUMN etfs.ticker IS 'ETF ticker symbol (e.g., ARKK, SPY)';
COMMENT ON COLUMN etfs.url IS 'URL of the ETF holdings page to scrape';
COMMENT ON COLUMN etfs.agent_command IS 'LLM prompt/instructions for extracting holdings data';
COMMENT ON COLUMN etfs.description IS 'ETF description (can be auto-populated from scrape)';
COMMENT ON COLUMN etfs.category IS 'ETF category: innovation, sector, broad_market, etc.';
COMMENT ON COLUMN etfs.priority IS 'Display priority within category';
COMMENT ON COLUMN etfs.last_scrape_at IS 'Timestamp of last successful scrape';
COMMENT ON COLUMN etfs.last_scrape_success IS 'Whether the last scrape was successful';
COMMENT ON COLUMN etfs.last_scrape_error IS 'Error message from last failed scrape';

COMMENT ON TABLE etf_holdings IS 'ETF holdings extracted from provider websites';
COMMENT ON COLUMN etf_holdings.etf_id IS 'Reference to parent ETF';
COMMENT ON COLUMN etf_holdings.ticker IS 'Stock ticker symbol';
COMMENT ON COLUMN etf_holdings.company_name IS 'Company name';
COMMENT ON COLUMN etf_holdings.cusip IS 'CUSIP identifier if available';
COMMENT ON COLUMN etf_holdings.holding_date IS 'Date of the holdings data';
COMMENT ON COLUMN etf_holdings.shares IS 'Number of shares held';
COMMENT ON COLUMN etf_holdings.market_value IS 'Market value in USD';
COMMENT ON COLUMN etf_holdings.weight_pct IS 'Weight percentage in portfolio';
COMMENT ON COLUMN etf_holdings.shares_change IS 'Change in shares from previous date';
COMMENT ON COLUMN etf_holdings.weight_change IS 'Change in weight from previous date';
COMMENT ON COLUMN etf_holdings.change_type IS 'Type of change: new, increased, decreased, sold';

-- Insert ARKK as the first example ETF
INSERT INTO etfs (name, ticker, url, agent_command, description, category, priority)
VALUES (
    'ARK Innovation ETF',
    'ARKK',
    'https://www.ark-funds.com/funds/arkk',
    'Download holdings via the link on the provided URL. Available as CSV and PDF. Download the CSV version titled "Full Holdings CSV". Look for a download link or button that downloads the complete holdings list in CSV format. Expected CSV columns: date, fund, company, ticker, cusip, shares, market value ($), weight (%). If a description of the ETF can be found on the website, extract it as well.',
    'ARK Innovation ETF is an actively managed ETF that seeks long-term growth of capital by investing under normal circumstances primarily in domestic and foreign equity securities of companies that are relevant to the fund''s investment theme of disruptive innovation.',
    'innovation',
    1
) ON CONFLICT (ticker) DO NOTHING;
