SELECT a.user_id, a.user_name, (SELECT count(*) FROM orders o WHERE o.user_id = a.user_id) as total_orders,
a.created_at FROM users a WHERE a.status = 'active' AND a.user_id IN (select user_id from logins where login_date > '2023-01-01')
ORDER BY a.created_at desc;