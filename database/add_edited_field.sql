-- Add 'edited' field to expenses table for tracking expense modifications
-- Run this in Supabase SQL Editor

ALTER TABLE expenses 
ADD COLUMN IF NOT EXISTS edited BOOLEAN DEFAULT FALSE;

-- Update existing records to set edited as false
UPDATE expenses SET edited = FALSE WHERE edited IS NULL;

