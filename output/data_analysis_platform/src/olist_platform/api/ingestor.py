import csv
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..config import REPORTS_DIR
from ..db import connect
from ..transform import main as run_transform
from ..feature_engineering import main as run_features

app = FastAPI(title="Olist Data Entry Portal", version="1.0.0")

DATA_DIR = Path(r"E:\Downloads\myproject")
MAIN_API_URL = os.getenv("MAIN_API_URL", "http://127.0.0.1:8000")

DATASETS = {
    "customers": {
        "file": "olist_customers_dataset.csv",
        "fields": ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"]
    },
    "orders": {
        "file": "olist_orders_dataset.csv",
        "fields": ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
    },
    "order_items": {
        "file": "olist_order_items_dataset.csv",
        "fields": ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"]
    },
    "order_payments": {
        "file": "olist_order_payments_dataset.csv",
        "fields": ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"]
    },
    "order_reviews": {
        "file": "olist_order_reviews_dataset.csv",
        "fields": ["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message", "review_creation_date", "review_answer_timestamp"]
    },
    "products": {
        "file": "olist_products_dataset.csv",
        "fields": ["product_id", "product_category_name", "product_name_lenght", "product_description_lenght", "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    },
    "sellers": {
        "file": "olist_sellers_dataset.csv",
        "fields": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"]
    },
    "geolocation": {
        "file": "olist_geolocation_dataset.csv",
        "fields": ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city", "geolocation_state"]
    },
    "category_translation": {
        "file": "product_category_name_translation.csv",
        "fields": ["product_category_name", "product_category_name_english"]
    }
}

class RecordRequest(BaseModel):
    dataset: str
    data: Dict[str, str]

def append_to_csv(dataset_key: str, data: Dict[str, str]):
    meta = DATASETS[dataset_key]
    file_path = DATA_DIR / meta["file"]
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {meta['file']}")
    
    row = [data.get(field, "") for field in meta["fields"]]
    with open(file_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def insert_into_db(dataset_key: str, data: Dict[str, str]):
    table_map = {
        "customers": "raw_customers",
        "orders": "raw_orders",
        "order_items": "raw_order_items",
        "order_payments": "raw_order_payments",
        "order_reviews": "raw_order_reviews",
        "products": "raw_products",
        "sellers": "raw_sellers",
        "geolocation": "raw_geolocation",
        "category_translation": "raw_category_translation"
    }
    table_name = table_map.get(dataset_key)
    meta = DATASETS[dataset_key]
    fields = meta["fields"]
    
    columns_str = ", ".join([f'"{f}"' for f in fields])
    placeholders = ", ".join(["?" for _ in fields])
    sql = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
    
    values = [data.get(f) for f in fields]
    with connect() as conn:
        conn.execute(sql, values)
        conn.commit()

def trigger_main_api_reload():
    try:
        req = urllib.request.Request(f"{MAIN_API_URL}/reload-features", method="POST")
        with urllib.request.urlopen(req) as resp:
            pass
    except urllib.error.URLError:
        # The main API may not be running or reachable, ignore
        pass

@app.get("/", response_class=HTMLResponse)
def home():
    options_html = "".join([f'<option value="{k}">{k.replace("_", " ").title()}</option>' for k in DATASETS.keys()])
    js_datasets = str({k: v["fields"] for k, v in DATASETS.items()})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Olist Real-Time Ingestion Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0d12;
            --card-bg: #141822;
            --input-bg: #1b202e;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --border-color: #262f45;
            --success: #10b981;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}

        .container {{
            width: 100%;
            max-width: 650px;
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }}

        h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            margin-top: 0;
            text-align: center;
            background: linear-gradient(135deg, #fff 40%, var(--text-muted));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        p.subtitle {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-bottom: 30px;
        }}

        .form-group {{
            margin-bottom: 20px;
        }}

        label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 0.9rem;
        }}

        select, input {{
            width: 100%;
            padding: 12px 16px;
            border-radius: 10px;
            background-color: var(--input-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            font-family: inherit;
            box-sizing: border-box;
            transition: border-color 0.2s;
        }}

        select:focus, input:focus {{
            outline: none;
            border-color: var(--primary);
        }}

        #dynamic-fields {{
            background: rgba(0, 0, 0, 0.15);
            padding: 20px;
            border-radius: 12px;
            border: 1px dashed var(--border-color);
            margin-bottom: 25px;
        }}

        .field-row {{
            margin-bottom: 15px;
        }}

        .field-row:last-child {{
            margin-bottom: 0;
        }}

        button.btn {{
            width: 100%;
            background-color: var(--primary);
            color: white;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
        }}

        button.btn:hover {{
            background-color: var(--primary-hover);
        }}

        button.btn:active {{
            transform: scale(0.98);
        }}

        .toast {{
            display: none;
            margin-top: 20px;
            padding: 14px;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
        }}

        .toast-success {{
            background-color: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--success);
            color: var(--success);
        }}

        .toast-error {{
            background-color: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #ef4444;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Olist Real-Time Ingestor</h1>
        <p class="subtitle">Enter live entries and watch them propagate immediately to the main API</p>
        
        <div class="form-group">
            <label for="dataset-select">Select Type</label>
            <select id="dataset-select" onchange="buildForm()">
                {options_html}
            </select>
        </div>

        <form id="entry-form" onsubmit="submitForm(event)">
            <div id="dynamic-fields">
                <!-- Dynamic inputs -->
            </div>
            
            <button type="submit" class="btn">Inject Live Record</button>
        </form>

        <div id="toast" class="toast"></div>
    </div>

    <script>
        const schemas = {js_datasets};

        function buildForm() {{
            const select = document.getElementById("dataset-select");
            const fieldsContainer = document.getElementById("dynamic-fields");
            const datasetKey = select.value;
            const fields = schemas[datasetKey];

            fieldsContainer.innerHTML = "";
            fields.forEach(field => {{
                const row = document.createElement("div");
                row.className = "field-row";
                row.innerHTML = `
                    <label for="field-${{field}}">${{field.replace(/_/g, " ").toUpperCase()}}</label>
                    <input type="text" id="field-${{field}}" name="${{field}}" required>
                `;
                fieldsContainer.appendChild(row);
            }});
        }}

        async function submitForm(e) {{
            e.preventDefault();
            const select = document.getElementById("dataset-select");
            const datasetKey = select.value;
            const fields = schemas[datasetKey];
            
            const payload = {{
                dataset: datasetKey,
                data: {{}}
            }};

            fields.forEach(field => {{
                payload.data[field] = document.getElementById(`field-${{field}}`).value;
            }});

            const toast = document.getElementById("toast");
            toast.style.display = "none";

            try {{
                const res = await fetch("/add-record", {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json"
                    }},
                    body: JSON.stringify(payload)
                }});

                const data = await res.json();
                if (res.ok) {{
                    toast.className = "toast toast-success";
                    toast.innerText = "Success! Record appended to CSV, inserted in DB, rebuilt SQL tables/features, and refreshed Main API!";
                    toast.style.display = "block";
                    // Clear inputs
                    fields.forEach(field => {{
                        document.getElementById(`field-${{field}}`).value = "";
                    }});
                }} else {{
                    throw new Error(data.detail || "Error inserting record");
                }}
            }} catch(err) {{
                toast.className = "toast toast-error";
                toast.innerText = err.message;
                toast.style.display = "block";
            }}
        }}

        buildForm();
    </script>
</body>
</html>
"""

@app.post("/add-record")
def add_record(payload: RecordRequest):
    try:
        # 1. Append to local CSV
        append_to_csv(payload.dataset, payload.data)
        
        # 2. Insert into SQLite raw table
        insert_into_db(payload.dataset, payload.data)
        
        # 3. Rebuild Staging, Marts, and Views
        run_transform()
        
        # 4. Rebuild Features CSV Reports
        run_features()
        
        # 5. Clear Main API caches
        trigger_main_api_reload()
        
        return {"status": "success", "message": "Record integrated in real-time successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
