-- Categories table for managing product/inventory categories
-- This table already exists with the schema below
-- Just run the INSERT statements to add default categories

-- CREATE TABLE IF NOT EXISTS categories (
--   category_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--   category_name VARCHAR(100) NOT NULL UNIQUE,
--   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Insert some default categories
INSERT INTO categories (category_name) VALUES 
  ('Electronics'),
  ('Furniture'),
  ('Clothing'),
  ('Food & Beverages'),
  ('Office Supplies')
ON CONFLICT (category_name) DO NOTHING;

