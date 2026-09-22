from __future__ import annotations

import pandas as pd


def add_order_value(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["order_value"] = df["price"].fillna(0) + df["freight_value"].fillna(0)
    return df


def compute_shipping_time(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    delta = df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    df["shipping_time_days"] = delta.dt.days
    return df


def compute_delivery_total_time(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    delta = df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]
    df["total_delivery_time"] = delta.dt.days
    return df


def compute_shipping_delay(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    delta = df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    df["shipping_delay_days"] = delta.dt.days
    return df
