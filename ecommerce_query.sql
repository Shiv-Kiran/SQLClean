SELECT c.first_name, c.last_name, o.order_id, o.order_date, p.product_name, oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) as line_total
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'shipped' AND o.order_date >= '2024-01-01'
ORDER BY o.order_date DESC, c.last_name;