DROP TABLE IF EXISTS customer_order;
CREATE TABLE customer_order AS
SELECT o.order_id, o.order_purchase_timestamp, i.order_item_id,
       i.product_id, i.price, i.freight_value,
       c.customer_unique_id, t.product_category_name_english
FROM orders AS o
LEFT JOIN order_items AS i ON o.order_id = i.order_id
LEFT JOIN customers AS c ON o.customer_id = c.customer_id
LEFT JOIN products AS p ON i.product_id = p.product_id
LEFT JOIN category_translation AS t ON p.product_category_name = t.product_category_name;
