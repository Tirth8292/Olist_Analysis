DROP TABLE IF EXISTS transaction_data;
CREATE TABLE transaction_data AS
SELECT c.customer_unique_id, o.order_id, o.order_purchase_timestamp,
       i.order_item_id, i.product_id, i.seller_id, i.price, i.freight_value,
       t.product_category_name_english, p.payment_installments, p.payment_value
FROM customers AS c
JOIN orders AS o ON c.customer_id = o.customer_id
JOIN order_items AS i ON o.order_id = i.order_id
LEFT JOIN products AS pr ON i.product_id = pr.product_id
LEFT JOIN category_translation AS t ON pr.product_category_name = t.product_category_name
LEFT JOIN order_payments AS p ON o.order_id = p.order_id;
