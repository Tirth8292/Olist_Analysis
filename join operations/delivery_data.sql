DROP TABLE IF EXISTS delivery_data;
CREATE TABLE delivery_data AS
SELECT o.order_purchase_timestamp, o.order_delivered_customer_date,
       o.order_estimated_delivery_date, i.seller_id, c.customer_unique_id,
       cg.geolocation_lat AS customer_lat, cg.geolocation_lng AS customer_lng,
       cg.geolocation_city AS customer_city, s.seller_city,
       sg.geolocation_lat AS seller_lat, sg.geolocation_lng AS seller_lng
FROM orders AS o
JOIN customers AS c ON o.customer_id = c.customer_id
JOIN order_items AS i ON o.order_id = i.order_id
LEFT JOIN (
    SELECT geolocation_zip_code_prefix,
           AVG(CAST(geolocation_lat AS REAL)) AS geolocation_lat,
           AVG(CAST(geolocation_lng AS REAL)) AS geolocation_lng,
           MIN(geolocation_city) AS geolocation_city
    FROM geolocation GROUP BY geolocation_zip_code_prefix
) AS cg ON c.customer_zip_code_prefix = cg.geolocation_zip_code_prefix
LEFT JOIN sellers AS s ON i.seller_id = s.seller_id
LEFT JOIN (
    SELECT geolocation_zip_code_prefix,
           AVG(CAST(geolocation_lat AS REAL)) AS geolocation_lat,
           AVG(CAST(geolocation_lng AS REAL)) AS geolocation_lng
    FROM geolocation GROUP BY geolocation_zip_code_prefix
) AS sg ON s.seller_zip_code_prefix = sg.geolocation_zip_code_prefix;
