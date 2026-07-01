import csv
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


DATA_DIR = Path(r"E:\Downloads\myproject")

DATASETS = {
    "customers": {
        "file": "olist_customers_dataset.csv",
        "columns": [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    },
    "orders": {
        "file": "olist_orders_dataset.csv",
        "columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    "order_items": {
        "file": "olist_order_items_dataset.csv",
        "columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    },
    "order_payments": {
        "file": "olist_order_payments_dataset.csv",
        "columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    },
    "order_reviews": {
        "file": "olist_order_reviews_dataset.csv",
        "columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    },
    "products": {
        "file": "olist_products_dataset.csv",
        "columns": [
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    },
    "sellers": {
        "file": "olist_sellers_dataset.csv",
        "columns": [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ],
    },
    "geolocation": {
        "file": "olist_geolocation_dataset.csv",
        "columns": [
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ],
    },
    "category_translation": {
        "file": "product_category_name_translation.csv",
        "columns": [
            "product_category_name",
            "product_category_name_english",
        ],
    },
}


class NewRow(BaseModel):
    data: dict[str, Any] = Field(
        ...,
        examples=[
            {
                "seller_id": "new_seller_001",
                "seller_zip_code_prefix": "13023",
                "seller_city": "campinas",
                "seller_state": "SP",
            }
        ],
    )


app = FastAPI(
    title="Olist Owner Data Entry API",
    version="1.0.0",
    description="Append owner-entered rows into the original Olist CSV datasets.",
)


def dataset_path(dataset: str) -> Path:
    info = DATASETS.get(dataset)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset}")
    path = DATA_DIR / info["file"]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"CSV file not found: {path}")
    return path


def backup_file(path: Path) -> Path:
    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    return backup


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "data_dir": str(DATA_DIR)}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    rows = "".join(
        f"<tr><td>{name}</td><td>{info['file']}</td><td>{', '.join(info['columns'])}</td></tr>"
        for name, info in DATASETS.items()
    )
    return f"""
    <html>
      <head>
        <title>Olist Owner Data Entry</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.4; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #d0d7de; padding: 8px; vertical-align: top; }}
          th {{ background: #f6f8fa; text-align: left; }}
          code {{ background: #f6f8fa; padding: 2px 4px; }}
        </style>
      </head>
      <body>
        <h1>Olist Owner Data Entry</h1>
        <p>This local API appends new owner-entered rows into the original CSV files.</p>
        <p>Use <a href="/docs">/docs</a> to add rows safely.</p>
        <p>Writes require <code>confirm_write=true</code>.</p>
        <table>
          <tr><th>Dataset key</th><th>CSV file</th><th>Columns</th></tr>
          {rows}
        </table>
      </body>
    </html>
    """


@app.get("/owner/datasets")
def list_datasets() -> dict:
    return {
        name: {
            "csv_path": str(DATA_DIR / info["file"]),
            "columns": info["columns"],
        }
        for name, info in DATASETS.items()
    }


@app.get("/owner/datasets/{dataset}/sample")
def sample_rows(dataset: str, limit: int = Query(5, ge=1, le=50)) -> dict:
    path = dataset_path(dataset)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [row for _, row in zip(range(limit), reader)]
    return {"dataset": dataset, "csv_path": str(path), "rows": rows}


@app.post("/owner/datasets/{dataset}/rows")
def add_row(
    dataset: str,
    payload: NewRow,
    confirm_write: bool = Query(False, description="Must be true to append to the CSV file."),
) -> dict:
    info = DATASETS.get(dataset)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset}")
    columns = info["columns"]
    incoming = payload.data
    missing = [column for column in columns if column not in incoming]
    extra = [column for column in incoming if column not in columns]
    if missing:
        raise HTTPException(status_code=400, detail={"message": "Missing columns", "missing": missing})
    if extra:
        raise HTTPException(status_code=400, detail={"message": "Unknown columns", "extra": extra})
    if not confirm_write:
        return {
            "status": "preview_only",
            "message": "Row is valid. Run again with confirm_write=true to store it in the CSV.",
            "dataset": dataset,
            "row": {column: incoming[column] for column in columns},
        }

    path = dataset_path(dataset)
    backup = backup_file(path)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writerow({column: incoming[column] for column in columns})
    return {
        "status": "stored",
        "dataset": dataset,
        "csv_path": str(path),
        "backup_path": str(backup),
        "row": {column: incoming[column] for column in columns},
        "next_step": "Call POST /owner/rebuild-analytics to refresh the local warehouse and reports.",
    }


@app.post("/owner/rebuild-analytics")
def rebuild_analytics(confirm_rebuild: bool = Query(False)) -> dict:
    if not confirm_rebuild:
        return {
            "status": "preview_only",
            "message": "Run again with confirm_rebuild=true to reload CSVs and rebuild analytics outputs.",
        }
    project_root = Path(__file__).resolve().parents[2]
    commands = [
        ["python", "-m", "src.olist_platform.extract_load", "--data-dir", str(DATA_DIR)],
        ["python", "-m", "src.olist_platform.transform"],
        ["python", "-m", "src.olist_platform.run_quality_checks"],
        ["python", "-m", "src.olist_platform.feature_engineering"],
    ]
    outputs = []
    for command in commands:
        proc = subprocess.run(command, cwd=project_root, capture_output=True, text=True)
        outputs.append(
            {
                "command": " ".join(command),
                "return_code": proc.returncode,
                "stdout_tail": proc.stdout[-1000:],
                "stderr_tail": proc.stderr[-1000:],
            }
        )
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail={"message": "Rebuild failed", "outputs": outputs})
    return {"status": "rebuilt", "outputs": outputs}

