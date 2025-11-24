-- Migration: Add Growth Analysis Fields to stock_analyses table
-- Created: 2025-11-24
-- Description: Adds comprehensive growth stock analysis fields including
--              scoring breakdown, price targets, insights, and data quality metrics

-- Add Growth Analysis fields
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS portfolio_allocation NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS price_target_base NUMERIC(12, 4);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS price_target_optimistic NUMERIC(12, 4);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS price_target_pessimistic NUMERIC(12, 4);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS upside_potential NUMERIC(7, 2);

-- Add Scoring Breakdown fields
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS composite_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS fundamental_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS technical_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS competitive_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20);

-- Add Key Insights fields (JSON arrays)
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS key_strengths JSONB;
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS key_risks JSONB;
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS catalyst_points JSONB;
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS monitoring_points JSONB;

-- Add Data Quality fields
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS data_completeness_score NUMERIC(5, 2);
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS missing_data_categories JSONB;

-- Add AI Qualitative Analysis fields
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS ai_summary TEXT;
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS ai_reasoning TEXT;

-- Add comments for documentation
COMMENT ON COLUMN stock_analyses.portfolio_allocation IS 'Suggested portfolio allocation percentage (0-100)';
COMMENT ON COLUMN stock_analyses.price_target_base IS 'Base case price target';
COMMENT ON COLUMN stock_analyses.price_target_optimistic IS 'Optimistic scenario price target';
COMMENT ON COLUMN stock_analyses.price_target_pessimistic IS 'Pessimistic scenario price target';
COMMENT ON COLUMN stock_analyses.upside_potential IS 'Percentage upside to base target';
COMMENT ON COLUMN stock_analyses.composite_score IS 'Weighted composite score (0-10)';
COMMENT ON COLUMN stock_analyses.fundamental_score IS 'Fundamental analysis score (0-10)';
COMMENT ON COLUMN stock_analyses.sentiment_score IS 'Market sentiment score (0-10)';
COMMENT ON COLUMN stock_analyses.technical_score IS 'Technical analysis score (0-10)';
COMMENT ON COLUMN stock_analyses.competitive_score IS 'Competitive position score (0-10)';
COMMENT ON COLUMN stock_analyses.risk_score IS 'Risk assessment score (1-10, higher = riskier)';
COMMENT ON COLUMN stock_analyses.risk_level IS 'Risk level: low, moderate, high, very high';
COMMENT ON COLUMN stock_analyses.key_strengths IS 'Array of key investment strengths';
COMMENT ON COLUMN stock_analyses.key_risks IS 'Array of key investment risks';
COMMENT ON COLUMN stock_analyses.catalyst_points IS 'Array of potential catalysts';
COMMENT ON COLUMN stock_analyses.monitoring_points IS 'Array of points to monitor';
COMMENT ON COLUMN stock_analyses.data_completeness_score IS 'Data completeness percentage (0-100)';
COMMENT ON COLUMN stock_analyses.missing_data_categories IS 'Array of missing data categories';
COMMENT ON COLUMN stock_analyses.ai_summary IS 'AI-generated investment summary';
COMMENT ON COLUMN stock_analyses.ai_reasoning IS 'AI-generated detailed reasoning';

-- Create index for composite_score for ranking queries
CREATE INDEX IF NOT EXISTS idx_stock_analyses_composite_score ON stock_analyses(composite_score DESC);

-- Create index for risk_level filtering
CREATE INDEX IF NOT EXISTS idx_stock_analyses_risk_level ON stock_analyses(risk_level);
