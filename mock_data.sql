-- ==========================================
-- Mock Database for Testing Telegram AI Agent
-- Run this in your Supabase SQL Editor
-- ==========================================

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'customer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Create Products Table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- 3. Create Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    total_amount DECIMAL(10, 2) NOT NULL,
    status TEXT DEFAULT 'pending',
    order_date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 4. Insert Mock Users
INSERT INTO users (name, email, role) VALUES
('Alice Smith', 'alice@example.com', 'admin'),
('Bob Jones', 'bob@example.com', 'customer'),
('Charlie Brown', 'charlie@example.com', 'customer'),
('Diana Prince', 'diana@example.com', 'customer'),
('Evan Wright', 'evan@example.com', 'manager'),
('Fiona Gallagher', 'fiona@example.com', 'customer'),
('George Martin', 'george@example.com', 'customer'),
('Hannah Abbott', 'hannah@example.com', 'customer'),
('Ian Malcolm', 'ian@example.com', 'admin'),
('Julia Child', 'julia@example.com', 'customer');

-- 5. Insert Mock Products
INSERT INTO products (name, category, price, stock_quantity) VALUES
('Wireless Mouse', 'Electronics', 25.99, 150),
('Mechanical Keyboard', 'Electronics', 89.50, 45),
('Coffee Mug', 'Home', 12.00, 300),
('Ergonomic Chair', 'Furniture', 249.99, 10),
('Notebook', 'Office', 4.50, 500),
('USB-C Hub', 'Electronics', 35.00, 120),
('Desk Lamp', 'Home', 45.00, 80),
('Noise Cancelling Headphones', 'Electronics', 199.99, 60),
('Water Bottle', 'Home', 15.00, 200),
('Standing Desk', 'Furniture', 499.00, 5);

-- 6. Insert Mock Orders
INSERT INTO orders (user_id, total_amount, status) VALUES
(2, 25.99, 'completed'),
(3, 101.50, 'pending'),
(2, 4.50, 'processing'),
(5, 249.99, 'completed'),
(4, 12.00, 'cancelled'),
(6, 35.00, 'completed'),
(7, 45.00, 'completed'),
(8, 199.99, 'pending'),
(9, 499.00, 'processing'),
(10, 15.00, 'completed');

-- Verify inserted data
-- SELECT * FROM users;
-- SELECT * FROM products;
-- SELECT * FROM orders;
