# Map-First Sales Dashboard Specification

## 1. Dashboard Goal

Build a Power BI dashboard that shows where sales are strongest by city and state, which categories are driving revenue, and how the numbers change after new records are submitted through the live ingestor portal.

This dashboard should feel more like a commercial operations dashboard than a technical warehouse report.

---

## 2. Dashboard Style

Use a clean, executive-friendly layout with:

- a strong geographic map as the hero visual,
- KPI cards for business health,
- top-city and top-state rankings,
- category and seller performance charts,
- a live-refresh loop from the local API.

---

## 3. Recommended Visuals

### Page 1: Sales Geography

Main visual:
- Filled map or bubble map by customer city and state
- Bubble size = GMV
- Bubble color = order volume or average review score

Supporting visuals:
- KPI cards: Total GMV, Delivered Orders, Active Sellers, Avg Review Score
- Top 10 cities by GMV bar chart
- Top 10 states by GMV bar chart
- Monthly GMV trend line chart

### Page 2: Category and Seller Performance

- Top product categories by GMV bar chart
- Top sellers by GMV ranked table
- Delivery performance by state
- Late-delivery risk by seller state

### Page 3: Live Operations Monitor

- Live refresh status card
- New record impact summary
- Recent city growth highlights
- Recent categories and sellers gaining momentum

---

## 4. Data Source Options

### Preferred option: local API

Use Power BI Desktop > Get Data > Web and connect to the local API:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/orders/recent
- http://127.0.0.1:8000/sellers/leaderboard
- http://127.0.0.1:8000/orders/repeat-by-city

### Alternative option: SQLite warehouse

Connect Power BI directly to:

- data/warehouse/olist.db

This is useful when you want direct access to the modeled tables without using the API.

---

## 5. Suggested Power BI Model

Use a simple star schema:

- dim_dates
- dim_customers
- dim_sellers
- dim_products
- fct_orders
- fct_order_items
- fct_payments

Important modeling rules:
- Use one-to-many relationships from dimensions to facts
- Keep the map based on city/state dimensions
- Make customer city the main geographic field for the map

---

## 6. DAX Measures

```dax
Total GMV = SUM(fct_order_items[item_gmv])
```

```dax
Delivered Orders =
CALCULATE(
    DISTINCTCOUNT(fct_orders[order_id]),
    fct_orders[order_status] = "delivered"
)
```

```dax
GMV by City = CALCULATE([Total GMV], ALLEXCEPT(dim_customers, dim_customers[customer_city]))
```

```dax
Orders by City = CALCULATE(DISTINCTCOUNT(fct_orders[order_id]), ALLEXCEPT(dim_customers, dim_customers[customer_city]))
```

```dax
GMV Growth % = DIVIDE([Total GMV] - [Prior Month GMV], [Prior Month GMV])
```

---

## 7. Live Refresh Design

The dashboard should refresh after new data is submitted through the ingestor portal at:

- http://127.0.0.1:8001/

Recommended flow:

1. New record is entered in the ingestor portal.
2. The record is written to the local source data.
3. The analytics layer is rebuilt or refreshed.
4. Power BI performs Refresh All.
5. The map and charts update automatically.

---

## 8. Best Visual Priority

If you want the dashboard to look polished and business-friendly, prioritize these visuals in order:

1. Map by city/state
2. Top cities bar chart
3. KPI cards
4. Monthly GMV trend line
5. Category breakdown bar chart
6. Seller performance table

---

## 9. Final Recommendation

For your use case, the dashboard should be centered around:

- sales concentration by city,
- sales concentration by state,
- top-performing categories,
- live refresh after new ingested records,
- a strong map-first layout that is easy for executives to read.
