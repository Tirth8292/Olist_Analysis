import csv
import math
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..config import REPORTS_DIR
from ..db import connect

app = FastAPI(
    title="Olist Marketplace Intelligence API",
    version="1.0.0",
    swagger_ui_parameters={"syntaxHighlight.theme": "github", "tryItOutEnabled": True},
    docs_url="/docs",
    redoc_url="/redoc"
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Remove 422 validation errors from paths
    for path in openapi_schema.get("paths", {}).values():
        for method in path.values():
            if "responses" in method and "422" in method["responses"]:
                del method["responses"]["422"]
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi


@app.post("/reload-features")
def reload_features():
    seller_scores.cache_clear()
    delivery_lanes.cache_clear()
    return {"status": "success", "message": "API caches cleared"}


@app.get("/orders/recent")
def get_recent_orders(limit: int = Query(10, ge=1, le=100)) -> dict:
    with connect() as conn:
        rows = conn.execute(
            "select * from fct_orders order by order_purchase_timestamp desc limit :limit",
            {"limit": limit}
        ).fetchall()
    return {
        "count": len(rows),
        "orders": [dict(row) for row in rows]
    }


@app.get("/order/{order_id}")
def get_order_detail(order_id: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "select * from fct_orders where order_id = :order_id",
            {"order_id": order_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(row)


@app.get("/products/recent")
def get_recent_products(limit: int = Query(10, ge=1, le=100)) -> dict:
    with connect() as conn:
        rows = conn.execute(
            "select * from dim_products order by rowid desc limit :limit",
            {"limit": limit}
        ).fetchall()
    return {
        "count": len(rows),
        "products": [dict(row) for row in rows]
    }


@app.get("/product/{product_id}")
def get_product_detail(product_id: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "select * from dim_products where product_id = :product_id",
            {"product_id": product_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(row)


@app.get("/sellers/recent")
def get_recent_sellers(limit: int = Query(10, ge=1, le=100)) -> dict:
    with connect() as conn:
        rows = conn.execute(
            "select * from dim_sellers order by rowid desc limit :limit",
            {"limit": limit}
        ).fetchall()
    return {
        "count": len(rows),
        "sellers": [dict(row) for row in rows]
    }


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Olist Marketplace Intelligence API Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0d0f14;
            --card-bg: #161a23;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --accent: #a855f7;
            --success: #10b981;
            --border-color: #242c3d;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .background-glow {
            position: absolute;
            top: -150px;
            left: 50%;
            transform: translateX(-50%);
            width: 600px;
            height: 300px;
            background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
            z-index: -1;
            filter: blur(80px);
            pointer-events: none;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            flex-grow: 1;
        }

        header {
            text-align: center;
            margin-bottom: 50px;
        }

        h1 {
            font-size: 2.8rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #fff 30%, var(--text-muted) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .badge-container {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-top: 15px;
        }

        .badge {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 99px;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .badge-status {
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--success);
        }

        .doc-buttons {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 30px;
        }

        .btn {
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white;
            border: none;
            padding: 12px 28px;
            border-radius: 12px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
        }

        .btn-secondary {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            box-shadow: none;
        }

        .btn-secondary:hover {
            background: #1e2433;
            border-color: #3b4760;
            transform: translateY(-2px);
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
            margin-top: 40px;
        }

        @media (min-width: 768px) {
            .grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .card:hover {
            transform: translateY(-4px);
            border-color: #3b4760;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .method {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 6px;
            text-transform: uppercase;
        }

        .method-get {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--success);
        }

        .method-post {
            background-color: rgba(99, 102, 241, 0.1);
            color: var(--primary);
        }

        .path {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            font-weight: 600;
            color: #fff;
        }

        .card-desc {
            font-size: 0.9rem;
            color: var(--text-muted);
            line-height: 1.5;
            margin-bottom: 16px;
        }

        .code-block {
            background-color: #080a0e;
            border-radius: 8px;
            padding: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            overflow-x: auto;
            border: 1px solid #141922;
        }
    </style>
</head>
<body>
    <div class="background-glow"></div>
    <div class="container">
        <header>
            <h1>Olist Intelligence API Portal</h1>
            <div class="badge-container">
                <div class="badge">
                    <span class="badge-status"></span>
                    Online
                </div>
                <div class="badge">
                    v1.0.0
                </div>
            </div>
            <div class="doc-buttons">
                <a href="/docs" class="btn">
                    Interactive Swagger UI
                </a>
                <a href="/redoc" class="btn btn-secondary">
                    ReDoc Alternative
                </a>
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <span class="path">/health</span>
                    <span class="method method-get">GET</span>
                </div>
                <div class="card-desc">Check the API service health status and check verified data directories.</div>
                <div class="code-block">curl http://localhost:8000/health</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="path">/sellers/leaderboard</span>
                    <span class="method method-get">GET</span>
                </div>
                <div class="card-desc">Rank and retrieve best/worst performing sellers on the marketplace.</div>
                <div class="code-block">curl "http://localhost:8000/sellers/leaderboard?limit=5"</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="path">/seller/{seller_id}</span>
                    <span class="method method-get">GET</span>
                </div>
                <div class="card-desc">Retrieve performance metrics, ranking, and details for a specific seller.</div>
                <div class="code-block">curl http://localhost:8000/seller/&lt;seller_id&gt;</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="path">/orders/repeat-by-city</span>
                    <span class="method method-get">GET</span>
                </div>
                <div class="card-desc">Analyze categories repeatedly purchased by customers grouped by city.</div>
                <div class="code-block">curl "http://localhost:8000/orders/repeat-by-city?city=sao+paulo"</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="path">/delivery/estimate</span>
                    <span class="method method-get">GET</span>
                </div>
                <div class="card-desc">Estimate delivery duration based on historical transit data.</div>
                <div class="code-block">curl "http://localhost:8000/delivery/estimate?origin_zip=13023&destination_zip=14409"</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="path">/seller/score</span>
                    <span class="method method-post">POST</span>
                </div>
                <div class="card-desc">Scores a specific seller ID, returning risk tier and recommendations.</div>
                <div class="code-block">curl -X POST -H "Content-Type: application/json" -d '{"seller_id":"&lt;id&gt;"}' http://localhost:8000/seller/score</div>
            </div>
        </div>
    </div>
    <footer style="text-align: center; padding: 30px; color: var(--text-muted); font-size: 0.85rem; border-top: 1px solid var(--border-color); margin-top: 50px;">
        Olist Marketplace Analytics Engineering Platform
    </footer>
</body>
</html>"""



class SellerScoreRequest(BaseModel):
    seller_id: str


def number_value(row: dict, key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in (None, ""):
        return default
    return float(value)


def seller_response(row: dict, rank: int | None = None) -> dict:
    response = {
        "seller_id": row["seller_id"],
        "seller_city": row["seller_city"],
        "seller_state": row["seller_state"],
        "orders": int(number_value(row, "orders")),
        "gmv": number_value(row, "gmv"),
        "performance_score": number_value(row, "performance_score"),
        "risk_tier": row["risk_tier"],
        "score_breakdown": {
            "on_time_delivery_rate_40_percent": number_value(row, "on_time_delivery_rate"),
            "average_review_score_30_percent": number_value(row, "avg_review_score"),
            "order_cancellation_rate_20_percent": number_value(row, "cancellation_rate"),
            "average_order_value_growth_10_percent": number_value(row, "revenue_growth_rate"),
        },
        "recommendation": recommendation_for(row["risk_tier"]),
    }
    if rank is not None:
        response["rank"] = rank
    return response


@lru_cache
def seller_scores() -> dict[str, dict]:
    path = REPORTS_DIR / "seller_scores.csv"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["seller_id"]: row for row in csv.DictReader(handle)}


@lru_cache
def delivery_lanes() -> dict[tuple[str, str], dict]:
    path = REPORTS_DIR / "delivery_lanes.csv"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {(row["origin_zip"], row["destination_zip"]): row for row in csv.DictReader(handle)}


def recommendation_for(tier: str) -> str:
    if tier == "high_risk":
        return "Audit fulfillment process, shipping promise, and product quality before increasing seller exposure."
    if tier == "watchlist":
        return "Monitor late deliveries and review trend weekly; offer operational coaching."
    return "Seller is healthy; consider higher marketplace visibility."


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "reports_dir": str(Path(REPORTS_DIR))}


@app.post("/seller/score")
def score_seller(payload: SellerScoreRequest) -> dict:
    row = seller_scores().get(payload.seller_id)
    if row is None:
        raise HTTPException(status_code=404, detail="seller_id not found. Run feature_engineering first.")
    return seller_response(row)


@app.get("/sellers/leaderboard")
def sellers_leaderboard(
    limit: int = Query(10, ge=1, le=5000),
    sort: str = Query("best", pattern="^(best|worst)$"),
    min_orders: int = Query(1, ge=1),
) -> dict:
    sellers = [
        row
        for row in seller_scores().values()
        if int(number_value(row, "orders")) >= min_orders
    ]
    sellers.sort(
        key=lambda row: number_value(row, "performance_score"),
        reverse=(sort == "best"),
    )
    return {
        "metric_formula": {
            "on_time_delivery_rate": "40%",
            "average_review_score": "30%",
            "order_cancellation_rate": "20%",
            "average_order_value_growth": "10%",
        },
        "sort": sort,
        "min_orders": min_orders,
        "total_matching_sellers": len(sellers),
        "count_returned": min(limit, len(sellers)),
        "sellers": [
            seller_response(row, rank=index + 1)
            for index, row in enumerate(sellers[:limit])
        ],
    }


@app.get("/seller/{seller_id}")
def seller_detail(seller_id: str) -> dict:
    row = seller_scores().get(seller_id)
    if row is None:
        raise HTTPException(status_code=404, detail="seller_id not found.")
    ranked = sorted(
        seller_scores().values(),
        key=lambda item: number_value(item, "performance_score"),
        reverse=True,
    )
    rank = next(
        (index + 1 for index, item in enumerate(ranked) if item["seller_id"] == seller_id),
        None,
    )
    return seller_response(row, rank=rank)


@app.get("/orders/repeat-by-city")
def repeat_orders_by_city(
    city: str | None = Query(None, description="Optional customer city filter, for example: sao paulo"),
    limit: int = Query(20, ge=1, le=500),
    min_repeat_orders: int = Query(2, ge=2),
) -> dict:
    sql = """
    with customer_category_orders as (
      select
        c.customer_city,
        coalesce(p.product_category_name_english, 'unknown') as order_type,
        o.customer_unique_id,
        count(distinct o.order_id) as order_count,
        sum(i.item_gmv) as gmv
      from fct_orders o
      join dim_customers c on o.customer_id = c.customer_id
      join fct_order_items i on o.order_id = i.order_id
      left join dim_products p on i.product_id = p.product_id
      where o.order_status = 'delivered'
        and (:city is null or c.customer_city = lower(:city))
      group by 1, 2, 3
      having count(distinct o.order_id) >= :min_repeat_orders
    )
    select
      customer_city,
      order_type,
      count(distinct customer_unique_id) as repeat_customers,
      sum(order_count) as repeat_orders,
      round(sum(gmv), 2) as gmv,
      round(avg(order_count), 2) as avg_repeat_orders_per_customer
    from customer_category_orders
    group by 1, 2
    order by repeat_orders desc, repeat_customers desc, gmv desc
    limit :limit
    """
    with connect() as conn:
        rows = conn.execute(
            sql,
            {"city": city, "limit": limit, "min_repeat_orders": min_repeat_orders},
        ).fetchall()
    return {
        "description": "Product categories repeatedly ordered by customers in each city.",
        "city_filter": city,
        "min_repeat_orders_per_customer": min_repeat_orders,
        "count_returned": len(rows),
        "order_book": [
            {
                "customer_city": row["customer_city"],
                "order_type": row["order_type"],
                "repeat_customers": row["repeat_customers"],
                "repeat_orders": row["repeat_orders"],
                "gmv": row["gmv"],
                "avg_repeat_orders_per_customer": row["avg_repeat_orders_per_customer"],
            }
            for row in rows
        ],
    }


@app.get("/delivery/estimate")
def delivery_estimate(
    origin_zip: str = Query(..., min_length=1),
    destination_zip: str = Query(..., min_length=1),
) -> dict:
    lane = delivery_lanes().get((origin_zip, destination_zip))
    if lane:
        return {
            "origin_zip": origin_zip,
            "destination_zip": destination_zip,
            "estimated_delivery_days": math.ceil(float(lane["avg_delivery_days"])),
            "late_delivery_rate": float(lane["late_delivery_rate"]),
            "historical_orders": int(lane["orders"]),
            "method": "exact historical lane",
        }
    raise HTTPException(status_code=404, detail="No historical lane found for this origin/destination pair.")
