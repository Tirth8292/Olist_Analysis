"""
00. Data Setup: Loading and Initial Exploration
================================================
This is the first step in the analysis pipeline. It reads the already-joined
CSV extracts and builds a single item-level master dataset without performing
any additional SQL joins.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.data_utils import load_all_raw, save_processed

pd.set_option("display.max_columns", 80)
pd.set_option("display.width", 120)


def explore(dataframes: dict[str, pd.DataFrame]) -> None:
    for name, df in dataframes.items():
        print(f"--- EXPLORING '{name}' ---")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        nulls = df.isnull().sum()
        nulls = nulls[nulls > 0]
        if len(nulls):
            print(nulls.to_string())
        else:
            print("No missing values")
        print()


def build_master(dataframes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    transaction_data = dataframes["transaction_data"]
    delivery_data = dataframes["delivery_data"]
    product_review = dataframes["product_review"]
    customer_data = dataframes["customer_data"]

    item_df = transaction_data.drop_duplicates(
        subset=["order_id", "product_id", "order_item_id"], keep="first"
    ).copy()
    print(f"Base item-level table: {item_df.shape}")

    delivery_dedup = delivery_data.drop_duplicates(
        subset=["order_purchase_timestamp", "customer_unique_id", "seller_id"], keep="first"
    ).rename(columns={
        "customer_city": "delivery_customer_city",
        "customer_lat": "delivery_customer_lat",
        "customer_lng": "delivery_customer_lng",
    })
    df_master = item_df.merge(
        delivery_dedup,
        on=["order_purchase_timestamp", "customer_unique_id", "seller_id"],
        how="left",
    )
    print(f"After merging delivery_data: {df_master.shape}")

    review_dedup = product_review.drop_duplicates(subset=["order_id", "product_id"], keep="first")[
        [
            "order_id", "product_id", "review_id", "review_score", "review_comment_title",
            "review_comment_message", "review_creation_date", "review_answer_timestamp",
        ]
    ]
    df_master = df_master.merge(review_dedup, on=["order_id", "product_id"], how="left")
    print(f"After merging product_review: {df_master.shape}")

    customer_dedup = customer_data.drop_duplicates(subset="customer_unique_id", keep="first")[
        [
            "customer_unique_id", "customer_zip_code_prefix", "customer_city",
            "customer_state", "geolocation_lat", "geolocation_lng",
        ]
    ]
    df_master = df_master.merge(customer_dedup, on="customer_unique_id", how="left")
    print(f"After merging customer_data: {df_master.shape}")

    return df_master


def main() -> None:
    print("Loading the seven joined CSV extracts...\n")
    dataframes = load_all_raw()
    print(f"Loaded {len(dataframes)} dataframes: {list(dataframes.keys())}\n")

    explore(dataframes)

    print("Assembling the analytics-ready master table...\n")
    df_master = build_master(dataframes)

    print("\n--- Master DataFrame ---")
    print(f"Final shape: {df_master.shape}")
    print(df_master.head().to_string())

    save_processed(df_master, "main_data")

    sample_fraction = 0.05
    df_sample = df_master.sample(frac=sample_fraction, random_state=42)
    save_processed(df_sample, "sample_data")

    print(f"\nSaved main_data.parquet ({df_master.shape}) and sample_data.parquet ({df_sample.shape})")


if __name__ == "__main__":
    main()
