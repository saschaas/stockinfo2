-- Migration: Add Company Description Field
-- Created: 2025-12-11
-- Description: Adds company business description field to stock_analyses table
--              for storing what the company does and how they make money

-- Add company description field
ALTER TABLE stock_analyses ADD COLUMN IF NOT EXISTS description TEXT;

-- Add comment for documentation
COMMENT ON COLUMN stock_analyses.description IS 'Company business description explaining what they do and how they make money';
