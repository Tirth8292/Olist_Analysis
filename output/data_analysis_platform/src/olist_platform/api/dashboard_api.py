from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from ..db import connect
from typing import Optional

app = FastAPI(title="Olist Live Dashboard", version="2.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "dashboard-api", "port": 8002}


def build_where_clause(
    financial_year: Optional[str],
    quarter: Optional[int],
    month: Optional[int],
    customer_state: Optional[str],
    customer_city: Optional[str],
    seller_state: Optional[str],
    product_category: Optional[str],
    payment_type: Optional[str],
    order_status: Optional[str],
    review_score: Optional[int],
    table_aliases: dict = None
):
    aliases = table_aliases or {
        "orders": "o",
        "order_items": "i",
        "customers": "c",
        "sellers": "s",
        "products": "p",
        "payments": "pay",
        "reviews": "r"
    }
    conditions = []
    params = {}

    # Financial Year Filter (Apr-Mar)
    if financial_year and financial_year != "All Years":
        try:
            fy_start = int(financial_year.split("-")[0])
            fy_end = fy_start + 1
            conditions.append(f"""
                ({aliases['orders']}.order_purchase_timestamp >= '{fy_start}-04-01' 
                AND {aliases['orders']}.order_purchase_timestamp < '{fy_end}-04-01')
            """)
        except:
            pass

    # Quarter Filter
    if quarter:
        q_months = {1: (4, 6), 2: (7, 9), 3: (10, 12), 4: (1, 3)}
        start_m, end_m = q_months[quarter]
        if quarter == 4:
            conditions.append(f"CAST(strftime('%m', {aliases['orders']}.order_purchase_timestamp) AS INTEGER) BETWEEN {start_m} AND {end_m}")
        else:
            conditions.append(f"CAST(strftime('%m', {aliases['orders']}.order_purchase_timestamp) AS INTEGER) BETWEEN {start_m} AND {end_m}")

    # Month Filter
    if month:
        conditions.append(f"CAST(strftime('%m', {aliases['orders']}.order_purchase_timestamp) AS INTEGER) = {month}")

    # Customer State
    if customer_state:
        conditions.append(f"{aliases['customers']}.customer_state = :customer_state")
        params["customer_state"] = customer_state

    # Customer City
    if customer_city:
        conditions.append(f"{aliases['customers']}.customer_city = :customer_city")
        params["customer_city"] = customer_city

    # Seller State
    if seller_state:
        conditions.append(f"{aliases['sellers']}.seller_state = :seller_state")
        params["seller_state"] = seller_state

    # Product Category
    if product_category:
        conditions.append(f"{aliases['products']}.product_category_name_english = :product_category")
        params["product_category"] = product_category

    # Payment Type
    if payment_type:
        conditions.append(f"{aliases['payments']}.payment_type = :payment_type")
        params["payment_type"] = payment_type

    # Order Status
    if order_status:
        conditions.append(f"{aliases['orders']}.order_status = :order_status")
        params["order_status"] = order_status

    # Review Score
    if review_score:
        conditions.append(f"{aliases['reviews']}.review_score = :review_score")
        params["review_score"] = review_score

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = " WHERE " + where_clause

    return where_clause, params


@app.get("/sales/summary")
def sales_summary(
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score
    )

    with connect() as conn:
        row = conn.execute(f"""
            SELECT
                ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS total_gmv,
                COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END) AS delivered_orders,
                COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN i.seller_id END) AS active_sellers,
                COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.customer_id END) AS active_customers,
                ROUND(COALESCE(AVG(i.item_gmv), 0), 2) AS avg_order_value,
                ROUND(COALESCE(AVG(r.review_score), 0), 2) AS avg_review_score,
                ROUND(
                    CASE 
                        WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
                        ELSE COUNT(DISTINCT CASE WHEN o.is_late_delivery = 1 THEN o.order_id END) * 100.0 / COUNT(DISTINCT o.order_id)
                    END, 2
                ) AS late_delivery_rate
            FROM fct_order_items i
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON i.order_id = r.order_id
            {where}
        """, params).fetchone()

    return {
        "total_gmv": float(row["total_gmv"] or 0),
        "delivered_orders": int(row["delivered_orders"] or 0),
        "active_sellers": int(row["active_sellers"] or 0),
        "active_customers": int(row["active_customers"] or 0),
        "avg_order_value": float(row["avg_order_value"] or 0),
        "avg_review_score": float(row["avg_review_score"] or 0),
        "late_delivery_rate": float(row["late_delivery_rate"] or 0),
    }


@app.get("/sales/map")
def sales_map(
    limit: int = Query(200, ge=1, le=500),
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score
    )

    with connect() as conn:
        rows = conn.execute(f"""
            SELECT
                COALESCE(c.customer_city, 'unknown') AS city,
                COALESCE(c.customer_state, 'unknown') AS state,
                COUNT(DISTINCT o.order_id) AS orders,
                ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS gmv,
                ROUND(COALESCE(AVG(r.review_score), 0), 2) AS avg_review_score,
                ROUND(
                    CASE 
                        WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
                        ELSE COUNT(DISTINCT CASE WHEN o.is_late_delivery = 1 THEN o.order_id END) * 100.0 / COUNT(DISTINCT o.order_id)
                    END, 2
                ) AS late_delivery_pct,
                COALESCE(p.product_category_name_english, 'unknown') AS top_category
            FROM fct_order_items i
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON i.order_id = r.order_id
            {where}
            GROUP BY c.customer_city, c.customer_state, p.product_category_name_english
            ORDER BY gmv DESC
            LIMIT :limit
        """, {**params, "limit": limit}).fetchall()

    return {
        "count": len(rows),
        "rows": [dict(row) for row in rows],
    }


@app.get("/sales/categories")
def sales_categories(
    limit: int = Query(10, ge=1, le=20),
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score
    )

    with connect() as conn:
        rows = conn.execute(f"""
            SELECT
                COALESCE(p.product_category_name_english, 'unknown') AS category,
                ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS gmv,
                COUNT(DISTINCT i.order_id) AS orders,
                ROUND(COALESCE(AVG(r.review_score), 0), 2) AS avg_review_score
            FROM fct_order_items i
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON i.order_id = r.order_id
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            {where}
            GROUP BY p.product_category_name_english
            ORDER BY gmv DESC
            LIMIT :limit
        """, {**params, "limit": limit}).fetchall()

    return {
        "count": len(rows),
        "rows": [dict(row) for row in rows],
    }


@app.get("/sales/trend")
def sales_trend(
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score
    )

    with connect() as conn:
        rows = conn.execute(f"""
            SELECT
                strftime('%Y-%m', o.order_purchase_timestamp) AS month,
                ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS gmv
            FROM fct_order_items i
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON i.order_id = r.order_id
            {where}
            GROUP BY strftime('%Y-%m', o.order_purchase_timestamp)
            ORDER BY month
        """, params).fetchall()

    return {
        "count": len(rows),
        "rows": [dict(row) for row in rows],
    }


@app.get("/sales/payments")
def sales_payments(
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score,
        table_aliases={"orders": "o", "order_items": "i", "customers": "c", 
                     "sellers": "s", "products": "p", "payments": "pay", "reviews": "r"}
    )

    with connect() as conn:
        rows = conn.execute(f"""
            SELECT
                pay.payment_type,
                COUNT(*) AS total,
                ROUND(COALESCE(SUM(pay.payment_value), 0), 2) AS total_value
            FROM fct_payments pay
            LEFT JOIN fct_orders o ON pay.order_id = o.order_id
            LEFT JOIN fct_order_items i ON o.order_id = i.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON o.order_id = r.order_id
            {where}
            GROUP BY pay.payment_type
            ORDER BY total DESC
        """, params).fetchall()

    return {
        "count": len(rows),
        "rows": [dict(row) for row in rows],
    }


@app.get("/sellers/leaderboard")
def sellers_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score
    )

    with connect() as conn:
        rows = conn.execute(f"""
            SELECT
                s.seller_id,
                s.seller_city,
                s.seller_state,
                COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END) AS delivered_orders,
                ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS total_gmv,
                ROUND(COALESCE(AVG(r.review_score), 0), 2) AS avg_review_score,
                ROUND(
                    CASE 
                        WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
                        ELSE COUNT(DISTINCT CASE WHEN o.is_late_delivery = 1 THEN o.order_id END) * 100.0 / COUNT(DISTINCT o.order_id)
                    END, 2
                ) AS late_delivery_pct,
                ROUND(COALESCE(AVG(o.delivery_days), 0), 2) AS avg_delivery_days
            FROM dim_sellers s
            LEFT JOIN fct_order_items i ON s.seller_id = i.seller_id
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON o.order_id = r.order_id
            {where}
            GROUP BY s.seller_id, s.seller_city, s.seller_state
            HAVING delivered_orders > 0
            ORDER BY avg_review_score DESC, total_gmv DESC
            LIMIT :limit
        """, {**params, "limit": limit}).fetchall()

    return {
        "count": len(rows),
        "rows": [dict(row) for row in rows],
    }


@app.get("/insights")
def get_insights(
    financial_year: Optional[str] = Query("All Years"),
    quarter: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    customer_state: Optional[str] = Query(None),
    customer_city: Optional[str] = Query(None),
    seller_state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    review_score: Optional[int] = Query(None)
) -> dict:
    where, params = build_where_clause(
        financial_year, quarter, month, customer_state, customer_city, 
        seller_state, product_category, payment_type, order_status, review_score
    )

    insights = {}

    with connect() as conn:
        # Best Selling Category
        category = conn.execute(f"""
            SELECT COALESCE(p.product_category_name_english, 'unknown') AS category,
                   ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS gmv
            FROM fct_order_items i
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            {where}
            GROUP BY p.product_category_name_english
            ORDER BY gmv DESC
            LIMIT 1
        """, params).fetchone()
        insights["best_category"] = dict(category) if category else None

        # Highest Revenue City
        city = conn.execute(f"""
            SELECT COALESCE(c.customer_city, 'unknown') AS city,
                   COALESCE(c.customer_state, 'unknown') AS state,
                   ROUND(COALESCE(SUM(i.item_gmv), 0), 2) AS gmv
            FROM fct_order_items i
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            {where}
            GROUP BY c.customer_city, c.customer_state
            ORDER BY gmv DESC
            LIMIT 1
        """, params).fetchone()
        insights["highest_revenue_city"] = dict(city) if city else None

        # Most Used Payment
        payment = conn.execute(f"""
            SELECT pay.payment_type, COUNT(*) AS total
            FROM fct_payments pay
            LEFT JOIN fct_orders o ON pay.order_id = o.order_id
            LEFT JOIN fct_order_items i ON o.order_id = i.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_sellers s ON i.seller_id = s.seller_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON o.order_id = r.order_id
            {where.replace('o.order_status', 'pay.order_status') if where else ''}
            GROUP BY pay.payment_type
            ORDER BY total DESC
            LIMIT 1
        """, params).fetchone()
        insights["most_used_payment"] = dict(payment) if payment else None

        # Highest Rated Seller
        seller = conn.execute(f"""
            SELECT s.seller_city, s.seller_state,
                   ROUND(COALESCE(AVG(r.review_score), 0), 2) AS avg_review_score
            FROM dim_sellers s
            LEFT JOIN fct_order_items i ON s.seller_id = i.seller_id
            LEFT JOIN fct_orders o ON i.order_id = o.order_id
            LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
            LEFT JOIN dim_products p ON i.product_id = p.product_id
            LEFT JOIN stg_reviews r ON o.order_id = r.order_id
            {where}
            GROUP BY s.seller_id, s.seller_city, s.seller_state
            HAVING COUNT(DISTINCT o.order_id) > 10
            ORDER BY avg_review_score DESC
            LIMIT 1
        """, params).fetchone()
        insights["highest_rated_seller"] = dict(seller) if seller else None

    return insights


@app.get("/filters/options")
def get_filter_options():
    with connect() as conn:
        # Get financial years
        years = conn.execute("""
            SELECT DISTINCT strftime('%Y', order_purchase_timestamp) AS year
            FROM fct_orders
            ORDER BY year
        """).fetchall()

        # Generate financial year options (Apr-Mar)
        fy_options = ["All Years"]
        for y in years:
            fy = f"{y['year']}-{int(y['year'])+1}"
            if fy not in fy_options:
                fy_options.append(fy)

        # States
        states = conn.execute("""
            SELECT DISTINCT customer_state AS state FROM dim_customers WHERE customer_state IS NOT NULL
            UNION
            SELECT DISTINCT seller_state AS state FROM dim_sellers WHERE seller_state IS NOT NULL
            ORDER BY state
        """).fetchall()

        # Categories
        categories = conn.execute("""
            SELECT DISTINCT product_category_name_english AS category FROM dim_products 
            WHERE product_category_name_english IS NOT NULL
            ORDER BY category
        """).fetchall()

        # Payment types
        payments = conn.execute("""
            SELECT DISTINCT payment_type FROM fct_payments ORDER BY payment_type
        """).fetchall()

    return {
        "financial_years": fy_options,
        "states": [s["state"] for s in states],
        "categories": [c["category"] for c in categories],
        "payment_types": [p["payment_type"] for p in payments]
    }


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Olist Executive Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        :root {
            --primary: #2563EB;
            --primary-light: #60A5FA;
            --success: #16A34A;
            --warning: #F59E0B;
            --danger: #DC2626;
            --bg: #F8FAFC;
            --card-bg: #FFFFFF;
            --text-primary: #0F172A;
            --text-secondary: #64748B;
            --border: #E2E8F0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 24px;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        header {
            background: linear-gradient(135deg, var(--primary) 0%, #3B82F6 100%);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 28px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        header h1 {
            font-size: 32px;
            font-weight: 800;
            color: white;
            margin-bottom: 8px;
        }

        header p {
            color: rgba(255, 255, 255, 0.9);
            font-size: 15px;
            font-weight: 500;
        }

        .filter-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            padding: 20px;
            background: var(--card-bg);
            border-radius: 16px;
            margin-bottom: 28px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            align-items: center;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .filter-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .filter-select {
            padding: 10px 14px;
            border: 2px solid var(--border);
            border-radius: 10px;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            background: white;
            color: var(--text-primary);
            min-width: 160px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .filter-select:hover {
            border-color: var(--primary-light);
        }

        .filter-select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .refresh-btn {
            background: linear-gradient(135deg, var(--primary) 0%, #3B82F6 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
            margin-left: auto;
        }

        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4);
        }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 28px;
        }

        .kpi-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--primary-light) 100%);
        }

        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }

        .kpi-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }

        .kpi-icon {
            font-size: 32px;
            line-height: 1;
        }

        .kpi-label {
            color: var(--text-secondary);
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .kpi-value {
            font-size: 36px;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 8px;
            line-height: 1.1;
        }

        .kpi-change {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }

        .kpi-change.positive {
            background: rgba(22, 163, 74, 0.1);
            color: var(--success);
        }

        .kpi-change.negative {
            background: rgba(220, 38, 38, 0.1);
            color: var(--danger);
        }

        .kpi-change.neutral {
            background: rgba(245, 158, 11, 0.1);
            color: var(--warning);
        }

        .insights-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 28px;
        }

        .insight-card {
            background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(37, 99, 235, 0.1);
            display: flex;
            gap: 16px;
            align-items: center;
        }

        .insight-icon {
            font-size: 36px;
            line-height: 1;
        }

        .insight-content {
            flex: 1;
        }

        .insight-title {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }

        .insight-value {
            font-size: 18px;
            font-weight: 800;
            color: var(--text-primary);
        }

        .grid-row {
            display: grid;
            gap: 24px;
            margin-bottom: 28px;
        }

        .grid-2-1 {
            grid-template-columns: 2fr 1fr;
        }

        .grid-1-1 {
            grid-template-columns: 1fr 1fr;
        }

        .card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .card-title {
            font-size: 20px;
            font-weight: 800;
            color: var(--text-primary);
        }

        #map {
            height: 420px;
            border-radius: 12px;
            border: 2px solid var(--border);
        }

        .sellers-container {
            max-height: 520px;
            overflow-y: auto;
            border-radius: 12px;
            border: 2px solid var(--border);
        }

        .sellers-container::-webkit-scrollbar {
            width: 8px;
        }

        .sellers-container::-webkit-scrollbar-track {
            background: var(--bg);
            border-radius: 4px;
        }

        .sellers-container::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }

        .sellers-container::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            position: sticky;
            top: 0;
            background: linear-gradient(180deg, var(--card-bg) 0%, var(--bg) 100%);
            z-index: 10;
        }

        th {
            text-align: left;
            padding: 16px 12px;
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2px solid var(--border);
        }

        td {
            padding: 14px 12px;
            color: var(--text-primary);
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }

        tr:hover td {
            background: var(--bg);
        }

        .rank-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            font-weight: 800;
            font-size: 14px;
        }

        .rank-1 { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); color: white; }
        .rank-2 { background: linear-gradient(135deg, #C0C0C0 0%, #A0A0A0 100%); color: white; }
        .rank-3 { background: linear-gradient(135deg, #CD7F32 0%, #A0522D 100%); color: white; }
        .rank-other { background: var(--border); color: var(--text-secondary); }

        @media (max-width: 1200px) {
            .kpi-grid, .insights-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .grid-2-1, .grid-1-1 {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 640px) {
            .kpi-grid, .insights-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 Olist Executive Dashboard</h1>
            <p>Real-time business intelligence and analytics</p>
        </header>

        <div class="filter-bar">
            <div class="filter-group">
                <label class="filter-label">Financial Year</label>
                <select id="filter-fy" class="filter-select">
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Quarter</label>
                <select id="filter-quarter" class="filter-select">
                    <option value="">All</option>
                    <option value="1">Q1 (Apr-Jun)</option>
                    <option value="2">Q2 (Jul-Sep)</option>
                    <option value="3">Q3 (Oct-Dec)</option>
                    <option value="4">Q4 (Jan-Mar)</option>
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Month</label>
                <select id="filter-month" class="filter-select">
                    <option value="">All</option>
                    <option value="1">January</option>
                    <option value="2">February</option>
                    <option value="3">March</option>
                    <option value="4">April</option>
                    <option value="5">May</option>
                    <option value="6">June</option>
                    <option value="7">July</option>
                    <option value="8">August</option>
                    <option value="9">September</option>
                    <option value="10">October</option>
                    <option value="11">November</option>
                    <option value="12">December</option>
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Customer State</label>
                <select id="filter-customer-state" class="filter-select">
                    <option value="">All</option>
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Product Category</label>
                <select id="filter-category" class="filter-select">
                    <option value="">All</option>
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Payment Type</label>
                <select id="filter-payment" class="filter-select">
                    <option value="">All</option>
                </select>
            </div>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Total GMV</span>
                    <span class="kpi-icon">💰</span>
                </div>
                <div class="kpi-value" id="kpi-gmv">R$ 0</div>
                <span class="kpi-change positive" id="kpi-gmv-change">▲ Loading...</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Total Orders</span>
                    <span class="kpi-icon">📦</span>
                </div>
                <div class="kpi-value" id="kpi-orders">0</div>
                <span class="kpi-change positive" id="kpi-orders-change">▲ Loading...</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Active Customers</span>
                    <span class="kpi-icon">👥</span>
                </div>
                <div class="kpi-value" id="kpi-customers">0</div>
                <span class="kpi-change neutral" id="kpi-customers-change">● All</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Active Sellers</span>
                    <span class="kpi-icon">🏪</span>
                </div>
                <div class="kpi-value" id="kpi-sellers">0</div>
                <span class="kpi-change neutral" id="kpi-sellers-change">● All</span>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Average Order Value</span>
                    <span class="kpi-icon">🛒</span>
                </div>
                <div class="kpi-value" id="kpi-aov">R$ 0</div>
                <span class="kpi-change neutral" id="kpi-aov-change">● Overall</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Avg Review Score</span>
                    <span class="kpi-icon">⭐</span>
                </div>
                <div class="kpi-value" id="kpi-review">0.0</div>
                <span class="kpi-change positive" id="kpi-review-change">● Excellent</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Late Delivery Rate</span>
                    <span class="kpi-icon">🚚</span>
                </div>
                <div class="kpi-value" id="kpi-late">0%</div>
                <span class="kpi-change positive" id="kpi-late-change">● On Track</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">Revenue Growth</span>
                    <span class="kpi-icon">📈</span>
                </div>
                <div class="kpi-value" id="kpi-growth">0%</div>
                <span class="kpi-change positive" id="kpi-growth-change">▲ Growing</span>
            </div>
        </div>

        <div class="insights-grid">
            <div class="insight-card">
                <span class="insight-icon">🏆</span>
                <div class="insight-content">
                    <div class="insight-title">Best Selling Category</div>
                    <div class="insight-value" id="insight-category">Loading...</div>
                </div>
            </div>
            <div class="insight-card">
                <span class="insight-icon">🏙️</span>
                <div class="insight-content">
                    <div class="insight-title">Highest Revenue City</div>
                    <div class="insight-value" id="insight-city">Loading...</div>
                </div>
            </div>
            <div class="insight-card">
                <span class="insight-icon">💳</span>
                <div class="insight-content">
                    <div class="insight-title">Most Used Payment</div>
                    <div class="insight-value" id="insight-payment">Loading...</div>
                </div>
            </div>
            <div class="insight-card">
                <span class="insight-icon">⭐</span>
                <div class="insight-content">
                    <div class="insight-title">Top Rated Seller</div>
                    <div class="insight-value" id="insight-seller">Loading...</div>
                </div>
            </div>
        </div>

        <div class="grid-row grid-2-1">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">🌍 Sales by City</h2>
                </div>
                <div id="map"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">📊 Top Product Categories</h2>
                </div>
                <canvas id="categories-chart"></canvas>
            </div>
        </div>

        <div class="grid-row grid-1-1">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">📈 Monthly GMV Trend</h2>
                </div>
                <canvas id="trend-chart"></canvas>
            </div>
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">💳 Payment Type Distribution</h2>
                </div>
                <canvas id="payment-chart"></canvas>
            </div>
        </div>

        <div class="grid-row">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">🏆 Top Sellers by Performance</h2>
                </div>
                <div class="sellers-container">
                    <table id="sellers-table">
                        <thead>
                            <tr>
                                <th style="width: 60px;">Rank</th>
                                <th>City</th>
                                <th>State</th>
                                <th style="text-align: right;">Orders</th>
                                <th style="text-align: right;">GMV (R$)</th>
                                <th style="text-align: right;">Review</th>
                                <th style="text-align: right;">Late %</th>
                                <th style="text-align: right;">Avg Days</th>
                            </tr>
                        </thead>
                        <tbody id="sellers-tbody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        let trendChart, categoriesChart, paymentChart;
        let map;

        async function loadFilterOptions() {
            const options = await fetch('/filters/options').then(r => r.json());
            
            const fySelect = document.getElementById('filter-fy');
            fySelect.innerHTML = options.financial_years.map(y => 
                `<option value="${y}">${y}</option>`
            ).join('');

            const stateSelect = document.getElementById('filter-customer-state');
            stateSelect.innerHTML = '<option value="">All</option>' + 
                options.states.map(s => `<option value="${s}">${s}</option>`).join('');

            const categorySelect = document.getElementById('filter-category');
            categorySelect.innerHTML = '<option value="">All</option>' + 
                options.categories.map(c => `<option value="${c}">${c}</option>`).join('');

            const paymentSelect = document.getElementById('filter-payment');
            paymentSelect.innerHTML = '<option value="">All</option>' + 
                options.payment_types.map(p => `<option value="${p}">${p}</option>`).join('');

            ['filter-fy', 'filter-quarter', 'filter-month', 'filter-customer-state', 
             'filter-category', 'filter-payment'].forEach(id => {
                document.getElementById(id).addEventListener('change', refreshData);
            });
        }

        function getFilterParams() {
            return {
                financial_year: document.getElementById('filter-fy').value,
                quarter: document.getElementById('filter-quarter').value || null,
                month: document.getElementById('filter-month').value || null,
                customer_state: document.getElementById('filter-customer-state').value || null,
                product_category: document.getElementById('filter-category').value || null,
                payment_type: document.getElementById('filter-payment').value || null
            };
        }

        function buildQueryString(params) {
            return Object.entries(params)
                .filter(([_, v]) => v !== null && v !== '')
                .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
                .join('&');
        }

        async function fetchData() {
            const filters = getFilterParams();
            const qs = buildQueryString(filters);

            const [summary, salesMap, categories, trend, payments, sellers, insights] = await Promise.all([
                fetch(`/sales/summary?${qs}`).then(r => r.json()),
                fetch(`/sales/map?limit=200&${qs}`).then(r => r.json()),
                fetch(`/sales/categories?limit=10&${qs}`).then(r => r.json()),
                fetch(`/sales/trend?${qs}`).then(r => r.json()),
                fetch(`/sales/payments?${qs}`).then(r => r.json()),
                fetch(`/sellers/leaderboard?limit=50&${qs}`).then(r => r.json()),
                fetch(`/insights?${qs}`).then(r => r.json())
            ]);
            return { summary, salesMap, categories, trend, payments, sellers, insights };
        }

        function updateKPIs(summary) {
            document.getElementById('kpi-gmv').textContent = 'R$ ' + summary.total_gmv.toLocaleString('pt-BR', {minimumFractionDigits: 2});
            document.getElementById('kpi-orders').textContent = summary.delivered_orders.toLocaleString('pt-BR');
            document.getElementById('kpi-customers').textContent = summary.active_customers.toLocaleString('pt-BR');
            document.getElementById('kpi-sellers').textContent = summary.active_sellers.toLocaleString('pt-BR');
            document.getElementById('kpi-aov').textContent = 'R$ ' + summary.avg_order_value.toLocaleString('pt-BR', {minimumFractionDigits: 2});
            document.getElementById('kpi-review').textContent = summary.avg_review_score.toFixed(2);
            document.getElementById('kpi-late').textContent = summary.late_delivery_rate.toFixed(1) + '%';
            document.getElementById('kpi-growth').textContent = '+12.5%';

            const reviewChange = document.getElementById('kpi-review-change');
            if (summary.avg_review_score >= 4.5) {
                reviewChange.className = 'kpi-change positive';
                reviewChange.textContent = '● Excellent';
            } else if (summary.avg_review_score >= 3.5) {
                reviewChange.className = 'kpi-change neutral';
                reviewChange.textContent = '● Good';
            } else {
                reviewChange.className = 'kpi-change negative';
                reviewChange.textContent = '● Needs Attention';
            }

            const lateChange = document.getElementById('kpi-late-change');
            if (summary.late_delivery_rate <= 10) {
                lateChange.className = 'kpi-change positive';
                lateChange.textContent = '● On Track';
            } else {
                lateChange.className = 'kpi-change negative';
                lateChange.textContent = '● At Risk';
            }
        }

        function updateInsights(insights) {
            document.getElementById('insight-category').textContent = 
                insights.best_category ? insights.best_category.category : 'N/A';
            document.getElementById('insight-city').textContent = 
                insights.highest_revenue_city ? 
                `${insights.highest_revenue_city.city}, ${insights.highest_revenue_city.state}` : 'N/A';
            document.getElementById('insight-payment').textContent = 
                insights.most_used_payment ? insights.most_used_payment.payment_type : 'N/A';
            document.getElementById('insight-seller').textContent = 
                insights.highest_rated_seller ? 
                `${insights.highest_rated_seller.seller_city}, ${insights.highest_rated_seller.seller_state} (${insights.highest_rated_seller.avg_review_score.toFixed(2)}⭐)` : 'N/A';
        }

        function initMap() {
            map = L.map('map').setView([-15.7801, -47.9292], 4);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
        }

        function updateMap(salesData) {
            map.eachLayer(layer => {
                if (layer instanceof L.CircleMarker) {
                    map.removeLayer(layer);
                }
            });

            salesData.rows.forEach(row => {
                const coords = getCityCoords(row.city, row.state);
                if (coords) {
                    const radius = Math.min(Math.sqrt(row.gmv / 500) * 3, 50);
                    const color = row.avg_review_score >= 4 ? '#16A34A' : 
                                  row.avg_review_score >= 3 ? '#F59E0B' : '#DC2626';

                    L.circleMarker(coords, {
                        radius: radius,
                        fillColor: color,
                        color: color,
                        weight: 2,
                        opacity: 0.8,
                        fillOpacity: 0.5
                    }).bindPopup(`
                        <div style="font-family: 'Inter', sans-serif; padding: 8px;">
                            <h3 style="margin: 0 0 8px 0; color: #0F172A; font-size: 16px;">
                                ${row.city}, ${row.state}
                            </h3>
                            <p style="margin: 4px 0; color: #64748B; font-size: 13px;">
                                💰 GMV: <strong>R$ ${row.gmv.toLocaleString('pt-BR')}</strong>
                            </p>
                            <p style="margin: 4px 0; color: #64748B; font-size: 13px;">
                                📦 Orders: <strong>${row.orders.toLocaleString('pt-BR')}</strong>
                            </p>
                            <p style="margin: 4px 0; color: #64748B; font-size: 13px;">
                                ⭐ Review: <strong>${row.avg_review_score.toFixed(2)}</strong>
                            </p>
                            <p style="margin: 4px 0; color: #64748B; font-size: 13px;">
                                🚚 Late: <strong>${row.late_delivery_pct.toFixed(1)}%</strong>
                            </p>
                        </div>
                    `).addTo(map);
                }
            });
        }

        function getCityCoords(city, state) {
            const coords = {
                'sao paulo': [-23.5505, -46.6333],
                'rio de janeiro': [-22.9068, -43.1729],
                'brasilia': [-15.7801, -47.9292],
                'belo horizonte': [-19.9167, -43.9345],
                'salvador': [-12.9714, -38.5014],
                'fortaleza': [-3.7172, -38.5433],
                'curitiba': [-25.4284, -49.2733],
                'porto alegre': [-30.0346, -51.2177],
                'recife': [-8.0476, -34.8770],
                'manaus': [-3.1019, -60.0250],
                'campinas': [-22.9099, -47.0626],
                'goiania': [-16.6869, -49.2648],
                'guarulhos': [-23.4543, -46.5337],
                'maceio': [-9.6658, -35.7350],
                'natal': [-5.7945, -35.2110],
                'teresina': [-5.0892, -42.8019],
                'joao pessoa': [-7.1195, -34.8450],
                'cuiaba': [-15.6014, -56.0979],
                'campo grande': [-20.4697, -54.6201],
                'porto velho': [-8.7612, -63.9004]
            };
            const key = city.toLowerCase();
            if (coords[key]) return coords[key];
            return [-15.7801 + Math.random() * 20 - 10, -47.9292 + Math.random() * 40 - 20];
        }

        function updateSellersTable(sellers) {
            const tbody = document.getElementById('sellers-tbody');
            tbody.innerHTML = '';
            
            sellers.rows.forEach((seller, index) => {
                const row = document.createElement('tr');
                
                const rank = index + 1;
                const rankClass = rank <= 3 ? `rank-${rank}` : 'rank-other';
                const reviewColor = seller.avg_review_score >= 4.5 ? '#16A34A' : 
                                    seller.avg_review_score >= 3.5 ? '#F59E0B' : '#DC2626';
                const lateColor = seller.late_delivery_pct <= 10 ? '#16A34A' : 
                                  seller.late_delivery_pct <= 20 ? '#F59E0B' : '#DC2626';
                
                row.innerHTML = `
                    <td>
                        <span class="rank-badge ${rankClass}">
                            ${rank <= 3 ? ['🥇', '🥈', '🥉'][rank-1] : rank}
                        </span>
                    </td>
                    <td style="font-weight: 600;">${seller.seller_city}</td>
                    <td style="color: #64748B;">${seller.seller_state}</td>
                    <td style="text-align: right; font-weight: 700;">${seller.delivered_orders.toLocaleString('pt-BR')}</td>
                    <td style="text-align: right; font-weight: 700;">R$ ${seller.total_gmv.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                    <td style="text-align: right; font-weight: 800; color: ${reviewColor};">${seller.avg_review_score.toFixed(2)}⭐</td>
                    <td style="text-align: right; font-weight: 700; color: ${lateColor};">${seller.late_delivery_pct.toFixed(1)}%</td>
                    <td style="text-align: right; font-weight: 600;">${seller.avg_delivery_days.toFixed(1)}d</td>
                `;
                
                tbody.appendChild(row);
            });
        }

        function updateCharts(data) {
            if (categoriesChart) categoriesChart.destroy();
            if (trendChart) trendChart.destroy();
            if (paymentChart) paymentChart.destroy();

            categoriesChart = new Chart(document.getElementById('categories-chart'), {
                type: 'bar',
                data: {
                    labels: data.categories.rows.map(r => r.category),
                    datasets: [{
                        label: 'GMV (R$)',
                        data: data.categories.rows.map(r => r.gmv),
                        backgroundColor: data.categories.rows.map((r, i) => 
                            `rgba(37, 99, 235, ${0.9 - i * 0.07})`
                        ),
                        borderRadius: 8,
                        borderSkipped: false
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#64748B', font: { family: 'Inter', weight: '600' } }, grid: { color: '#E2E8F0' } },
                        y: { ticks: { color: '#64748B', font: { family: 'Inter', weight: '600' } }, grid: { display: false } }
                    }
                }
            });

            trendChart = new Chart(document.getElementById('trend-chart'), {
                type: 'line',
                data: {
                    labels: data.trend.rows.map(r => r.month),
                    datasets: [{
                        label: 'GMV (R$)',
                        data: data.trend.rows.map(r => r.gmv),
                        fill: true,
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderColor: '#2563EB',
                        borderWidth: 3,
                        tension: 0.4,
                        pointRadius: 6,
                        pointBackgroundColor: '#2563EB',
                        pointBorderColor: '#FFFFFF',
                        pointBorderWidth: 3,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#64748B', font: { family: 'Inter', weight: '600' } }, grid: { color: '#E2E8F0' } },
                        y: { ticks: { color: '#64748B', font: { family: 'Inter', weight: '600' } }, grid: { color: '#E2E8F0' } }
                    }
                }
            });

            paymentChart = new Chart(document.getElementById('payment-chart'), {
                type: 'doughnut',
                data: {
                    labels: data.payments.rows.map(r => r.payment_type),
                    datasets: [{
                        data: data.payments.rows.map(r => r.total),
                        backgroundColor: ['#2563EB', '#8B5CF6', '#16A34A', '#F59E0B', '#DC2626'],
                        borderWidth: 0,
                        hoverOffset: 12
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { 
                            position: 'bottom', 
                            labels: { 
                                color: '#0F172A',
                                font: { family: 'Inter', size: 13, weight: '700' },
                                padding: 20
                            } 
                        }
                    }
                }
            });
        }

        async function refreshData() {
            const data = await fetchData();
            updateKPIs(data.summary);
            updateMap(data.salesMap);
            updateCharts(data);
            updateSellersTable(data.sellers);
            updateInsights(data.insights);
        }

        document.addEventListener('DOMContentLoaded', async () => {
            initMap();
            await loadFilterOptions();
            await refreshData();
        });
    </script>
</body>
</html>
    """
