from .db import connect


CHECKS = {
    "orders_have_unique_ids": "select count(*) - count(distinct order_id) from stg_orders",
    "customers_have_unique_ids": "select count(*) - count(distinct customer_id) from stg_customers",
    "order_items_have_orders": """
        select count(*)
        from stg_order_items i
        left join stg_orders o on i.order_id = o.order_id
        where o.order_id is null
    """,
    "orders_have_customers": """
        select count(*)
        from stg_orders o
        left join stg_customers c on o.customer_id = c.customer_id
        where c.customer_id is null
    """,
    "payments_are_non_negative": "select count(*) from stg_payments where payment_value < 0",
}


def main() -> None:
    failures = []
    with connect() as conn:
        for name, sql in CHECKS.items():
            value = conn.execute(sql).fetchone()[0]
            status = "PASS" if value == 0 else "FAIL"
            print(f"{status} {name}: {value}")
            if value != 0:
                failures.append(name)
    if failures:
        raise SystemExit(f"Quality checks failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()

