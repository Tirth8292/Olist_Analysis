"""
04. Time Series Forecasting & Predictive Modeling
====================================================
Uses the already-joined dataset to model daily sales and predict bad reviews.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import pandas as pd
from imblearn.under_sampling import RandomUnderSampler
from prophet import Prophet
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import RocCurveDisplay, accuracy_score, classification_report, confusion_matrix, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data_utils import FIGURES_DIR, load_processed

pd.set_option("display.max_columns", 100)


def forecast_sales(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("1. TIME SERIES FORECASTING: TOTAL SALES")
    print("=" * 80)

    daily = df[["order_id", "order_purchase_timestamp", "order_value"]].drop_duplicates(subset=["order_id"])
    daily = daily.set_index("order_purchase_timestamp")["order_value"].resample("D").sum().reset_index()
    daily = daily.rename(columns={"order_purchase_timestamp": "ds", "order_value": "y"})

    plt.figure(figsize=(12, 6))
    plt.plot(daily["ds"], daily["y"])
    plt.title("Total Daily Sales Revenue")
    plt.xlabel("Date")
    plt.ylabel("Total Sales (R$)")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "daily_sales_timeseries.png", dpi=150)
    plt.close()

    black_fridays = pd.DataFrame({
        "holiday": "black_friday",
        "ds": pd.to_datetime(["2016-11-25", "2017-11-24"]),
        "lower_window": 0, "upper_window": 1,
    })

    initial_cutoff = "2018-07-31"
    daily_clean = daily[daily["ds"] <= initial_cutoff].copy()
    cutoff_date = daily_clean["ds"].max() - pd.Timedelta(days=90)
    train = daily_clean[daily_clean["ds"] <= cutoff_date]
    test = daily_clean[daily_clean["ds"] > cutoff_date]

    model = Prophet(holidays=black_fridays, daily_seasonality=False, yearly_seasonality=True, weekly_seasonality=True)
    model.fit(train)

    forecast = model.predict(test[["ds"]])
    comparison = pd.merge(test.rename(columns={"y": "y_true"}), forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]], on="ds")
    mae = mean_absolute_error(comparison["y_true"], comparison["yhat"])
    mae_pct = mae / comparison["y_true"].mean() * 100
    print(f"Prophet MAE on test set: R$ {mae:.2f} ({mae_pct:.2f}% of mean daily sales)")

    plt.figure(figsize=(12, 6))
    plt.plot(comparison["ds"], comparison["y_true"], label="Actual", color="black")
    plt.plot(comparison["ds"], comparison["yhat"], label="Forecast", color="blue")
    plt.fill_between(comparison["ds"], comparison["yhat_lower"], comparison["yhat_upper"], color="blue", alpha=0.2)
    plt.title("Prophet Forecast vs Actual Sales (Test Set)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "prophet_forecast_vs_actual.png", dpi=150)
    plt.close()

    full_period = pd.concat([train.tail(7), test])
    naive_pred = full_period["y"].shift(7).iloc[7:]
    mae_naive = mean_absolute_error(test["y"], naive_pred)
    mae_naive_pct = mae_naive / test["y"].mean() * 100
    print(f"Naive (t-7) baseline MAE: R$ {mae_naive:.2f} ({mae_naive_pct:.2f}%)")


def predict_bad_reviews(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("2. PREDICTIVE MODELING: PREDICTING BAD REVIEWS")
    print("=" * 80)

    numerical_features = ["shipping_time_days", "shipping_delay_days", "price", "freight_value"]
    categorical_features = ["product_category_name_english", "customer_state"]

    model_df = df[numerical_features + categorical_features + ["review_score"]].copy().dropna()
    model_df["is_bad_review"] = (model_df["review_score"] <= 2).astype(int)
    model_df = model_df.drop(columns=["review_score"])

    X = model_df.drop(columns=["is_bad_review"])
    y = model_df["is_bad_review"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    preprocessor = ColumnTransformer(transformers=[
        ("num", StandardScaler(), numerical_features),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
    ])
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc = preprocessor.transform(X_test)

    rus = RandomUnderSampler(random_state=42)
    X_train_res, y_train_res = rus.fit_resample(X_train_proc, y_train)

    for name, model in [
        ("Logistic Regression", LogisticRegression(random_state=42, max_iter=1000)),
        ("Random Forest", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1, class_weight="balanced")),
    ]:
        model.fit(X_train_res, y_train_res)
        y_pred = model.predict(X_test_proc)
        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred)
        report = classification_report(y_test, y_pred, target_names=["Good Review (0)", "Bad Review (1)"], output_dict=True)
        print(f"\n--- {name} ---")
        print(f"Accuracy: {acc:.4f}")
        print("Confusion matrix [[TN, FP], [FN, TP]]:\n", cm)
        print(f"Bad-review recall: {report['Bad Review (1)']['recall']:.3f}, precision: {report['Bad Review (1)']['precision']:.3f}, f1: {report['Bad Review (1)']['f1-score']:.3f}")

        fig, ax = plt.subplots(figsize=(6, 6))
        RocCurveDisplay.from_estimator(model, X_test_proc, y_test, ax=ax)
        ax.plot([0, 1], [0, 1], color="red", linestyle="--")
        ax.set_title(f"ROC Curve - {name}")
        fig.savefig(FIGURES_DIR / f"roc_curve_{name.lower().replace(' ', '_')}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    df = load_processed("analytics_main_data")
    print(f"Loaded analytics_main_data: {df.shape}")
    forecast_sales(df)
    predict_bad_reviews(df)


if __name__ == "__main__":
    main()
