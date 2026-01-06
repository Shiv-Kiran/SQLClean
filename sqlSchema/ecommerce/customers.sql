-- Customers table for e-commerce system
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO customers (first_name, last_name, email, phone, city, state) VALUES
('Alice', 'Brown', 'alice.brown@email.com', '555-0101', 'New York', 'NY'),
('Charlie', 'Wilson', 'charlie.wilson@email.com', '555-0102', 'Los Angeles', 'CA'),
('Diana', 'Davis', 'diana.davis@email.com', '555-0103', 'Chicago', 'IL');