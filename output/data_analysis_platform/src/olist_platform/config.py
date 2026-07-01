from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "olist.db"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_FILES = {
    "raw_customers": "olist_customers_dataset.csv",
    "raw_orders": "olist_orders_dataset.csv",
    "raw_order_items": "olist_order_items_dataset.csv",
    "raw_order_payments": "olist_order_payments_dataset.csv",
    "raw_order_reviews": "olist_order_reviews_dataset.csv",
    "raw_products": "olist_products_dataset.csv",
    "raw_sellers": "olist_sellers_dataset.csv",
    "raw_category_translation": "product_category_name_translation.csv",
    "raw_geolocation": "olist_geolocation_dataset.csv",
}

