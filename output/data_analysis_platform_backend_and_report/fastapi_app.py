"""Standalone FastAPI backend for the Olist CSV datasets.

Run from output/data_analysis_platform:
    python -m uvicorn fastapi_app:app --reload

Set OLIST_DATA_DIR when the CSVs live elsewhere. By default this points to
<project-root>/Data Set, matching this repository's layout.
"""

from __future__ import annotations

import csv
import os
import sqlite3
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("OLIST_DATA_DIR", PROJECT_ROOT / "Data Set"))
LIVE_ORDERS_PATH = Path(os.getenv("OLIST_LIVE_ORDERS_FILE", Path(__file__).with_name("live_orders.csv")))

DATASETS = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

TABLES = {
    "customers": "customers",
    "geolocation": "geolocation",
    "order_items": "order_items",
    "order_payments": "order_payments",
    "order_reviews": "order_reviews",
    "orders": "orders",
    "products": "products",
    "sellers": "sellers",
    "category_translation": "category_translation",
}

_database: sqlite3.Connection | None = None
_database_lock = RLock()


class LiveOrder(BaseModel):
    order_id: str
    customer_id: str
    order_status: str
    order_purchase_timestamp: str
    order_approved_at: str | None = None
    order_delivered_carrier_date: str | None = None
    order_delivered_customer_date: str | None = None
    order_estimated_delivery_date: str | None = None


class NewCustomer(BaseModel):
    customer_id: str
    customer_unique_id: str
    customer_zip_code_prefix: str
    customer_city: str
    customer_state: str


class NewOrderItem(BaseModel):
    product_id: str
    seller_id: str
    price: str
    freight_value: str
    shipping_limit_date: str | None = None
    order_item_id: str | None = None


class CompleteOrder(BaseModel):
    customer: NewCustomer
    order: LiveOrder
    items: list[NewOrderItem]


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _read_csv(path: Path) -> tuple[list[str], list[list[str | None]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader, [])
        rows = [[value or None for value in row] for row in reader]
    return columns, rows


def _append_order(order: LiveOrder) -> Path:
    path = DATA_DIR / DATASETS["orders"]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if order.order_id in (row.get("order_id") for row in reader):
            raise HTTPException(status_code=409, detail="An order with this order_id already exists")
    if LIVE_ORDERS_PATH.exists():
        _, live_rows = _read_csv(LIVE_ORDERS_PATH)
        if any(row and row[0] == order.order_id for row in live_rows):
            raise HTTPException(status_code=409, detail="An order with this order_id already exists")

    values = order.model_dump()
    try:
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writerow({column: values.get(column) or "" for column in columns})
        return path
    except PermissionError:
        LIVE_ORDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        live_exists = LIVE_ORDERS_PATH.exists() and LIVE_ORDERS_PATH.stat().st_size > 0
        with LIVE_ORDERS_PATH.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            if not live_exists:
                writer.writeheader()
            writer.writerow({column: values.get(column) or "" for column in columns})
        return LIVE_ORDERS_PATH



def _append_dataset_row(dataset: str, values: dict[str, Any]) -> Path:
    if dataset not in DATASETS:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset}")

    path = DATA_DIR / DATASETS[dataset]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []

    unknown_columns = sorted(set(values) - set(columns))
    if unknown_columns:
        raise HTTPException(
            status_code=422,
            detail={"unknown_columns": unknown_columns, "allowed_columns": columns},
        )
    if not values:
        raise HTTPException(status_code=422, detail="At least one column value is required")

    try:
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writerow({column: values.get(column) or "" for column in columns})
    except PermissionError as error:
        raise HTTPException(status_code=503, detail=f"Cannot write to {path}") from error
    return path


def _append_csv_rows(rows_by_dataset: dict[str, list[dict[str, Any]]]) -> list[Path]:
    handles: list[Any] = []
    original_sizes: dict[Path, int] = {}
    try:
        for dataset, rows in rows_by_dataset.items():
            path = DATA_DIR / DATASETS[dataset]
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                columns = csv.DictReader(handle).fieldnames or []
            original_sizes[path] = path.stat().st_size
            handle = path.open("a", encoding="utf-8", newline="")
            handles.append(handle)
            writer = csv.DictWriter(handle, fieldnames=columns)
            for row in rows:
                writer.writerow({column: row.get(column) or "" for column in columns})
        for handle in handles:
            handle.flush()
        return list(original_sizes)
    except (OSError, csv.Error) as error:
        for handle in handles:
            handle.close()
        for path, size in original_sizes.items():
            with path.open("r+b") as handle:
                handle.truncate(size)
        raise HTTPException(status_code=503, detail=f"Could not save complete order: {error}") from error
    finally:
        for handle in handles:
            if not handle.closed:
                handle.close()


def _rebuild_joined_outputs() -> None:
    builder = PROJECT_ROOT / "join operations" / "build_joined_csv.py"
    try:
        subprocess.run(
            [sys.executable, str(builder), "--project-root", str(PROJECT_ROOT)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise HTTPException(status_code=500, detail=f"Could not rebuild joined CSVs: {detail}") from error


def _load_database() -> sqlite3.Connection:
    missing = [filename for filename in DATASETS.values() if not (DATA_DIR / filename).exists()]
    if missing:
        raise RuntimeError(f"Missing CSV files in {DATA_DIR}: {', '.join(missing)}")

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row

    for dataset, filename in DATASETS.items():
        columns, rows = _read_csv(DATA_DIR / filename)
        if dataset == "orders" and LIVE_ORDERS_PATH.exists():
            live_columns, live_rows = _read_csv(LIVE_ORDERS_PATH)
            if live_columns != columns:
                raise RuntimeError("live_orders.csv columns do not match the orders dataset")
            rows.extend(live_rows)
        if not columns:
            raise RuntimeError(f"CSV has no header: {DATA_DIR / filename}")
        table = TABLES[dataset]
        column_sql = ", ".join(f"{_quote(column)} TEXT" for column in columns)
        connection.execute(f"CREATE TABLE {_quote(table)} ({column_sql})")
        placeholders = ", ".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO {_quote(table)} VALUES ({placeholders})",
            [row[: len(columns)] + [None] * max(0, len(columns) - len(row)) for row in rows],
        )

    connection.executescript(
        """
        CREATE INDEX idx_order_items_order_id ON order_items(order_id);
        CREATE INDEX idx_order_items_product_id ON order_items(product_id);
        CREATE INDEX idx_order_items_seller_id ON order_items(seller_id);
        CREATE INDEX idx_order_payments_order_id ON order_payments(order_id);
        CREATE INDEX idx_order_reviews_order_id ON order_reviews(order_id);
        CREATE INDEX idx_orders_customer_id ON orders(customer_id);
        CREATE INDEX idx_products_category ON products(product_category_name);
        """
    )
    connection.commit()
    return connection


def _get_database() -> sqlite3.Connection:
    global _database
    with _database_lock:
        if _database is None:
            _database = _load_database()
        return _database


def _reload_database() -> dict[str, Any]:
    global _database
    replacement = _load_database()
    with _database_lock:
        previous = _database
        _database = replacement
    if previous is not None:
        previous.close()
    return _dataset_status(replacement)


def _dataset_status(connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    connection = connection or _get_database()
    status = {}
    for dataset, table in TABLES.items():
        count = connection.execute(f"SELECT COUNT(*) FROM {_quote(table)}").fetchone()[0]
        status[dataset] = {"file": DATASETS[dataset], "rows": count}
    return status


def _rows(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    result = _get_database().execute(query, parameters or {}).fetchall()
    return [dict(row) for row in result]


def _paged_rows(
    query: str,
    parameters: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    parameters = parameters or {}
    count_query = f"SELECT COUNT(*) FROM ({query}) AS filtered_rows"
    connection = _get_database()
    total = connection.execute(count_query, parameters).fetchone()[0]
    offset = (page - 1) * page_size
    rows = _rows(
        f"{query} LIMIT :page_size OFFSET :offset",
        {**parameters, "page_size": page_size, "offset": offset},
    )
    return {
        "items": rows,
        "count": len(rows),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


def _report_rows(filename: str) -> list[dict[str, Any]]:
    path = Path(__file__).with_name("reports") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Report not found: {filename}")
    columns, rows = _read_csv(path)
    return [dict(zip(columns, row)) for row in rows]


@asynccontextmanager
async def lifespan(_: FastAPI):
    _get_database()
    yield
    global _database
    if _database is not None:
        _database.close()
        _database = None


app = FastAPI(
    title="Olist Marketplace Intelligence API",
    version="1.0.0",
    description="FastAPI backend backed directly by all nine Olist CSV datasets.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": app.title,
        "version": app.version,
        "docs": "/docs",
        "data_directory": str(DATA_DIR),
        "endpoints": [
            "/health",
            "/datasets",
            "/datasets/{dataset}",
            "/orders/new",
            "/orders/recent",
            "/orders/live",
            "/order/{order_id}",
            "/products/recent",
            "/product/{product_id}",
            "/sellers/leaderboard",
            "/sales/summary",
            "/reload",
        ],
    }


@app.get("/orders/new", response_class=HTMLResponse)
def new_order_form() -> str:
        return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Add Olist Order</title>
    <style>
        body { margin: 0; padding: 32px; background: #f4f7fb; color: #172033; font: 16px Arial, sans-serif; }
        main { max-width: 760px; margin: auto; background: white; padding: 28px; border-radius: 12px; box-shadow: 0 8px 30px #17203318; }
        h1 { margin-top: 0; } p { color: #596579; }
        form { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        label { display: grid; gap: 6px; font-weight: 600; }
        input, select { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #cbd4e1; border-radius: 6px; font: inherit; }
        .wide { grid-column: 1 / -1; } button { grid-column: 1 / -1; padding: 12px; border: 0; border-radius: 6px; background: #1769aa; color: white; font-weight: 700; cursor: pointer; }
        pre { white-space: pre-wrap; background: #f0f4f8; padding: 16px; border-radius: 6px; overflow: auto; }
        @media (max-width: 600px) { body { padding: 16px; } form { grid-template-columns: 1fr; } .wide { grid-column: auto; } }
    </style>
</head>
<body>
<main>
    <h1>Add a new order</h1>
    <p>Submit the order here. It will be saved to the orders CSV and appear in the latest five orders.</p>
    <form id="order-form">
        <label>Order ID<input name="order_id" required placeholder="new-order-001"></label>
        <label>Customer ID<input name="customer_id" required placeholder="customer-id"></label>
        <label>Status<select name="order_status"><option>created</option><option>approved</option><option>delivered</option><option>shipped</option><option>canceled</option></select></label>
        <label>Purchase timestamp<input name="order_purchase_timestamp" required type="datetime-local"></label>
        <label>Approved at<input name="order_approved_at" type="datetime-local"></label>
        <label>Estimated delivery<input name="order_estimated_delivery_date" type="datetime-local"></label>
        <label>Delivered to carrier<input name="order_delivered_carrier_date" type="datetime-local"></label>
        <label>Delivered to customer<input name="order_delivered_customer_date" type="datetime-local"></label>
        <button type="submit">Save order</button>
    </form>
    <pre id="result">Latest five orders will appear here.</pre>
</main>
<script>
const form = document.getElementById("order-form");
const result = document.getElementById("result");
form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    for (const key of Object.keys(data)) if (data[key] === "") data[key] = null;
    try {
        const response = await fetch("/orders/live", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Could not save order");
        result.textContent = JSON.stringify(body.latest_5_orders, null, 2);
        form.reset();
    } catch (error) { result.textContent = "Error: " + error.message; }
});
</script>
</body>
</html>"""


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        return {"status": "ok", "data_directory": str(DATA_DIR), "datasets": _dataset_status()}
    except (OSError, RuntimeError, sqlite3.Error) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/datasets")
def datasets() -> dict[str, Any]:
    return {"data_directory": str(DATA_DIR), "datasets": _dataset_status()}


@app.post("/datasets/{dataset}")
def add_dataset_row(dataset: str, values: dict[str, Any]) -> dict[str, Any]:
    """Append one row to a raw dataset, reload the API, and rebuild joined CSVs."""
    with _database_lock:
        stored_path = _append_dataset_row(dataset, values)
        try:
            dataset_status = _reload_database()
            _rebuild_joined_outputs()
        except (OSError, RuntimeError, sqlite3.Error) as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "status": "stored",
        "dataset": dataset,
        "stored_in": str(stored_path),
        "row": values,
        "datasets": dataset_status,
        "message": "Row appended to the original raw CSV and joined CSVs rebuilt",
    }


@app.get("/metadata/schema")
def metadata_schema() -> dict[str, Any]:
    schema = {}
    for dataset, filename in DATASETS.items():
        columns, _ = _read_csv(DATA_DIR / filename)
        schema[dataset] = {"file": filename, "columns": columns}
    return {"data_directory": str(DATA_DIR), "datasets": schema}


@app.get("/orders")
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    status: str | None = None,
    customer_id: str | None = None,
    purchased_from: str | None = None,
    purchased_to: str | None = None,
) -> dict[str, Any]:
    filters = ["1 = 1"]
    parameters: dict[str, Any] = {}
    if status:
        filters.append("o.order_status = :status")
        parameters["status"] = status
    if customer_id:
        filters.append("o.customer_id = :customer_id")
        parameters["customer_id"] = customer_id
    if purchased_from:
        filters.append("o.order_purchase_timestamp >= :purchased_from")
        parameters["purchased_from"] = purchased_from
    if purchased_to:
        filters.append("o.order_purchase_timestamp <= :purchased_to")
        parameters["purchased_to"] = purchased_to
    return _paged_rows(
        f"""
        SELECT o.*, c.customer_unique_id, c.customer_city, c.customer_state
        FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        WHERE {' AND '.join(filters)}
        ORDER BY datetime(o.order_purchase_timestamp) DESC
        """,
        parameters,
        page,
        page_size,
    )


@app.get("/customers")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    state: str | None = None,
    city: str | None = None,
) -> dict[str, Any]:
    filters = ["1 = 1"]
    parameters: dict[str, Any] = {}
    if state:
        filters.append("customer_state = :state")
        parameters["state"] = state
    if city:
        filters.append("customer_city = :city")
        parameters["city"] = city
    return _paged_rows(
        f"SELECT * FROM customers WHERE {' AND '.join(filters)} ORDER BY customer_id",
        parameters,
        page,
        page_size,
    )


@app.get("/customers/{customer_id}")
def customer_detail(customer_id: str) -> dict[str, Any]:
    customers = _rows("SELECT * FROM customers WHERE customer_id = :customer_id", {"customer_id": customer_id})
    if not customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    orders = _rows(
        "SELECT * FROM orders WHERE customer_id = :customer_id ORDER BY datetime(order_purchase_timestamp) DESC",
        {"customer_id": customer_id},
    )
    return {"customer": customers[0], "order_count": len(orders), "orders": orders}


@app.get("/products")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    category: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    filters = ["1 = 1"]
    parameters: dict[str, Any] = {}
    if category:
        filters.append("p.product_category_name = :category")
        parameters["category"] = category
    if search:
        filters.append("LOWER(COALESCE(t.product_category_name_english, p.product_category_name)) LIKE :search")
        parameters["search"] = f"%{search.lower()}%"
    return _paged_rows(
        f"""
        SELECT p.*, t.product_category_name_english
        FROM products p
        LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
        WHERE {' AND '.join(filters)}
        ORDER BY p.product_id
        """,
        parameters,
        page,
        page_size,
    )


@app.get("/sellers")
def list_sellers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    state: str | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    filter_sql = "1 = 1"
    if state:
        filter_sql = "seller_state = :state"
        parameters["state"] = state
    return _paged_rows(
        f"SELECT * FROM sellers WHERE {filter_sql} ORDER BY seller_id",
        parameters,
        page,
        page_size,
    )


@app.get("/payments")
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    payment_type: str | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    filter_sql = "1 = 1"
    if payment_type:
        filter_sql = "payment_type = :payment_type"
        parameters["payment_type"] = payment_type
    return _paged_rows(
        f"SELECT * FROM order_payments WHERE {filter_sql} ORDER BY order_id, payment_sequential",
        parameters,
        page,
        page_size,
    )


@app.get("/reviews")
def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    score: int | None = Query(None, ge=1, le=5),
) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    filter_sql = "1 = 1"
    if score is not None:
        filter_sql = "review_score = :score"
        parameters["score"] = score
    return _paged_rows(
        f"SELECT * FROM order_reviews WHERE {filter_sql} ORDER BY review_creation_date DESC",
        parameters,
        page,
        page_size,
    )


@app.get("/categories")
def list_categories() -> dict[str, Any]:
    return {"categories": _rows("SELECT * FROM category_translation ORDER BY product_category_name_english")}


@app.get("/geolocation")
def list_geolocation(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    zip_code: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    filters = ["1 = 1"]
    parameters: dict[str, Any] = {}
    if zip_code:
        filters.append("geolocation_zip_code_prefix = :zip_code")
        parameters["zip_code"] = zip_code
    if state:
        filters.append("geolocation_state = :state")
        parameters["state"] = state
    return _paged_rows(
        f"SELECT * FROM geolocation WHERE {' AND '.join(filters)} ORDER BY geolocation_zip_code_prefix",
        parameters,
        page,
        page_size,
    )


@app.get("/analytics/sales-summary")
def analytics_sales_summary() -> dict[str, Any]:
    return sales_summary()


@app.get("/analytics/revenue-by-period")
def revenue_by_period() -> dict[str, Any]:
    rows = _rows(
        """
        SELECT substr(o.order_purchase_timestamp, 1, 7) AS period,
               COUNT(DISTINCT o.order_id) AS orders,
               ROUND(COALESCE(SUM(CAST(i.price AS REAL) + CAST(i.freight_value AS REAL)), 0), 2) AS revenue
        FROM orders o
        LEFT JOIN order_items i ON i.order_id = o.order_id
        GROUP BY period
        ORDER BY period
        """
    )
    return {"count": len(rows), "items": rows}


@app.get("/analytics/revenue-by-category")
def revenue_by_category(limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
               COUNT(DISTINCT i.order_id) AS orders,
               COUNT(*) AS items,
               ROUND(SUM(CAST(i.price AS REAL) + CAST(i.freight_value AS REAL)), 2) AS revenue
        FROM order_items i
        LEFT JOIN products p ON p.product_id = i.product_id
        LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
        GROUP BY category
        ORDER BY revenue DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"count": len(rows), "items": rows}


@app.get("/analytics/delivery-performance")
def delivery_performance() -> dict[str, Any]:
    rows = _rows(
        """
        SELECT c.customer_state AS state,
               COUNT(*) AS delivered_orders,
               ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 2) AS average_delivery_days,
               ROUND(AVG(CASE WHEN julianday(o.order_delivered_customer_date) <= julianday(o.order_estimated_delivery_date) THEN 1.0 ELSE 0.0 END) * 100, 2) AS on_time_percent
        FROM orders o
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.order_status = 'delivered'
          AND o.order_delivered_customer_date IS NOT NULL
        GROUP BY c.customer_state
        ORDER BY on_time_percent DESC
        """
    )
    return {"count": len(rows), "items": rows}


@app.get("/analytics/repeat-customers")
def repeat_customers() -> dict[str, Any]:
    row = _get_database().execute(
        """
        SELECT COUNT(*) AS customers,
               COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
               ROUND(COALESCE(AVG(order_count), 0), 2) AS average_orders_per_customer
        FROM (
            SELECT customer_id, COUNT(*) AS order_count
            FROM orders
            GROUP BY customer_id
        )
        """
    ).fetchone()
    return dict(row)


@app.get("/analytics/reports/{report_name}")
def analytics_report(report_name: str) -> dict[str, Any]:
    allowed_reports = {
        "customer-rfm": "customer_rfm.csv",
        "cohort-retention": "cohort_retention.csv",
        "delivery-lanes": "delivery_lanes.csv",
        "seller-scores": "seller_scores.csv",
    }
    filename = allowed_reports.get(report_name)
    if filename is None:
        raise HTTPException(status_code=404, detail=f"Unknown report: {report_name}")
    rows = _report_rows(filename)
    return {"report": report_name, "count": len(rows), "items": rows}


@app.post("/reload")
def reload() -> dict[str, Any]:
    try:
        return {"status": "reloaded", "data_directory": str(DATA_DIR), "datasets": _reload_database()}
    except (OSError, RuntimeError, sqlite3.Error) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/orders/recent")
def recent_orders(limit: int = Query(5, ge=1, le=100)) -> dict[str, Any]:
    orders = _rows(
        """
        SELECT o.*, c.customer_city, c.customer_state
        FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        ORDER BY datetime(o.order_purchase_timestamp) DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"count": len(orders), "orders": orders}


@app.post("/orders/live")
def add_live_order(order: LiveOrder) -> dict[str, Any]:
    """Persist a new order in the source CSV and refresh the live dataset."""
    with _database_lock:
        try:
            stored_path = _append_order(order)
            dataset_status = _reload_database()
            _rebuild_joined_outputs()
        except HTTPException:
            raise
        except PermissionError as error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "The orders CSV and live fallback file cannot be written. "
                    f"Files: {DATA_DIR / DATASETS['orders']} and {LIVE_ORDERS_PATH}"
                ),
            ) from error
        except (OSError, RuntimeError, sqlite3.Error) as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "status": "stored",
        "message": "Order saved and loaded into the live API",
        "stored_in": str(stored_path),
        "order": order.model_dump(),
        "datasets": dataset_status,
        "latest_5_orders": recent_orders(5)["orders"],
    }


@app.post("/orders/complete")
def add_complete_order(payload: CompleteOrder) -> dict[str, Any]:
    """Save a new customer, order, and ordered products in one request."""
    if not payload.items:
        raise HTTPException(status_code=422, detail="At least one ordered product is required")
    if payload.order.customer_id != payload.customer.customer_id:
        raise HTTPException(status_code=422, detail="order.customer_id must match customer.customer_id")

    with _database_lock:
        database = _get_database()
        if _rows("SELECT 1 FROM customers WHERE customer_id = :id", {"id": payload.customer.customer_id}):
            raise HTTPException(status_code=409, detail="Customer already exists")
        if _rows("SELECT 1 FROM orders WHERE order_id = :id", {"id": payload.order.order_id}):
            raise HTTPException(status_code=409, detail="Order already exists")

        product_ids = [item.product_id for item in payload.items]
        seller_ids = [item.seller_id for item in payload.items]
        product_placeholders = ",".join(f":product_{index}" for index in range(len(product_ids)))
        seller_placeholders = ",".join(f":seller_{index}" for index in range(len(seller_ids)))
        product_parameters = {f"product_{index}": value for index, value in enumerate(product_ids)}
        seller_parameters = {f"seller_{index}": value for index, value in enumerate(seller_ids)}
        existing_products = {
            row["product_id"]
            for row in _get_database().execute(
                f"SELECT product_id FROM products WHERE product_id IN ({product_placeholders})",
                product_parameters,
            ).fetchall()
        }
        existing_sellers = {
            row["seller_id"]
            for row in _get_database().execute(
                f"SELECT seller_id FROM sellers WHERE seller_id IN ({seller_placeholders})",
                seller_parameters,
            ).fetchall()
        }
        missing_products = sorted(set(product_ids) - existing_products)
        missing_sellers = sorted(set(seller_ids) - existing_sellers)
        if missing_products or missing_sellers:
            raise HTTPException(
                status_code=422,
                detail={"missing_products": missing_products, "missing_sellers": missing_sellers},
            )

        customer_values = payload.customer.model_dump()
        order_values = payload.order.model_dump()
        item_values = []
        for index, item in enumerate(payload.items, start=1):
            values = item.model_dump()
            values["order_id"] = payload.order.order_id
            values["order_item_id"] = values["order_item_id"] or str(index)
            item_values.append(values)

        _append_csv_rows({"customers": [customer_values], "orders": [order_values], "order_items": item_values})
        try:
            dataset_status = _reload_database()
            _rebuild_joined_outputs()
        except (OSError, RuntimeError, sqlite3.Error) as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "status": "stored",
        "message": "Customer, order, and ordered products were saved",
        "stored_in": {
            "customer": str(DATA_DIR / DATASETS["customers"]),
            "order": str(DATA_DIR / DATASETS["orders"]),
            "items": str(DATA_DIR / DATASETS["order_items"]),
        },
        "customer": customer_values,
        "order": order_values,
        "items": item_values,
        "datasets": dataset_status,
    }


@app.get("/order/{order_id}")
def order_detail(order_id: str) -> dict[str, Any]:
    order = _rows(
        """
        SELECT o.*, c.customer_unique_id, c.customer_city, c.customer_state
        FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.order_id = :order_id
        """,
        {"order_id": order_id},
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order": order[0],
        "items": _rows("SELECT * FROM order_items WHERE order_id = :order_id ORDER BY order_item_id", {"order_id": order_id}),
        "payments": _rows("SELECT * FROM order_payments WHERE order_id = :order_id ORDER BY payment_sequential", {"order_id": order_id}),
        "reviews": _rows("SELECT * FROM order_reviews WHERE order_id = :order_id", {"order_id": order_id}),
    }


@app.get("/products/recent")
def recent_products(limit: int = Query(10, ge=1, le=100)) -> dict[str, Any]:
    products = _rows(
        """
        SELECT p.*, t.product_category_name_english
        FROM products p
        LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
        ORDER BY p.rowid DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"count": len(products), "products": products}


@app.get("/product/{product_id}")
def product_detail(product_id: str) -> dict[str, Any]:
    products = _rows(
        """
        SELECT p.*, t.product_category_name_english
        FROM products p
        LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
        WHERE p.product_id = :product_id
        """,
        {"product_id": product_id},
    )
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": products[0], "sellers": _rows(
        """
        SELECT DISTINCT s.*
        FROM sellers s
        JOIN order_items i ON i.seller_id = s.seller_id
        WHERE i.product_id = :product_id
        """,
        {"product_id": product_id},
    )}


@app.get("/sellers/leaderboard")
def sellers_leaderboard(limit: int = Query(10, ge=1, le=100)) -> dict[str, Any]:
    sellers = _rows(
        """
        SELECT s.seller_id, s.seller_city, s.seller_state,
               COUNT(DISTINCT i.order_id) AS orders,
               ROUND(SUM(CAST(i.price AS REAL) + CAST(i.freight_value AS REAL)), 2) AS gross_revenue,
               ROUND(AVG(CAST(r.review_score AS REAL)), 2) AS average_review_score
        FROM sellers s
        JOIN order_items i ON i.seller_id = s.seller_id
        LEFT JOIN order_reviews r ON r.order_id = i.order_id
        GROUP BY s.seller_id, s.seller_city, s.seller_state
        ORDER BY gross_revenue DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"count": len(sellers), "sellers": sellers}


@app.get("/sales/summary")
def sales_summary() -> dict[str, Any]:
    row = _get_database().execute(
        """
        SELECT COUNT(DISTINCT o.order_id) AS total_orders,
               COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END) AS delivered_orders,
               COUNT(DISTINCT i.product_id) AS products_sold,
               COUNT(DISTINCT i.seller_id) AS active_sellers,
               ROUND(COALESCE(SUM(CAST(i.price AS REAL) + CAST(i.freight_value AS REAL)), 0), 2) AS gross_revenue,
               ROUND(COALESCE(AVG(CAST(r.review_score AS REAL)), 0), 2) AS average_review_score
        FROM orders o
        LEFT JOIN order_items i ON i.order_id = o.order_id
        LEFT JOIN order_reviews r ON r.order_id = o.order_id
        """
    ).fetchone()
    return dict(row)
