DROP TABLE IF EXISTS customer_data;
CREATE TABLE customer_data AS
SELECT c.customer_id, c.customer_unique_id, c.customer_zip_code_prefix,
       c.customer_city, c.customer_state,
       g.geolocation_lat, g.geolocation_lng
FROM customers AS c
LEFT JOIN (
    SELECT geolocation_zip_code_prefix,
           AVG(CAST(geolocation_lat AS REAL)) AS geolocation_lat,
           AVG(CAST(geolocation_lng AS REAL)) AS geolocation_lng
    FROM geolocation
    GROUP BY geolocation_zip_code_prefix
) AS g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix;
