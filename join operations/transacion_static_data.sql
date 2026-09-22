DROP TABLE IF EXISTS transacion_static_data;
CREATE TABLE transacion_static_data AS
SELECT c.customer_unique_id,
       SUM(CASE WHEN t.product_category_name_english = 'housewares' THEN 1 ELSE 0 END) AS housewares,
       SUM(CASE WHEN t.product_category_name_english = 'sports_leisure' THEN 1 ELSE 0 END) AS sports_leisure,
       SUM(CASE WHEN t.product_category_name_english = 'health_beauty' THEN 1 ELSE 0 END) AS health_beauty,
       SUM(CASE WHEN t.product_category_name_english = 'computers' THEN 1 ELSE 0 END) AS computers,
       SUM(CASE WHEN t.product_category_name_english = 'toys' THEN 1 ELSE 0 END) AS toys
FROM customers AS c
JOIN orders AS o ON c.customer_id = o.customer_id
JOIN order_items AS i ON o.order_id = i.order_id
LEFT JOIN products AS p ON i.product_id = p.product_id
LEFT JOIN category_translation AS t ON p.product_category_name = t.product_category_name
GROUP BY c.customer_unique_id;
