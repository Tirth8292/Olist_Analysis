select
  order_id,
  customer_id,
  order_status,
  order_purchase_timestamp::date as purchase_date,
  order_purchase_timestamp,
  order_delivered_customer_date,
  order_estimated_delivery_date,
  extract(day from order_delivered_customer_date - order_purchase_timestamp) as delivery_days,
  case
    when order_delivered_customer_date > order_estimated_delivery_date then 1
    else 0
  end as is_late_delivery
from {{ ref('stg_orders') }}

