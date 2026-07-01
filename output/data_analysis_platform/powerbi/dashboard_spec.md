# Olist Power BI Dashboard Specification

## Overview
This specification covers two dashboards:
1. **Power BI Dashboard** - For deep analysis and sharing
2. **Live Web Dashboard** - For real-time monitoring at `http://127.0.0.1:8002`

---

## Quick Start: Run All Services
Run this script to start everything at once:
```powershell
cd c:\Users\tirth\Documents\Codex\2026-06-23\hi-2\outputs\olist_analytics_platform
python start_all_services.py
```

Services will be available at:
- 📊 Main API: http://127.0.0.1:8000
- 📝 Live Ingestor: http://127.0.0.1:8001
- 🎨 Web Dashboard: http://127.0.0.1:8002

---

## Part 1: Live Web Dashboard (Ready to Use!)
The web dashboard is already built and runs on port 8002! It includes:
- 🔢 KPI Cards (Total GMV, Delivered Orders, Active Sellers, Avg Review)
- 🗺️ Interactive Sales Map (with city-wise GMV and reviews)
- 📊 Top Product Categories Bar Chart
- 📈 Monthly GMV Trend Line
- 💳 Payment Type Distribution Donut Chart

Just click "Refresh Data" to see updates after using the ingestor!

---

## Part 2: Power BI Dashboard Setup

### Step 1: Data Source (Recommended: SQLite Direct Query)
1. Open Power BI Desktop
2. Click **Get Data > From Database > From SQLite Database**
3. Database file path: `c:\Users\tirth\Documents\Codex\2026-06-23\hi-2\outputs\olist_analytics_platform\data\warehouse\olist.db`
4. Select **DirectQuery** mode for real-time updates
5. Import these tables:
   - `dim_customers`
   - `dim_sellers`
   - `dim_products`
   - `dim_dates` (if exists)
   - `fct_orders`
   - `fct_order_items`
   - `fct_payments`
   - `stg_reviews`

### Step 2: Star Schema Relationships
Create these relationships (1-to-many, single direction):
- `dim_customers[customer_id]` → `fct_orders[customer_id]`
- `dim_sellers[seller_id]` → `fct_order_items[seller_id]`
- `dim_products[product_id]` → `fct_order_items[product_id]`
- `fct_orders[order_id]` → `fct_order_items[order_id]`
- `fct_orders[order_id]` → `fct_payments[order_id]`
- `fct_orders[order_id]` → `stg_reviews[order_id]`

### Step 3: Create DAX Measures
```dax
Total GMV = SUM(fct_order_items[item_gmv])

Delivered Orders = 
CALCULATE(
    DISTINCTCOUNT(fct_orders[order_id]),
    fct_orders[order_status] = "delivered"
)

Active Sellers = DISTINCTCOUNT(fct_order_items[seller_id])

Avg Review Score = AVERAGE(stg_reviews[review_score])

Late Delivery Rate = 
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(fct_orders[order_id]),
        fct_orders[is_late_delivery] = 1
    ),
    DISTINCTCOUNT(fct_orders[order_id])
)
```

### Step 4: Build Dashboard Pages

#### Page 1: Executive Commercial Radar
1. KPI Cards:
   - Total GMV
   - Delivered Orders
   - Active Sellers
   - Avg Review Score
   
2. Line Chart:
   - X-axis: `order_purchase_timestamp` (monthly)
   - Y-axis: Total GMV

3. Horizontal Bar Chart:
   - Y-axis: `product_category_name_english` (Top 10)
   - X-axis: Total GMV
   - Legend: Avg Review Score (color coding)

4. Donut Chart:
   - Legend: `payment_type`
   - Values: Count of orders or Total GMV

#### Page 2: Operations & Marketplace Risk
1. Clustered Column Chart:
   - X-axis: Seller State
   - Y-axis: Late Delivery Rate

2. Scatter Plot:
   - X-axis: Average Distance (if available)
   - Y-axis: Average Delivery Days
   - Size: Order Volume

3. Donut Chart:
   - Legend: Seller Risk Tier

4. Table:
   - Top Delivery Lanes (seller state to customer state)
   - Metrics: Volume, Avg Days, Late Rate

#### Page 3: Customer Intelligence
1. Table:
   - Repeat Orders by City/Category
   
2. Heatmap (Matrix):
   - Rows: Cohort Month
   - Columns: Months Since First Purchase
   - Values: Retention Rate

3. Treemap:
   - Groups: RFM Segments
   - Values: Customer Count or Total GMV

### Step 5: Live Refresh
1. After adding records via http://127.0.0.1:8001
2. In Power BI, click **Refresh**
3. All visuals will update automatically!

---

## Data Model Diagram
```
dim_customers ──┐
                ├─ fct_orders ── fct_order_items ── dim_products
dim_sellers ────┘                │
                                 ├─ fct_payments
                                 └─ stg_reviews
```

---

## Troubleshooting
- If SQLite driver not found: Download from https://github.com/ilmax/sqliteodbc/releases
- Use **Import Mode** if DirectQuery is too slow, but click Refresh to get updates
