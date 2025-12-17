-- Migration: Add Scraped Websites Table
-- Created: 2025-12-17
-- Description: Adds scraped_websites table for storing user-configured websites
--              for data scraping with support for multiple data use categories

-- Create scraped_websites table
CREATE TABLE IF NOT EXISTS scraped_websites (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description TEXT,
    data_use VARCHAR(50) NOT NULL,
    extraction_template JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_test_at TIMESTAMPTZ,
    last_test_result JSONB,
    last_test_success BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on key for fast lookups
CREATE INDEX IF NOT EXISTS ix_scraped_websites_key ON scraped_websites(key);

-- Create index on data_use for filtering by category
CREATE INDEX IF NOT EXISTS ix_scraped_websites_data_use ON scraped_websites(data_use);

-- Create index on is_active for filtering active websites
CREATE INDEX IF NOT EXISTS ix_scraped_websites_active ON scraped_websites(is_active);

-- Add helpful comments
COMMENT ON TABLE scraped_websites IS 'User-configured websites for scraping data';
COMMENT ON COLUMN scraped_websites.key IS 'Unique identifier key for the website';
COMMENT ON COLUMN scraped_websites.name IS 'Display name for the data source';
COMMENT ON COLUMN scraped_websites.url IS 'URL pattern to scrape (may contain placeholders like {TICKER})';
COMMENT ON COLUMN scraped_websites.description IS 'User description of what data should be scraped';
COMMENT ON COLUMN scraped_websites.data_use IS 'Category of data: dashboard_sentiment, hot_stocks, hot_sectors, bad_sectors, analyst_ratings, news, etf_holdings, etf_holding_changes, fund_holdings, fund_holding_changes';
COMMENT ON COLUMN scraped_websites.extraction_template IS 'JSON template defining expected data format for the category';
COMMENT ON COLUMN scraped_websites.last_test_at IS 'Timestamp of last test scrape';
COMMENT ON COLUMN scraped_websites.last_test_result IS 'Result data from last test scrape';
COMMENT ON COLUMN scraped_websites.last_test_success IS 'Whether the last test was successful';
