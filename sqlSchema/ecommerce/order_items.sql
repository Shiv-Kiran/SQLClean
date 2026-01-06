-- Order Items table (many-to-many between orders and products)
CREATE TABLE order_items (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Sample data
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 199.99),
(1, 2, 1, 79.99),
(2, 2, 1, 79.99),
(3, 3, 1, 129.99);