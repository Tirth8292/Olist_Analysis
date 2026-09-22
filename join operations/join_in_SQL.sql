-- Olist joined-data build operations
-- Load the original CSV files into these tables before running this script:
-- customers, geolocation, orders, order_items, order_payments,
-- order_reviews, products, sellers, category_translation
--
-- The SELECT statements use SQLite-compatible SQL. Export each created table
-- to the matching CSV file in this folder after execution.

DROP TABLE IF EXISTS customer_data;
CREATE TABLE customer_data AS
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    g.geolocation_lat,
    g.geolocation_lng
FROM customers AS c
LEFT JOIN geolocation AS g
    ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix;

DROP TABLE IF EXISTS customer_order;
CREATE TABLE customer_order AS
SELECT
    o.order_id,
    o.order_purchase_timestamp,
    i.order_item_id,
    i.product_id,
    i.price,
    i.freight_value,
    c.customer_unique_id,
    t.product_category_name_english
FROM orders AS o
LEFT JOIN order_items AS i
    ON o.order_id = i.order_id
LEFT JOIN customers AS c
    ON o.customer_id = c.customer_id
LEFT JOIN products AS p
    ON i.product_id = p.product_id
LEFT JOIN category_translation AS t
    ON p.product_category_name = t.product_category_name;

DROP TABLE IF EXISTS customer_payment;
CREATE TABLE customer_payment AS
SELECT
    c.customer_unique_id,
    SUM(p.payment_installments) AS payment_installments,
    SUM(p.payment_value) AS payment_value
FROM customers AS c
JOIN orders AS o
    ON c.customer_id = o.customer_id
LEFT JOIN order_payments AS p
    ON o.order_id = p.order_id
GROUP BY c.customer_unique_id;

DROP TABLE IF EXISTS delivery_data;
CREATE TABLE delivery_data AS
SELECT
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    i.seller_id,
    c.customer_unique_id,
    cg.geolocation_lat AS customer_lat,
    cg.geolocation_lng AS customer_lng,
    cg.geolocation_city AS customer_city,
    s.seller_city,
    sg.geolocation_lat AS seller_lat,
    sg.geolocation_lng AS seller_lng
FROM orders AS o
JOIN customers AS c
    ON o.customer_id = c.customer_id
JOIN order_items AS i
    ON o.order_id = i.order_id
LEFT JOIN geolocation AS cg
    ON c.customer_zip_code_prefix = cg.geolocation_zip_code_prefix
LEFT JOIN sellers AS s
    ON i.seller_id = s.seller_id
LEFT JOIN geolocation AS sg
    ON s.seller_zip_code_prefix = sg.geolocation_zip_code_prefix;

DROP TABLE IF EXISTS product_review;
CREATE TABLE product_review AS
SELECT
    r.review_id,
    r.order_id,
    r.review_score,
    r.review_comment_title,
    r.review_comment_message,
    r.review_creation_date,
    r.review_answer_timestamp,
    i.product_id,
    t.product_category_name_english
FROM order_reviews AS r
LEFT JOIN order_items AS i
    ON r.order_id = i.order_id
LEFT JOIN products AS p
    ON i.product_id = p.product_id
LEFT JOIN category_translation AS t
    ON p.product_category_name = t.product_category_name;

DROP TABLE IF EXISTS transacion_static_data;
CREATE TABLE transacion_static_data AS
SELECT
    c.customer_unique_id,
    SUM(CASE WHEN t.product_category_name_english = 'housewares' THEN 1 ELSE 0 END) AS housewares,
    SUM(CASE WHEN t.product_category_name_english = 'sports_leisure' THEN 1 ELSE 0 END) AS sports_leisure,
    SUM(CASE WHEN t.product_category_name_english = 'health_beauty' THEN 1 ELSE 0 END) AS health_beauty,
    SUM(CASE WHEN t.product_category_name_english = 'computers' THEN 1 ELSE 0 END) AS computers,
    SUM(CASE WHEN t.product_category_name_english = 'toys' THEN 1 ELSE 0 END) AS toys
FROM customers AS c
JOIN orders AS o
    ON c.customer_id = o.customer_id
JOIN order_items AS i
    ON o.order_id = i.order_id
LEFT JOIN products AS p
    ON i.product_id = p.product_id
LEFT JOIN category_translation AS t
    ON p.product_category_name = t.product_category_name
GROUP BY c.customer_unique_id;

DROP TABLE IF EXISTS transaction_data;
CREATE TABLE transaction_data AS
SELECT
    c.customer_unique_id,
    o.order_id,
    o.order_purchase_timestamp,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.price,
    i.freight_value,
    t.product_category_name_english,
    p.payment_installments,
    p.payment_value
FROM customers AS c
JOIN orders AS o
    ON c.customer_id = o.customer_id
JOIN order_items AS i
    ON o.order_id = i.order_id
LEFT JOIN products AS pr
    ON i.product_id = pr.product_id
LEFT JOIN category_translation AS t
    ON pr.product_category_name = t.product_category_name
LEFT JOIN order_payments AS p
    ON o.order_id = p.order_id;

-- Optional SQLite export examples:
-- .headers on
-- .mode csv
-- .once join operations/customer_data.csv
-- SELECT * FROM customer_data;
