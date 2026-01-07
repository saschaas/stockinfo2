-- Migration: Add watchlist_items table for user stock monitoring
-- Created: 2026-01-07

-- Create watchlist_items table
CREATE TABLE IF NOT EXISTS watchlist_items (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(200),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create index on ticker for fast lookups
CREATE INDEX IF NOT EXISTS idx_watchlist_items_ticker ON watchlist_items(ticker);

-- Create index on added_at for sorting
CREATE INDEX IF NOT EXISTS idx_watchlist_items_added_at ON watchlist_items(added_at);
