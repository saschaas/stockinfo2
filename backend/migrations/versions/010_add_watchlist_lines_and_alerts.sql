-- Migration: Add watchlist lines and alerts for stock monitoring
-- Created: 2026-01-07

-- Add momentum indicator fields to watchlist_items
ALTER TABLE watchlist_items
    ADD COLUMN IF NOT EXISTS has_golden_cross BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_bullish_trend BOOLEAN,
    ADD COLUMN IF NOT EXISTS sma_20 NUMERIC(12, 4),
    ADD COLUMN IF NOT EXISTS sma_50 NUMERIC(12, 4),
    ADD COLUMN IF NOT EXISTS sma_200 NUMERIC(12, 4),
    ADD COLUMN IF NOT EXISTS last_momentum_update TIMESTAMP WITH TIME ZONE;

-- Create watchlist_lines table for custom trend lines and alerts
CREATE TABLE IF NOT EXISTS watchlist_lines (
    id SERIAL PRIMARY KEY,
    watchlist_item_id INTEGER NOT NULL REFERENCES watchlist_items(id) ON DELETE CASCADE,
    line_type VARCHAR(20) NOT NULL,  -- "trend" or "alert"
    name VARCHAR(100) NOT NULL,
    price_level NUMERIC(12, 4) NOT NULL,
    color VARCHAR(20) DEFAULT '#8b5cf6',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on watchlist_item_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_watchlist_line_item ON watchlist_lines(watchlist_item_id);

-- Create triggered_alerts table for alert history
CREATE TABLE IF NOT EXISTS triggered_alerts (
    id SERIAL PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES watchlist_lines(id) ON DELETE CASCADE,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    triggered_price NUMERIC(12, 4) NOT NULL,
    direction VARCHAR(20) NOT NULL,  -- "crossed_up" or "crossed_down"
    notified BOOLEAN DEFAULT FALSE,
    dismissed BOOLEAN DEFAULT FALSE
);

-- Create composite index for efficient alert queries
CREATE INDEX IF NOT EXISTS idx_triggered_alert_line_date ON triggered_alerts(line_id, triggered_at);
