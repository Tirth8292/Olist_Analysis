"""
03. Customer Segmentation (RFM)
=================================
Calculates RFM and K-Means clusters without any additional joins.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.data_utils import load_processed
from src.viz import line_plot, plot_bar, plot_box, plot_heatmap

pd.set_option("display.max_columns", 100)


def build_rfm(df: pd.DataFrame) -> pd.DataFrame:
    client = df.groupby("customer_unique_id")
    last_purchase = client["order_purchase_timestamp"].max()
    snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    recency_days = (snapshot_date - last_purchase).dt.days
    frequency = client["order_id"].nunique()

    customer_payment = df.groupby("customer_unique_id")["payment_value"].sum().rename("Monetary")
    rfm = pd.DataFrame({"Recency": recency_days, "Frequency": frequency})
    rfm["Monetary"] = rfm.index.map(customer_payment).astype(float).fillna(0.0)
    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    rfm = rfm.copy()
    rfm["R_score"] = pd.qcut(rfm["Recency"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)

    eps = 0.1
    freq_max = rfm["Frequency"].max() + eps
    freq_bins = [0, 1.0, 2.0, freq_max]
    rfm["F_score"] = pd.cut(rfm["Frequency"], bins=freq_bins, labels=[1, 2, 3], right=True, include_lowest=True).astype(int)

    m_labels = pd.qcut(rfm["Monetary"], q=5, duplicates="drop", labels=False)
    rfm["M_score"] = (m_labels + 1).astype(int)
    rfm["RFM_Score"] = rfm["R_score"].astype(str) + rfm["F_score"].astype(str) + rfm["M_score"].astype(str)
    return rfm


def segment(row) -> str:
    r, f = int(row["R_score"]), int(row["F_score"])
    if r >= 4 and f == 3:
        return "Champions"
    elif r >= 4 and f >= 2:
        return "Potential Loyalists"
    elif r >= 3 and f <= 2:
        return "Need Attention"
    elif r <= 2 and f == 3:
        return "At Risk"
    elif r <= 2 and f == 1:
        return "Hibernating/Lost"
    return "Others"


def run_rfm_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("1. RFM CUSTOMER SEGMENTATION")
    print("=" * 80)

    rfm = build_rfm(df)
    print(f"\nRFM table for {len(rfm):,} unique customers.")
    print(rfm.describe().to_string())

    rfm = score_rfm(rfm)
    rfm["Segment"] = rfm.apply(segment, axis=1)

    seg_counts = rfm.groupby("Segment").size().sort_values(ascending=False)
    print("\nSegment sizes:")
    print(seg_counts.to_string())

    plot_bar(seg_counts.index, seg_counts.values / seg_counts.sum(),
             title="Customer Segments Distribution", xlabel="Segment", ylabel="Percent",
             save_path="customer_segments_distribution.png")

    seg_means = rfm.groupby("Segment")[["Recency", "Frequency", "Monetary"]].mean()
    seg_medians = rfm.groupby("Segment")[["Recency", "Frequency", "Monetary"]].median()

    plot_bar(seg_means.index, seg_means["Recency"].sort_values(),
             title="Average Recency by Segment", xlabel="Segment", ylabel="Avg Recency (days)",
             save_path="average_recency_by_segment.png")
    plot_bar(seg_medians.index, seg_medians["Monetary"],
             title="Median Monetary by Segment", xlabel="Segment", ylabel="Median Monetary (R$)",
             save_path="median_monetary_by_segment.png")

    return rfm


def run_kmeans(rfm: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("2. AUTOMATED SEGMENTATION WITH K-MEANS")
    print("=" * 80)

    features = rfm[["Recency", "Frequency", "Monetary"]].copy()
    scaler = StandardScaler()
    scaled = pd.DataFrame(scaler.fit_transform(features), columns=features.columns, index=features.index)

    inertias = []
    for k in range(1, 11):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(scaled)
        inertias.append(km.inertia_)
    line_plot(list(range(1, 11)), inertias, title="Elbow Method for Optimal k",
              xlabel="Number of clusters (k)", ylabel="Inertia", save_path="elbow_method_kmeans.png")

    k_final = 3
    kmeans_final = KMeans(n_clusters=k_final, random_state=42, n_init=10).fit(scaled)
    rfm_k = rfm.copy()
    rfm_k["Cluster"] = kmeans_final.labels_

    cluster_profile = rfm_k.groupby("Cluster").agg(
        Recency_avg=("Recency", "mean"), Frequency_avg=("Frequency", "mean"),
        Monetary_avg=("Monetary", "mean"), Count=("Cluster", "size"),
    ).sort_values("Recency_avg", ascending=False)
    print("\nCluster profiles (mean):\n", cluster_profile.to_string())

    ordered_by_recency = cluster_profile.sort_values("Recency_avg", ascending=False).index.tolist()
    freq_rank = cluster_profile.sort_values("Frequency_avg", ascending=False).index.tolist()
    loyal_cluster = freq_rank[0]
    remaining = [c for c in ordered_by_recency if c != loyal_cluster]
    name_map = {loyal_cluster: "Group C: Loyals (Multiple Freq)"}
    if remaining:
        name_map[remaining[0]] = "Group A: Inactives (Freq 1)"
    if len(remaining) > 1:
        name_map[remaining[1]] = "Group B: Recents (Freq 1)"
    rfm_k["Cluster_Name"] = rfm_k["Cluster"].map(name_map)

    rfm_k["Frequency_log"] = np.log1p(rfm_k["Frequency"])
    rfm_k["Monetary_log"] = np.log1p(rfm_k["Monetary"])
    plot_box(rfm_k, x="Cluster_Name", y="Recency", title="Recency by Cluster",
             xlabel="Cluster", ylabel="Recency (days)", save_path="boxplot_recency_by_cluster.png")
    plot_box(rfm_k, x="Cluster_Name", y="Frequency_log", title="Frequency by Cluster (log)",
             xlabel="Cluster", ylabel="log(1+Frequency)", save_path="boxplot_frequency_by_cluster.png")
    plot_box(rfm_k, x="Cluster_Name", y="Monetary_log", title="Monetary by Cluster (log)",
             xlabel="Cluster", ylabel="log(1+Monetary)", save_path="boxplot_monetary_by_cluster.png")

    comparison = pd.crosstab(rfm_k["Segment"], rfm_k["Cluster_Name"])
    print("\nManual segments vs. K-Means clusters:\n", comparison.to_string())
    plot_heatmap(comparison, title="Comparison: Manual Segments vs. K-Means Clusters",
                 xlabel="K-Means Cluster", ylabel="RFM Segment",
                 save_path="heatmap_comparison_segments.png")

    return rfm_k


def main() -> None:
    df = load_processed("analytics_main_data")
    print(f"Loaded analytics_main_data: {df.shape}")

    rfm = run_rfm_segmentation(df)
    rfm_final = run_kmeans(rfm)

    from src.data_utils import save_processed
    save_processed(rfm_final.reset_index(), "rfm_segments")
    print(f"\nSaved rfm_segments.parquet ({rfm_final.shape})")


if __name__ == "__main__":
    main()
