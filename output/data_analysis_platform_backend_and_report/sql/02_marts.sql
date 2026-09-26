drop table if exists dim_customers;
create table dim_customers as
select
  c.customer_id,
  c.customer_unique_id,
  c.customer_zip_code_prefix,
  c.customer_city,
  c.customer_state,
  g.latitude as customer_latitude,
  g.longitude as customer_longitude
from stg_customers c
left join stg_geolocation g
  on c.customer_zip_code_prefix = g.zip_code_prefix;

drop table if exists dim_sellers;
create table dim_sellers as
select
  s.seller_id,
  s.seller_zip_code_prefix,
  s.seller_city,
  s.seller_state,
  g.latitude as seller_latitude,
  g.longitude as seller_longitude
from stg_sellers s
left join stg_geolocation g
  on s.seller_zip_code_prefix = g.zip_code_prefix;

drop table if exists dim_products;
create table dim_products as
select
  product_id,
  product_category_name,
  product_category_name_english,
  product_name_length,
  product_description_length,
  product_photos_qty,
  product_weight_g,
  product_length_cm,
  product_height_cm,
  product_width_cm,
  product_length_cm * product_height_cm * product_width_cm as product_volume_cm3
from stg_products;

drop table if exists dim_dates;
create table dim_dates as
with recursive dates(date_day) as (
  select date(min(order_purchase_timestamp)) from stg_orders
  union all
  select date(date_day, '+1 day')
  from dates
  where date_day < (select date(max(order_estimated_delivery_date)) from stg_orders)
)
select
  date_day,
  strftime('%Y', date_day) as year,
  strftime('%m', date_day) as month,
  strftime('%Y-%m', date_day) as year_month,
  strftime('%w', date_day) as day_of_week
from dates;

drop table if exists fct_orders;
create table fct_orders as
select
  o.order_id,
  o.customer_id,
  c.customer_unique_id,
  o.order_status,
  date(o.order_purchase_timestamp) as purchase_date,
  o.order_purchase_timestamp,
  o.order_approved_at,
  o.order_delivered_carrier_date,
  o.order_delivered_customer_date,
  o.order_estimated_delivery_date,
  case
    when o.order_delivered_customer_date is not null
      then julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)
  end as delivery_days,
  case
    when o.order_delivered_customer_date is not null
     and o.order_estimated_delivery_date is not null
     and o.order_delivered_customer_date > o.order_estimated_delivery_date then 1
    else 0
  end as is_late_delivery,
  case when o.order_status = 'canceled' then 1 else 0 end as is_canceled
from stg_orders o
left join stg_customers c
  on o.customer_id = c.customer_id;

drop table if exists fct_order_items;
create table fct_order_items as
select
  i.order_id,
  i.order_item_id,
  i.product_id,
  i.seller_id,
  i.shipping_limit_date,
  i.price,
  i.freight_value,
  i.price + i.freight_value as item_gmv,
  o.purchase_date,
  o.order_status,
  o.is_late_delivery,
  o.delivery_days
from stg_order_items i
left join fct_orders o
  on i.order_id = o.order_id;

drop table if exists fct_payments;
create table fct_payments as
select
  order_id,
  payment_sequential,
  payment_type,
  payment_installments,
  payment_value
from stg_payments;

