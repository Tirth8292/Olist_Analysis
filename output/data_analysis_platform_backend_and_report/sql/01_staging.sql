drop table if exists stg_customers;
create table stg_customers as
select
  customer_id,
  customer_unique_id,
  cast(customer_zip_code_prefix as integer) as customer_zip_code_prefix,
  lower(customer_city) as customer_city,
  upper(customer_state) as customer_state
from raw_customers;

drop table if exists stg_orders;
create table stg_orders as
select
  order_id,
  customer_id,
  lower(order_status) as order_status,
  datetime(order_purchase_timestamp) as order_purchase_timestamp,
  datetime(order_approved_at) as order_approved_at,
  datetime(order_delivered_carrier_date) as order_delivered_carrier_date,
  datetime(order_delivered_customer_date) as order_delivered_customer_date,
  datetime(order_estimated_delivery_date) as order_estimated_delivery_date
from raw_orders;

drop table if exists stg_order_items;
create table stg_order_items as
select
  order_id,
  cast(order_item_id as integer) as order_item_id,
  product_id,
  seller_id,
  datetime(shipping_limit_date) as shipping_limit_date,
  cast(price as real) as price,
  cast(freight_value as real) as freight_value
from raw_order_items;

drop table if exists stg_payments;
create table stg_payments as
select
  order_id,
  cast(payment_sequential as integer) as payment_sequential,
  lower(payment_type) as payment_type,
  cast(payment_installments as integer) as payment_installments,
  cast(payment_value as real) as payment_value
from raw_order_payments;

drop table if exists stg_reviews;
create table stg_reviews as
select
  review_id,
  order_id,
  cast(review_score as integer) as review_score,
  review_comment_title,
  review_comment_message,
  datetime(review_creation_date) as review_creation_date,
  datetime(review_answer_timestamp) as review_answer_timestamp
from raw_order_reviews;

drop table if exists stg_products;
create table stg_products as
select
  p.product_id,
  p.product_category_name,
  coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as product_category_name_english,
  cast(p.product_name_lenght as integer) as product_name_length,
  cast(p.product_description_lenght as integer) as product_description_length,
  cast(p.product_photos_qty as integer) as product_photos_qty,
  cast(p.product_weight_g as real) as product_weight_g,
  cast(p.product_length_cm as real) as product_length_cm,
  cast(p.product_height_cm as real) as product_height_cm,
  cast(p.product_width_cm as real) as product_width_cm
from raw_products p
left join raw_category_translation t
  on p.product_category_name = t.product_category_name;

drop table if exists stg_sellers;
create table stg_sellers as
select
  seller_id,
  cast(seller_zip_code_prefix as integer) as seller_zip_code_prefix,
  lower(seller_city) as seller_city,
  upper(seller_state) as seller_state
from raw_sellers;

drop table if exists stg_geolocation;
create table stg_geolocation as
select
  cast(geolocation_zip_code_prefix as integer) as zip_code_prefix,
  avg(cast(geolocation_lat as real)) as latitude,
  avg(cast(geolocation_lng as real)) as longitude,
  lower(min(geolocation_city)) as city,
  upper(min(geolocation_state)) as state
from raw_geolocation
group by cast(geolocation_zip_code_prefix as integer);

