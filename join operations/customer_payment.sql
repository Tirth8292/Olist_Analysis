DROP TABLE IF EXISTS customer_payment;
CREATE TABLE customer_payment AS
SELECT c.customer_unique_id,
       SUM(p.payment_installments) AS payment_installments,
       SUM(p.payment_value) AS payment_value
FROM customers AS c
JOIN orders AS o ON c.customer_id = o.customer_id
LEFT JOIN order_payments AS p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id;
