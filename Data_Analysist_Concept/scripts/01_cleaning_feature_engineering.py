"""
01. Data Cleaning and Feature Engineering
==========================================
Cleans the master table built in 00_setup_and_load.py and engineers the
derived features used in the rest of the workflow.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.cleaning import clean_data, missing_value_summary
from src.data_utils import load_processed, save_processed
from src.features import add_order_value, compute_delivery_total_time, compute_shipping_delay, compute_shipping_time

pd.set_option("display.max_columns", 100)


def main() -> None:
    df = load_processed("main_data")
    print(f"Loaded main_data: {df.shape}")

    print("\n--- Missing values BEFORE cleaning ---")
    print(missing_value_summary(df).to_string())

    df_clean = clean_data(df)
    print(f"\nShape after cleaning: {df_clean.shape}")

    print("\n--- Missing values AFTER cleaning ---")
    print(missing_value_summary(df_clean).to_string())

    df_featured = df_clean.copy()
    df_featured = add_order_value(df_featured)
    df_featured = compute_shipping_time(df_featured)
    df_featured = compute_delivery_total_time(df_featured)
    df_featured = compute_shipping_delay(df_featured)

    new_cols = ["order_value", "shipping_time_days", "total_delivery_time", "shipping_delay_days"]
    print("\n--- Sample of new features ---")
    print(df_featured[["order_id"] + new_cols].head(10).to_string())
    print("\n--- Summary stats of new features ---")
    print(df_featured[new_cols].describe().to_string())

    save_processed(df_featured, "analytics_main_data")
    print(f"\nSaved analytics_main_data.parquet ({df_featured.shape})")


if __name__ == "__main__":
    main()
