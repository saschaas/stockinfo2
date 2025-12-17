-- Migration: Add Scraped Category Data Table
-- Created: 2025-12-17
-- Description: Adds scraped_category_data table for storing category-specific
--              scraped data (top_gainers, top_losers, hot_stocks, etc.)
--              allowing multiple sources per category with data combination.

-- Create scraped_category_data table
CREATE TABLE IF NOT EXISTS scraped_category_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    category VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    scraping_model VARCHAR(50),
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on date for filtering by date
CREATE INDEX IF NOT EXISTS ix_scraped_category_data_date ON scraped_category_data(date);

-- Create index on source_key for filtering by source
CREATE INDEX IF NOT EXISTS ix_scraped_category_data_source_key ON scraped_category_data(source_key);

-- Create index on category for filtering by data type
CREATE INDEX IF NOT EXISTS ix_scraped_category_data_category ON scraped_category_data(category);

-- Create composite index for efficient queries by date and category
CREATE INDEX IF NOT EXISTS ix_scraped_category_data_date_category ON scraped_category_data(date, category);

-- Create unique constraint to prevent duplicate entries for same date/source/category
CREATE UNIQUE INDEX IF NOT EXISTS ix_scraped_category_data_unique
    ON scraped_category_data(date, source_key, category);

-- Add helpful comments
COMMENT ON TABLE scraped_category_data IS 'Category-specific data extracted from web scraping';
COMMENT ON COLUMN scraped_category_data.date IS 'Date when the data was scraped';
COMMENT ON COLUMN scraped_category_data.source_key IS 'Key identifying the website source';
COMMENT ON COLUMN scraped_category_data.source_url IS 'URL that was scraped';
COMMENT ON COLUMN scraped_category_data.category IS 'Data category: top_gainers, top_losers, hot_stocks, hot_sectors, bad_sectors, analyst_ratings, news, etc.';
COMMENT ON COLUMN scraped_category_data.data IS 'JSON data extracted for this category (stocks list, sectors list, etc.)';
COMMENT ON COLUMN scraped_category_data.scraping_model IS 'LLM model used for data extraction';
COMMENT ON COLUMN scraped_category_data.response_time_ms IS 'Time taken to scrape in milliseconds';
