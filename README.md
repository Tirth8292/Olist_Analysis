# Olist Marketplace Intelligence

An end-to-end analytics project for the Brazilian Olist marketplace dataset. It combines pre-joined CSV extracts, a six-step Python analysis pipeline, interactive dashboards, generated business visuals, and a CSV-backed FastAPI service.
![Olist dashboard preview](Dashboard/ZebraBI/Screenshot%202026-09-22%20204011.png)

## What this project includes
- **Joined-data analysis:** reads the existing files in `join operations/` directly. The analysis pipeline does not repeat the SQL join process.
- **Six Python analysis scripts:** setup, cleaning, feature engineering, EDA, RFM segmentation, forecasting, predictive modeling, and report generation.
- **Live dashboard:** filters and reloads the joined CSV data through a FastAPI service on port `8002`.
- **Marketplace API:** reads the nine raw Olist CSV datasets, exposes analytical endpoints, and supports live order entry on port `8000`.
- **Visual outputs:** charts for delivery, reviews, sales, payments, categories, customer segments, forecasting, and model performance.

## Open the project

These links work after starting the relevant local service:

| Experience | Link |
|---|---|
| Live joined-data dashboard | [http://127.0.0.1:8002](http://127.0.0.1:8002) when the dashboard service is running |
| Main FastAPI Swagger UI | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| FastAPI order-entry form | [http://127.0.0.1:8000/orders/new](http://127.0.0.1:8000/orders/new) |
| Dashboard visual assets | [Dashboard/](Dashboard/) |
## Architecture

```mermaid
flowchart LR
    A[Data Set\nRaw Olist CSVs] --> B[FastAPI\nPort 8000]
    C[join operations\nPre-joined CSV extracts] --> D[Six Python\nAnalysis Scripts]
    C --> E[Live Dashboard\nPort 8002]
    D --> F[Reports and PNGs]
    B --> G[Swagger UI]
    B -. optional live writes .-> A
```

The two data paths are intentional:

1. `Data Set/` contains the raw source files used by the FastAPI backend.
2. `join operations/` contains the already-joined extracts used by the analysis pipeline and live dashboard.

## Quick start

### 1. Create or activate the Python environment

PowerShell from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the backend requirements:

```powershell
pip install -r output/data_analysis_platform_backend_and_report/requirements.txt
```

The analysis scripts additionally use packages such as `matplotlib`, `seaborn`, `pyarrow`, `imbalanced-learn`, and `prophet`. Install them if they are not already present in the environment:

```powershell
pip install pandas numpy scipy scikit-learn matplotlib seaborn pyarrow imbalanced-learn prophet
```

### 2. Start the FastAPI backend

```powershell
Set-Location output/data_analysis_platform_backend_and_report
python -m uvicorn fastapi_app:app --host 127.0.0.1 --port 8000 --reload
```

Open the interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The backend loads the raw files from `Data Set/` by default. To use another directory:

```powershell
$env:OLIST_DATA_DIR = "C:\path\to\csv\folder"
python -m uvicorn fastapi_app:app --host 127.0.0.1 --port 8000 --reload
```

### 3. View the dashboard visuals

The repository includes dashboard-ready PNG assets in [Dashboard/](Dashboard/). The live dashboard link above points to the local dashboard service used with this project when it is running on port `8002`.

## FastAPI usage

The API is useful for dashboards, analysis clients, and live data entry. Important routes include:

| Area | Routes |
|---|---|
| Health and metadata | `/health`, `/`, `/datasets`, `/metadata/schema` |
| Orders | `/orders/recent`, `/orders/live`, `/orders/new`, `/order/{order_id}` |
| Catalog | `/products/recent`, `/product/{product_id}`, `/categories` |
| Marketplace entities | `/customers`, `/sellers/leaderboard`, `/payments`, `/reviews`, `/geolocation` |
| Analytics | `/sales/summary`, `/analytics/sales-summary`, `/analytics/revenue-by-period`, `/analytics/delivery-performance` |
| Reports | `/analytics/reports/customer-rfm`, `/analytics/reports/cohort-retention`, `/analytics/reports/delivery-lanes`, `/analytics/reports/seller-scores` |
| Refresh | `/reload` |

Example health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Example live order request:

```powershell
$body = @{
  order_id = "new-order-001"
  customer_id = "existing-customer-id"
  order_status = "created"
  order_purchase_timestamp = "2026-09-22 12:00:00"
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:8000/orders/live `
  -Method Post -ContentType "application/json" -Body $body
```

For a complete purchase containing a customer, order, and item records, use `POST /orders/complete` from Swagger. New records are written to the raw CSV source when possible; the fallback `live_orders.csv` file is used when the source directory is not writable.

## Six-file analysis pipeline

Run these scripts in order from the repository root:

```powershell
$python = ".\.venv\Scripts\python.exe"
$scripts = "Data_Analysist_Concept\olist_project\scripts"

& $python "$scripts\00_setup_and_load.py"
& $python "$scripts\01_cleaning_feature_engineering.py"
& $python "$scripts\02_eda_kpis_statistical_tests.py"
& $python "$scripts\03_customer_segmentation_rfm.py"
& $python "$scripts\04_modeling_forecasting.py"
& $python "$scripts\05_final_report.py"
```

| Script | Purpose |
|---|---|
| [00_setup_and_load.py](Data_Analysist_Concept/olist_project/scripts/00_setup_and_load.py) | Loads the seven joined CSV extracts and builds the analysis-ready table. |
| [01_cleaning_feature_engineering.py](Data_Analysist_Concept/olist_project/scripts/01_cleaning_feature_engineering.py) | Cleans types and creates order value, shipping time, delivery time, and delay features. |
| [02_eda_kpis_statistical_tests.py](Data_Analysist_Concept/olist_project/scripts/02_eda_kpis_statistical_tests.py) | Generates EDA charts, KPIs, correlations, and the Kruskal-Wallis test. |
| [03_customer_segmentation_rfm.py](Data_Analysist_Concept/olist_project/scripts/03_customer_segmentation_rfm.py) | Creates RFM segments and K-means customer clusters. |
| [04_modeling_forecasting.py](Data_Analysist_Concept/olist_project/scripts/04_modeling_forecasting.py) | Forecasts daily sales and predicts bad reviews with classification models. |
| [05_final_report.py](Data_Analysist_Concept/olist_project/scripts/05_final_report.py) | Creates the final Markdown report and checks referenced figures. |

Supporting reusable code is in [Data_Analysist_Concept/olist_project/src](Data_Analysist_Concept/olist_project/src). Processed parquet files are written to `Data_Analysist_Concept/olist_project/data/processed/`, and charts are written to `Data_Analysist_Concept/olist_project/outputs/figures/`.

## Visual gallery

### FastAPI interface

[![FastAPI Swagger screenshot](output/data_analysis_platform_backend_and_report/FastAPI.jpeg)](http://127.0.0.1:8000/docs)

Open the image directly: [FastAPI.jpeg](output/data_analysis_platform_backend_and_report/FastAPI.jpeg).

### Dashboard visuals

| Monthly growth dashboard | Revenue trend | Category value |
|---|---|---|
| ![Monthly growth dashboard](Dashboard/ZebraBI/Monthly%20Growth%20Dashboard.png) | ![Revenue line chart](Dashboard/ZebraBI/Revenue%20Line%20Chart.png) | ![Category value bar](Dashboard/ZebraBI/Category%20Value%20Bar.png) |

### Analysis outputs

| Delivery and reviews | Customer segmentation | Forecasting |
|---|---|---|
| ![Shipping time vs review score](Data_Analysist_Concept/scripts_outputs/figures/box_shipping_time_by_review_score.png) | ![Customer segment distribution](Data_Analysist_Concept/scripts_outputs/figures/customer_segments_distribution.png) | ![Prophet forecast](Data_Analysist_Concept/scripts_outputs/figures/prophet_forecast_vs_actual.png) |

More generated visuals are available in [Data_Analysist_Concept/olist_project/outputs/figures](Data_Analysist_Concept/scripts_outputs/figures), including product category performance, payment behavior, delivery delay, RFM clusters, ROC curves, and correlation heatmaps.

## Repository map

```text
Data Set/                                  Raw Olist CSV source files
join operations/                           Existing pre-joined analysis extracts    
Data_Analysist_Concept/scripts_outputs/
  scripts/                                 Six ordered analysis scripts
  src/                                     Reusable cleaning, feature, data, and chart helpers
  data/processed/                          Generated parquet datasets
  outputs/figures/                         Generated PNG charts
  outputs/reports/                         Generated Markdown reports
Dashboard/                                 Dashboard-ready PNG visuals
output/data_analysis_platform_backend.../  Main FastAPI backend on port 8000
```

## Key metrics

- **Order value:** item price plus freight value.
- **Shipping time:** days between purchase and customer delivery.
- **Shipping delay:** delivered date minus estimated delivery date.
- **RFM:** customer recency, purchase frequency, and monetary value.
- **Bad review:** review score less than or equal to 2.

## Troubleshooting

- **Port already in use:** start the service on another port, for example `--port 8003`, then open the matching URL.
- **Dashboard is unavailable:** confirm the separate dashboard service is running on port `8002` before opening the dashboard URL.
- **Missing parquet file:** run the analysis scripts in order, beginning with `00_setup_and_load.py`.
- **API cannot write to raw CSVs:** check file permissions; the backend can fall back to `output/data_analysis_platform_backend_and_report/live_orders.csv` for live order storage.
- **Changed CSV data:** use the dashboard reload action or call `POST http://127.0.0.1:8000/reload` for the main API.

## License and dataset note

This repository is an educational and portfolio analysis project. The Olist dataset is used for analysis and experimentation; review the dataset's original terms before redistributing the raw files.



