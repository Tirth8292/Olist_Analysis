import csv
import math
from collections import defaultdict

from .config import REPORTS_DIR
from .db import connect


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def haversine_km(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def write_rows(path, fieldnames, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_seller_scores(conn) -> None:
    rows = []
    for row in conn.execute("select * from vw_seller_performance_base"):
        on_time = row["on_time_delivery_rate"] or 0
        review = (row["avg_review_score"] or 0) / 5
        cancel = 1 - (row["cancellation_rate"] or 0)
        growth = clamp(((row["revenue_growth_rate"] or 0) + 1) / 2)
        score = round(100 * ((0.4 * on_time) + (0.3 * review) + (0.2 * cancel) + (0.1 * growth)), 2)
        if score >= 80:
            tier = "low_risk"
        elif score >= 60:
            tier = "watchlist"
        else:
            tier = "high_risk"
        rows.append({
            "seller_id": row["seller_id"],
            "seller_city": row["seller_city"],
            "seller_state": row["seller_state"],
            "orders": row["orders"],
            "gmv": row["gmv"],
            "on_time_delivery_rate": row["on_time_delivery_rate"],
            "avg_review_score": row["avg_review_score"],
            "cancellation_rate": row["cancellation_rate"],
            "revenue_growth_rate": row["revenue_growth_rate"],
            "performance_score": score,
            "risk_tier": tier,
        })
    rows.sort(key=lambda r: r["performance_score"])
    write_rows(REPORTS_DIR / "seller_scores.csv", rows[0].keys(), rows)


def build_customer_rfm(conn) -> None:
    sql = """
    with customer_orders as (
      select
        customer_unique_id,
        max(o.purchase_date) as last_purchase_date,
        count(distinct o.order_id) as frequency,
        sum(i.item_gmv) as monetary
      from fct_orders o
      join fct_order_items i on o.order_id = i.order_id
      where o.order_status = 'delivered'
      group by 1
    ),
    max_date as (select max(purchase_date) as analysis_date from fct_orders)
    select
      customer_unique_id,
      cast(julianday((select analysis_date from max_date)) - julianday(last_purchase_date) as integer) as recency_days,
      frequency,
      round(monetary, 2) as monetary
    from customer_orders
    """
    rows = []
    for row in conn.execute(sql):
        recency = row["recency_days"]
        frequency = row["frequency"]
        monetary = row["monetary"] or 0
        if frequency >= 3 and monetary >= 500:
            segment = "champions"
        elif frequency >= 2:
            segment = "loyal"
        elif recency <= 90:
            segment = "recent"
        elif recency > 365:
            segment = "at_risk"
        else:
            segment = "needs_attention"
        rows.append({
            "customer_unique_id": row["customer_unique_id"],
            "recency_days": recency,
            "frequency": frequency,
            "monetary": monetary,
            "rfm_segment": segment,
        })
    write_rows(REPORTS_DIR / "customer_rfm.csv", rows[0].keys(), rows)


def build_cohort_retention(conn) -> None:
    sql = """
    select
      customer_unique_id,
      strftime('%Y-%m', purchase_date) as order_month
    from fct_orders
    where order_status = 'delivered'
    group by 1, 2
    """
    customer_months = defaultdict(list)
    for row in conn.execute(sql):
        customer_months[row["customer_unique_id"]].append(row["order_month"])

    cohorts = defaultdict(set)
    retained = defaultdict(set)
    for customer_id, months in customer_months.items():
        months = sorted(months)
        cohort = months[0]
        cohorts[cohort].add(customer_id)
        cohort_year, cohort_month = map(int, cohort.split("-"))
        for order_month in months:
            year, month = map(int, order_month.split("-"))
            month_number = (year - cohort_year) * 12 + (month - cohort_month)
            retained[(cohort, month_number)].add(customer_id)

    rows = []
    for (cohort, month_number), customers in sorted(retained.items()):
        cohort_size = len(cohorts[cohort])
        rows.append({
            "cohort_month": cohort,
            "month_number": month_number,
            "customers": len(customers),
            "cohort_size": cohort_size,
            "retention_rate": round(len(customers) / cohort_size, 4) if cohort_size else 0,
        })
    write_rows(REPORTS_DIR / "cohort_retention.csv", rows[0].keys(), rows)


def build_delivery_lanes(conn) -> None:
    sql = """
    select
      i.order_id,
      s.seller_zip_code_prefix,
      c.customer_zip_code_prefix,
      s.seller_latitude,
      s.seller_longitude,
      c.customer_latitude,
      c.customer_longitude,
      i.delivery_days,
      i.is_late_delivery
    from fct_order_items i
    join fct_orders o on i.order_id = o.order_id
    join dim_sellers s on i.seller_id = s.seller_id
    join dim_customers c on o.customer_id = c.customer_id
    where i.order_status = 'delivered'
    """
    lane_stats = defaultdict(lambda: {"orders": 0, "delivery_days": 0.0, "late": 0, "distance": []})
    for row in conn.execute(sql):
        key = (row["seller_zip_code_prefix"], row["customer_zip_code_prefix"])
        distance = haversine_km(
            row["seller_latitude"],
            row["seller_longitude"],
            row["customer_latitude"],
            row["customer_longitude"],
        )
        lane_stats[key]["orders"] += 1
        lane_stats[key]["delivery_days"] += row["delivery_days"] or 0
        lane_stats[key]["late"] += row["is_late_delivery"] or 0
        if distance is not None:
            lane_stats[key]["distance"].append(distance)

    rows = []
    for (origin_zip, destination_zip), stats in lane_stats.items():
        orders = stats["orders"]
        avg_distance = sum(stats["distance"]) / len(stats["distance"]) if stats["distance"] else None
        rows.append({
            "origin_zip": origin_zip,
            "destination_zip": destination_zip,
            "orders": orders,
            "avg_delivery_days": round(stats["delivery_days"] / orders, 2),
            "late_delivery_rate": round(stats["late"] / orders, 4),
            "avg_distance_km": round(avg_distance, 2) if avg_distance is not None else "",
        })
    rows.sort(key=lambda r: r["orders"], reverse=True)
    write_rows(REPORTS_DIR / "delivery_lanes.csv", rows[0].keys(), rows)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        build_seller_scores(conn)
        build_customer_rfm(conn)
        build_cohort_retention(conn)
        build_delivery_lanes(conn)
    print(f"wrote feature reports to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
