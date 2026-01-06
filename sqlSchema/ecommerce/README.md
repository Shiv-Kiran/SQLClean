# E-commerce Database Schema

## Overview
This schema represents a complete e-commerce system with customer orders, products, payments, and shipping.

## Tables
- **customers**: Customer account information
- **products**: Product catalog with inventory
- **orders**: Order headers with customer and totals
- **order_items**: Individual items within orders (junction table)
- **payments**: Payment transactions
- **shipments**: Shipping and delivery tracking

## Best Practices
- Use transactions for order processing to ensure data consistency
- Index order_date, customer_id, and product_id for performance
- Use CHECK constraints for data validation (price > 0, quantity > 0)
- Consider partitioning orders by date for large datasets
- Use ENUM types for status fields to prevent invalid data
- Implement triggers for automatic inventory updates

## Common Queries
- Order totals: SUM(order_items.total_price) per order
- Customer lifetime value: SUM(orders.total_amount) per customer
- Product sales: COUNT(order_items) GROUP BY product
- Inventory alerts: WHERE stock_quantity < threshold