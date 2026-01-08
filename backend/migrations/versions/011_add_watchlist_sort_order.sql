-- Migration: Add sort_order column to watchlist_items for custom ordering
-- Created: 2026-01-08

-- Add sort_order column to watchlist_items table
ALTER TABLE watchlist_items ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;

-- Create index on sort_order for fast sorting
CREATE INDEX IF NOT EXISTS idx_watchlist_items_sort_order ON watchlist_items(sort_order);

-- Initialize sort_order based on existing added_at order (oldest gets lowest number)
WITH ordered_items AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY added_at ASC) - 1 AS new_order
    FROM watchlist_items
)
UPDATE watchlist_items SET sort_order = ordered_items.new_order
FROM ordered_items
WHERE watchlist_items.id = ordered_items.id;
