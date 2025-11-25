-- Migration: Add Index on Sector Field
-- Created: 2025-11-25
-- Description: Adds index on sector field in stock_analyses table to improve
--              performance of sector-based queries for sector comparison feature

-- Create index for sector-based filtering and aggregation
CREATE INDEX IF NOT EXISTS idx_stock_analyses_sector ON stock_analyses(sector);

-- Create composite index for sector and date for optimized sector statistics queries
CREATE INDEX IF NOT EXISTS idx_stock_analyses_sector_date ON stock_analyses(sector, analysis_date DESC);

-- Add comment for documentation
COMMENT ON INDEX idx_stock_analyses_sector IS 'Index for sector-based filtering and aggregation queries';
COMMENT ON INDEX idx_stock_analyses_sector_date IS 'Composite index for sector statistics queries with date ordering';
