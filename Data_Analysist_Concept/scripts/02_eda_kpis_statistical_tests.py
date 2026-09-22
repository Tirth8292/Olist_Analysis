"""
02. Exploratory Data Analysis (EDA), KPIs & Statistical Testing
=================================================================
This script reads the processed table and creates the figures equivalent to
those generated in the original Olist notebook, using the already-joined
CSV extracts rather than raw SQL joins.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy.stats import kruskal

from src.data_utils import load_processed
from src.viz import plot_bar, plot_box, plot_bubble, plot_count, plot_heatmap, plot_line, plot_scatter, plot_stacked_bar

pd.set_option("display.max_columns", 100)


def section_1_customer_satisfaction(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("1. CUSTOMER SATISFACTION & SALES PERFORMANCE")
    print("=" * 80)

    plot_count(df, column="review_score", title="Review Score Distribution",
               xlabel="Review Score", save_path="review_score_distribution.png")
    total = df["review_score"].count()
    for x in range(2, 6):
        pct = (df["review_score"] >= x).sum() / total * 100
        print(f"  Reviews >= {x}: {pct:.2f}%")

    geo = df.groupby("customer_state")["order_id"].nunique().sort_values(ascending=False).head(15)
    print("\nTop 15 states by order count:")
    print(geo.to_string())
    plot_bar(x=geo.index, y=geo.values, title="Geographical Distribution of Orders by State",
             xlabel="State", ylabel="Number of Orders", save_path="geo_distribution_orders.png")

    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M")
    monthly = df.groupby("order_month")["order_id"].nunique().sort_index()
    plot_line(monthly, title="Monthly Sales", xlabel="Month", ylabel="Orders",
              save_path="orders_by_month.png")


def section_2_logistics(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("2. LOGISTICS PERFORMANCE & ITS IMPACT ON SATISFACTION")
    print("=" * 80)

    avg_time = df.groupby("review_score")["shipping_time_days"].mean()
    avg_delay = df.groupby("review_score")["shipping_delay_days"].mean()
    plot_bar(avg_time.index, avg_time.values, title="Average Shipping Time by Review Score",
             xlabel="Review Score", ylabel="Avg Shipping Time (days)",
             save_path="avg_shipping_time_by_review_score.png")
    plot_bar(avg_delay.index, avg_delay.values, title="Average Shipping Delay by Review Score",
             xlabel="Review Score", ylabel="Avg Shipping Delay (days)",
             save_path="avg_shipping_delay_by_review_score.png")

    perf = df.dropna(subset=["shipping_time_days", "shipping_delay_days", "review_score"]).copy()
    perf["Delayed"] = np.where(perf["shipping_delay_days"] > 0, "Yes", "No")
    plot_box(df=perf, x="review_score", y="shipping_time_days", hue="Delayed",
             title="Shipping Time & Review Score", xlabel="Review Score",
             ylabel="Shipping Time (days)", save_path="box_shipping_time_by_review_score.png")

    delay_counts = perf.groupby(["review_score", "Delayed"])["order_id"].count()
    delay_pct = delay_counts.groupby(level=0).apply(lambda x: 100 * x / x.sum()).unstack("Delayed").fillna(0)
    plot_stacked_bar(delay_pct, title="Proportion of Delayed Orders by Review Score",
                     xlabel="Review Score", ylabel="Percentage of Orders (%)",
                     save_path="delay_proportion_by_review_score.png")

    spe = df[["review_score", "shipping_time_days", "shipping_delay_days"]].dropna()
    corr = spe.corr(method="spearman")
    print("\nSpearman correlation (review_score vs shipping metrics):")
    print(corr.to_string())
    plot_heatmap(corr, title="Spearman Correlation: Delivery Performance vs. Satisfaction",
                 xlabel="Features", ylabel="Features", save_path="spearman_correlation_heatmap.png")

    kw_data = df.dropna(subset=["review_score", "shipping_time_days"])
    groups = [kw_data.loc[kw_data["review_score"] == s, "shipping_time_days"].values
              for s in range(1, 6) if s in kw_data["review_score"].unique()]
    stat, pvalue = kruskal(*groups)
    print(f"\nKruskal-Wallis H-test on shipping_time_days across review_score groups: H={stat:.2f}, p={pvalue:.4g}")


def section_3_products(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("3. PRODUCT-LEVEL ANALYSIS")
    print("=" * 80)

    cats = df["product_category_name_english"].dropna().value_counts()
    print("\nTop 15 categories by units sold:\n", cats.head(15).to_string())
    top15 = cats.sort_values(ascending=False).head(15)
    plot_bar(x=top15.values, y=top15.index, title="Top 15 Product Categories",
             xlabel="Units Sold", ylabel="Product Category", orientation="h",
             save_path="top_15_product_categories.png")

    prod_rev = df.groupby("product_category_name_english")["price"].sum().sort_values(ascending=False)
    plot_bar(x=prod_rev.head(15).values / 1_000_000, y=prod_rev.head(15).index,
             title="Top 15 Product Categories by Revenue", orientation="h",
             xlabel="Revenue (millions)", ylabel="Product Category",
             save_path="top_15_product_categories_revenue.png")

    category_performance = df.groupby("product_category_name_english").agg(
        total_revenue=("price", "sum"),
        average_score=("review_score", "mean"),
        units_sold=("product_category_name_english", "count"),
    ).drop("uncategorized", errors="ignore")
    threshold = category_performance["units_sold"].quantile(0.50)
    relevant = category_performance[category_performance["units_sold"] >= threshold]
    plot_bubble(
        data=relevant, x_col="average_score", y_col="total_revenue", size_col="units_sold",
        title="Product Category Performance: Revenue vs. Avg Review Score vs. Units Sold",
        xlabel="Average Review Score", ylabel="Total Revenue", top_n_labels=19,
        save_path="category_performance_bubble_plot.png",
    )


def section_4_payments(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("4. PAYMENT BEHAVIOUR")
    print("=" * 80)

    pay = df.dropna(subset=["payment_installments", "payment_value"]).copy()
    installment_dist = pay["payment_installments"].value_counts().sort_index()
    print("\nOrders by number of installments:\n", installment_dist.head(12).to_string())
    plot_bar(installment_dist.index, installment_dist.values,
             title="Orders by Number of Installments", xlabel="Installments",
             ylabel="Number of Orders", save_path="installments_distribution.png")

    plot_scatter(x=pay["payment_installments"], y=pay["payment_value"],
                 title="Payment Value vs. Number of Installments",
                 xlabel="Number of Installments", ylabel="Payment Value",
                 save_path="payment_value_vs_installments.png")

    corr = pay[["payment_installments", "payment_value"]].corr(method="spearman")
    print("\nSpearman correlation (installments vs payment value):")
    print(corr.to_string())


def main() -> None:
    df = load_processed("analytics_main_data")
    print(f"Loaded analytics_main_data: {df.shape}")

    section_1_customer_satisfaction(df)
    section_2_logistics(df)
    section_3_products(df)
    section_4_payments(df)

    print("\nAll figures saved to outputs/figures/.")


if __name__ == "__main__":
    main()
