-- Payments table
CREATE TABLE payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100) UNIQUE,
    status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- Sample data
INSERT INTO payments (order_id, amount, payment_method, transaction_id, status) VALUES
(1, 279.98, 'credit_card', 'txn_123456', 'completed'),
(2, 79.99, 'paypal', 'txn_789012', 'completed'),
(3, 129.99, 'credit_card', 'txn_345678', 'completed');