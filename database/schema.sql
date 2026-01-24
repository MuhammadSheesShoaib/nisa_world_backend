-- Users table (already exists)
-- Ensure users table exists with correct structure
CREATE TABLE IF NOT EXISTS users (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role_id SMALLINT NOT NULL CHECK (role_id IN (1,2)), -- 1=Admin, 2=Staff
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory (Products) Table
CREATE TABLE IF NOT EXISTS inventory (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    cost_price DECIMAL(10,2) NOT NULL,
    sale_price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    added_by INT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw Materials Table
CREATE TABLE IF NOT EXISTS raw_materials (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_name VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method SMALLINT NOT NULL CHECK (payment_method IN (1,2)), -- 1=Full, 2=Advance
    advance_paid DECIMAL(10,2) DEFAULT 0,
    used BOOLEAN NOT NULL DEFAULT false,
    added_by INT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sales Table
CREATE TABLE IF NOT EXISTS sales (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_address TEXT,
    customer_phone VARCHAR(50),
    product_id INT,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    cost_price DECIMAL(10,2) NOT NULL,
    sale_price DECIMAL(10,2) NOT NULL,
    payment_type SMALLINT NOT NULL CHECK (payment_type IN (1,2)), -- 1=Full, 2=Advance
    advance_amount DECIMAL(10,2) DEFAULT 0,
    sold_by INT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Expenses Table
CREATE TABLE IF NOT EXISTS expenses (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_name VARCHAR(255) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method SMALLINT NOT NULL CHECK (payment_method IN (1,2)), -- 1=Full, 2=Advance
    added_by INT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_inventory_added_by ON inventory(added_by);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category);
CREATE INDEX IF NOT EXISTS idx_raw_materials_added_by ON raw_materials(added_by);
CREATE INDEX IF NOT EXISTS idx_sales_sold_by ON sales(sold_by);
CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_expenses_added_by ON expenses(added_by);
CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at);
