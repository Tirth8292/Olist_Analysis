drop view if exists vw_revenue_by_category;
create view vw_revenue_by_category as
select
  coalesce(p.product_category_name_english, 'unknown') as category,
  count(distinct i.order_id) as orders,
  count(*) as items_sold,
  round(sum(i.price), 2) as merchandise_revenue,
  round(sum(i.freight_value), 2) as freight_revenue,
  round(sum(i.item_gmv), 2) as gmv,
  round(avg(r.review_score), 2) as avg_review_score,
  round(avg(i.is_late_delivery), 4) as late_delivery_rate
from fct_order_items i
left join dim_products p on i.product_id = p.product_id
left join stg_reviews r on i.order_id = r.order_id
group by 1
order by gmv desc;

drop view if exists vw_delivery_sla_by_state;
create view vw_delivery_sla_by_state as
select
  s.seller_state,
  c.customer_state,
  count(distinct i.order_id) as orders,
  round(avg(i.delivery_days), 2) as avg_delivery_days,
  round(avg(i.is_late_delivery), 4) as late_delivery_rate,
  round(sum(i.item_gmv), 2) as gmv
from fct_order_items i
left join dim_sellers s on i.seller_id = s.seller_id
left join fct_orders o on i.order_id = o.order_id
left join dim_customers c on o.customer_id = c.customer_id
where i.order_status = 'delivered'
group by 1, 2
order by late_delivery_rate desc, orders desc;

drop view if exists vw_seller_performance_base;
create view vw_seller_performance_base as
with seller_monthly as (
  select
    seller_id,
    strftime('%Y-%m', purchase_date) as month,
    sum(item_gmv) as monthly_gmv
  from fct_order_items
  group by 1, 2
),
growth as (
  select
    seller_id,
    first_value(monthly_gmv) over (partition by seller_id order by month) as first_month_gmv,
    first_value(monthly_gmv) over (partition by seller_id order by month desc) as latest_month_gmv
  from seller_monthly
),
seller_reviews as (
  select
    i.seller_id,
    avg(r.review_score) as avg_review_score
  from fct_order_items i
  left join stg_reviews r on i.order_id = r.order_id
  group by 1
)
select
  i.seller_id,
  s.seller_city,
  s.seller_state,
  count(distinct i.order_id) as orders,
  round(sum(i.item_gmv), 2) as gmv,
  round(avg(case when i.order_status = 'delivered' then 1.0 - i.is_late_delivery end), 4) as on_time_delivery_rate,
  round(coalesce(sr.avg_review_score, 0), 2) as avg_review_score,
  round(avg(case when i.order_status = 'canceled' then 1.0 else 0.0 end), 4) as cancellation_rate,
  round(avg(case
    when g.first_month_gmv > 0 then (g.latest_month_gmv - g.first_month_gmv) / g.first_month_gmv
    else 0
  end), 4) as revenue_growth_rate
from fct_order_items i
left join dim_sellers s on i.seller_id = s.seller_id
left join seller_reviews sr on i.seller_id = sr.seller_id
left join growth g on i.seller_id = g.seller_id
group by 1, 2, 3;

