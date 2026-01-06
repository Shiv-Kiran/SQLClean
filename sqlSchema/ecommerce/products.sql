-- Products table
CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    category VARCHAR(100),
    stock_quantity INT DEFAULT 0 CHECK (stock_quantity >= 0),
    sku VARCHAR(50) UNIQUE,
    weight_kg DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO products (product_name, description, price, category, stock_quantity, sku) VALUES
('Wireless Headphones', 'High-quality wireless headphones with noise cancellation', 199.99, 'Electronics', 50, 'WH-001'),
('Coffee Maker', '12-cup programmable coffee maker', 79.99, 'Appliances', 30, 'CM-002'),
('Running Shoes', 'Comfortable running shoes for all terrains', 129.99, 'Sports', 75, 'RS-003');