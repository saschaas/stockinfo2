-- Migration: Add Web-Scraped Market Data Table
-- Created: 2025-12-11
-- Description: Adds web_scraped_market_data table for storing market data extracted
--              from web scraping with AI analysis

-- Create web_scraped_market_data table
CREATE TABLE web_scraped_market_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    source_url VARCHAR(500) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL DEFAULT 'market_overview',
    raw_scraped_data JSONB,
    scraping_model VARCHAR(50),
    market_summary TEXT,
    overall_sentiment NUMERIC(5,4),
    bullish_score NUMERIC(5,4),
    bearish_score NUMERIC(5,4),
    trending_sectors JSONB,
    declining_sectors JSONB,
    market_themes JSONB,
    key_events JSONB,
    analysis_model VARCHAR(50),
    analysis_timestamp TIMESTAMPTZ,
    confidence_score NUMERIC(5,4),
    data_completeness NUMERIC(5,2),
    extraction_method VARCHAR(50) NOT NULL DEFAULT 'mcp_playwright',
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on date for fast queries
CREATE INDEX ix_web_scraped_market_data_date ON web_scraped_market_data(date);

-- Add helpful comments
COMMENT ON TABLE web_scraped_market_data IS 'Market data extracted from web scraping with AI analysis';
COMMENT ON COLUMN web_scraped_market_data.source_name IS 'Configuration key (e.g., market_overview_perplexity)';
COMMENT ON COLUMN web_scraped_market_data.raw_scraped_data IS 'Raw data extracted by WebScrapingAgent';
COMMENT ON COLUMN web_scraped_market_data.scraping_model IS 'LLM model used for data extraction';
COMMENT ON COLUMN web_scraped_market_data.analysis_model IS 'LLM model used for market analysis';
COMMENT ON COLUMN web_scraped_market_data.confidence_score IS 'AI confidence in analysis (0-1)';
COMMENT ON COLUMN web_scraped_market_data.data_completeness IS 'Percentage of expected data fields found (0-100)';
