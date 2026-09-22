from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
JOIN_DIR = REPO_ROOT / "join operations"
RAW_DIR = JOIN_DIR
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

RAW_FILES = {
    "customer_data": "customer_data.csv",
    "customer_order": "customer_order.csv",
    "customer_payment": "customer_payment.csv",
    "delivery_data": "delivery_data.csv",
    "product_review": "porduct_review.csv",
    "transaction_static": "transacion_static_data.csv",
    "transaction_data": "transaction_data.csv",
}


def load_raw(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path}")
    return pd.read_csv(path)


def load_all_raw() -> dict[str, pd.DataFrame]:
    return {name: load_raw(fname) for name, fname in RAW_FILES.items()}


def save_processed(df: pd.DataFrame, name: str) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path


def load_processed(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Processed file not found: {path}")
    return pd.read_parquet(path)
