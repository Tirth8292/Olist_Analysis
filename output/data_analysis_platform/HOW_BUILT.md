# How This Project Was Built

## 1. Raw Data Ingestion

The project starts with the 9 Olist CSV files:

- customers
- orders
- order items
- payments
- reviews
- products
- sellers
- category translations
- geolocation

`src/olist_platform/extract_load.py` reads each CSV, normalizes headers, creates a matching raw table, and loads the records into `data/warehouse/olist.db`.

## 2. Staging Layer

`sql/01_staging.sql` converts raw text fields into analytics-friendly types:

- timestamps for order lifecycle fields
- numeric values for price, freight, payments, product dimensions, and latitude/longitude
- lowercase city names and uppercase state codes
- English product category names through the translation table
- zip-level geolocation averages

## 3. Star Schema

`sql/02_marts.sql` builds the modeled warehouse:

- `dim_customers`
- `dim_sellers`
- `dim_products`
- `dim_dates`
- `fct_orders`
- `fct_order_items`
- `fct_payments`

The fact tables include order status, GMV, delivery days, late delivery flags, and cancellation indicators.

## 4. Business Views

`sql/03_views.sql` creates reusable analytics views:

- `vw_revenue_by_category`
- `vw_delivery_sla_by_state`
- `vw_seller_performance_base`

These views answer executive, operations, and category performance questions without rejoining the raw CSVs manually.

## 5. Feature Engineering

`src/olist_platform/feature_engineering.py` generates:

- `reports/seller_scores.csv`
- `reports/customer_rfm.csv`
- `reports/cohort_retention.csv`
- `reports/delivery_lanes.csv`

Seller score formula:

```text
40% on-time delivery rate
30% average review score
20% inverse cancellation rate
10% revenue growth score
```

## 6. Data Quality

`src/olist_platform/run_quality_checks.py` validates:

- unique order IDs
- unique customer IDs
- order items have valid orders
- orders have valid customers
- payment values are non-negative

## 7. API Layer

`src/olist_platform/api/main.py` exposes:

- `POST /seller/score`
- `GET /delivery/estimate`
- `GET /health`

The API reads the generated feature outputs and returns seller risk tiers, recommendations, and historical delivery estimates.

## 8. Production Readiness

The repository includes:

- `dbt/` model and test scaffolding for a PostgreSQL/Supabase warehouse
- `airflow/dags/olist_pipeline_dag.py` for scheduled orchestration
- `docker-compose.yml` for local Postgres/API setup
- `powerbi/dashboard_spec.md` for dashboard design

This lets the project work locally today while still showing the scalable architecture expected from an analytics engineering portfolio project.

