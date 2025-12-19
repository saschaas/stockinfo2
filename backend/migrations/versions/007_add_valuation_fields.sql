-- Migration: Add Valuation Engine Fields
-- Created: 2025-12-19
-- Description: Adds comprehensive valuation fields to stock_analyses table
--              for DCF, DDM, relative valuation, and asset-based valuation methods.
--              Supports company classification, multiple valuation methods, and
--              fair value calculation with confidence ranges.

-- === COMPANY CLASSIFICATION FIELDS ===
-- Company type classification (dividend_payer, high_growth, reit, bank, etc.)
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_company_type VARCHAR(30);

-- Confidence in company classification (0.0 to 1.0)
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_classification_confidence NUMERIC(5,4);

-- Reasons for company classification as JSON array
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_classification_reasons JSONB;

-- === INTRINSIC VALUE RESULTS ===
-- Composite fair value per share (weighted average of methods)
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS intrinsic_value NUMERIC(12,4);

-- Fair value range - low estimate
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS intrinsic_value_low NUMERIC(12,4);

-- Fair value range - high estimate
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS intrinsic_value_high NUMERIC(12,4);

-- Margin of safety: (fair_value - current_price) / fair_value
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS margin_of_safety NUMERIC(7,4);

-- Valuation status: undervalued, fairly_valued, overvalued
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_status VARCHAR(30);

-- === DISCOUNT RATE FIELDS ===
-- Weighted Average Cost of Capital
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_wacc NUMERIC(7,5);

-- Cost of equity from CAPM
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_cost_of_equity NUMERIC(7,5);

-- Risk-free rate used in calculations
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_risk_free_rate NUMERIC(7,5);

-- === METHOD BREAKDOWN FIELDS ===
-- List of valuation methods used with their weights
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_methods_used JSONB;

-- Primary valuation method used
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_primary_method VARCHAR(30);

-- Detailed results from each valuation method
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_method_results JSONB;

-- === CONFIDENCE AND QUALITY FIELDS ===
-- Overall confidence in valuation (0 to 100)
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_confidence NUMERIC(5,2);

-- Data quality assessment: high, medium, low
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS valuation_data_quality VARCHAR(20);

-- === INDEXES ===
-- Index on valuation status for filtering undervalued stocks
CREATE INDEX IF NOT EXISTS ix_stock_analyses_valuation_status ON stock_analyses(valuation_status);

-- Index on company type for filtering by company classification
CREATE INDEX IF NOT EXISTS ix_stock_analyses_valuation_company_type ON stock_analyses(valuation_company_type);

-- === COMMENTS ===
COMMENT ON COLUMN stock_analyses.valuation_company_type IS 'Company classification: dividend_payer, high_growth, mature_growth, value, reit, bank, insurance, utility, distressed, cyclical, commodity';
COMMENT ON COLUMN stock_analyses.valuation_classification_confidence IS 'Confidence in company classification (0.0 to 1.0)';
COMMENT ON COLUMN stock_analyses.valuation_classification_reasons IS 'JSON array of reasons for company classification';
COMMENT ON COLUMN stock_analyses.intrinsic_value IS 'Composite fair value per share from weighted valuation methods';
COMMENT ON COLUMN stock_analyses.intrinsic_value_low IS 'Lower bound of fair value range (conservative estimate)';
COMMENT ON COLUMN stock_analyses.intrinsic_value_high IS 'Upper bound of fair value range (optimistic estimate)';
COMMENT ON COLUMN stock_analyses.margin_of_safety IS 'Percentage below fair value: (fair_value - price) / fair_value';
COMMENT ON COLUMN stock_analyses.valuation_status IS 'Valuation conclusion: undervalued, fairly_valued, overvalued';
COMMENT ON COLUMN stock_analyses.valuation_wacc IS 'Weighted Average Cost of Capital used in DCF';
COMMENT ON COLUMN stock_analyses.valuation_cost_of_equity IS 'Cost of equity from CAPM calculation';
COMMENT ON COLUMN stock_analyses.valuation_risk_free_rate IS 'Risk-free rate (10Y Treasury) used in calculations';
COMMENT ON COLUMN stock_analyses.valuation_methods_used IS 'JSON array of {method, weight, can_execute} for each method';
COMMENT ON COLUMN stock_analyses.valuation_primary_method IS 'Primary valuation method with highest weight';
COMMENT ON COLUMN stock_analyses.valuation_method_results IS 'JSON object with detailed results per valuation method';
COMMENT ON COLUMN stock_analyses.valuation_confidence IS 'Overall confidence score (0-100) based on data quality and method agreement';
COMMENT ON COLUMN stock_analyses.valuation_data_quality IS 'Data quality assessment: high, medium, low';
