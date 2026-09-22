from __future__ import annotations

import pandas as pd

DATETIME_COLUMNS = [
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "review_creation_date",
    "review_answer_timestamp",
]
CRITICAL_KEY_COLUMNS = ["product_id", "seller_id"]
CATEGORY_FILL_COLUMNS = ["product_category_name_english"]
CATEGORY_PLACEHOLDER = "uncategorized"


def fix_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in DATETIME_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def drop_missing_keys(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    columns = columns or CRITICAL_KEY_COLUMNS
    present = [c for c in columns if c in df.columns]
    return df.dropna(subset=present)


def fill_categories(df: pd.DataFrame, columns: list[str] | None = None, placeholder: str = CATEGORY_PLACEHOLDER) -> pd.DataFrame:
    df = df.copy()
    columns = columns or CATEGORY_FILL_COLUMNS
    for col in columns:
        if col in df.columns:
            df[col] = df[col].fillna(placeholder)
    return df


def missing_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    missing_count = df.isnull().sum()
    missing_pct = (missing_count / len(df)) * 100
    summary = pd.DataFrame({"missing_count": missing_count, "missing_percentage": missing_pct})
    return summary[summary["missing_count"] > 0].sort_values("missing_percentage", ascending=False)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = fix_dtypes(df)
    df = drop_missing_keys(df)
    df = fill_categories(df)
    return df
