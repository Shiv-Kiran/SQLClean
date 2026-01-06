-- Shipments table
CREATE TABLE shipments (
    shipment_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    shipment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    carrier VARCHAR(100),
    tracking_number VARCHAR(100) UNIQUE,
    status ENUM('preparing', 'shipped', 'in_transit', 'delivered', 'returned') DEFAULT 'preparing',
    estimated_delivery DATE,
    actual_delivery DATE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- Sample data
INSERT INTO shipments (order_id, carrier, tracking_number, status, estimated_delivery) VALUES
(1, 'FedEx', 'TRK123456789', 'shipped', '2024-01-10'),
(2, 'UPS', 'TRK987654321', 'delivered', '2024-01-08'),
(3, 'USPS', 'TRK456789123', 'in_transit', '2024-01-12');