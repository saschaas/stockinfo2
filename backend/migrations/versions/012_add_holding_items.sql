-- Migration: Add holding_items, holding_lines, and holding_triggered_alerts tables
-- Created: 2026-01-08

-- Create holding_items table
CREATE TABLE IF NOT EXISTS holding_items (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(200),
    quantity NUMERIC(18, 6) NOT NULL,
    cost_basis NUMERIC(12, 4),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    has_golden_cross BOOLEAN,
    is_bullish_trend BOOLEAN,
    sma_20 NUMERIC(12, 4),
    sma_50 NUMERIC(12, 4),
    sma_200 NUMERIC(12, 4),
    last_momentum_update TIMESTAMP WITH TIME ZONE
);

-- Create indexes on holding_items
CREATE INDEX IF NOT EXISTS idx_holding_items_ticker ON holding_items(ticker);
CREATE INDEX IF NOT EXISTS idx_holding_items_sort_order ON holding_items(sort_order);

-- Create holding_lines table
CREATE TABLE IF NOT EXISTS holding_lines (
    id SERIAL PRIMARY KEY,
    holding_item_id INTEGER NOT NULL REFERENCES holding_items(id) ON DELETE CASCADE,
    line_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    price_level NUMERIC(12, 4) NOT NULL,
    color VARCHAR(20) DEFAULT '#8b5cf6',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes on holding_lines
CREATE INDEX IF NOT EXISTS idx_holding_line_item ON holding_lines(holding_item_id);

-- Create holding_triggered_alerts table
CREATE TABLE IF NOT EXISTS holding_triggered_alerts (
    id SERIAL PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES holding_lines(id) ON DELETE CASCADE,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    triggered_price NUMERIC(12, 4) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    notified BOOLEAN DEFAULT FALSE,
    dismissed BOOLEAN DEFAULT FALSE
);

-- Create indexes on holding_triggered_alerts
CREATE INDEX IF NOT EXISTS idx_holding_triggered_alert_line_date ON holding_triggered_alerts(line_id, triggered_at);
