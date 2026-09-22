"""Build the joined CSV outputs from the original Olist CSV files."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import tempfile
from pathlib import Path


SOURCE_TABLES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

SQL_OUTPUTS = {
    "customer_data.sql": "customer_data.csv",
    "customer_order.sql": "customer_order.csv",
    "customer_payment.sql": "customer_payment.csv",
    "delivery_data.sql": "delivery_data.csv",
    "product_review.sql": "porduct_review.csv",
    "transacion_static_data.sql": "transacion_static_data.csv",
    "transaction_data.sql": "transaction_data.csv",
}


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def load_csv(connection: sqlite3.Connection, table: str, path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader, [])
        if not columns:
            raise ValueError(f"CSV has no header: {path}")
        connection.execute(
            f"CREATE TABLE {quote(table)} ({', '.join(f'{quote(column)} TEXT' for column in columns)})"
        )
        placeholders = ", ".join("?" for _ in columns)
        batch = []
        for row in reader:
            batch.append(row[: len(columns)] + [None] * max(0, len(columns) - len(row)))
            if len(batch) == 10000:
                connection.executemany(
                    f"INSERT INTO {quote(table)} VALUES ({placeholders})", batch
                )
                batch.clear()
        if batch:
            connection.executemany(
                f"INSERT INTO {quote(table)} VALUES ({placeholders})", batch
            )


def export_table(connection: sqlite3.Connection, table: str, path: Path) -> int:
    cursor = connection.execute(f"SELECT * FROM {quote(table)}")
    columns = [description[0] for description in cursor.description]
    try:
        handle = path.open("w", encoding="utf-8", newline="")
    except PermissionError:
        path = path.with_name(f"{path.stem}_regenerated{path.suffix}")
        handle = path.open("w", encoding="utf-8", newline="")
        print(f"Output was locked; writing {path.name} instead.")
    with handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        count = 0
        while True:
            rows = cursor.fetchmany(10000)
            if not rows:
                break
            writer.writerows(rows)
            count += len(rows)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--only", choices=sorted(SQL_OUTPUTS), help="Build one SQL output only.")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    source_dir = project_root / "Data Set"
    output_dir = project_root / "join operations"
    selected_outputs = [args.only] if args.only else list(SQL_OUTPUTS)
    missing_sql = [name for name in selected_outputs if not (output_dir / name).exists()]
    if missing_sql:
        raise FileNotFoundError(
            f"Missing join SQL file(s): {', '.join(missing_sql)} in {output_dir}"
        )
    temporary_database = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    temporary_database.close()
    connection = sqlite3.connect(temporary_database.name)
    try:
        for table, filename in SOURCE_TABLES.items():
            path = source_dir / filename
            if not path.exists():
                raise FileNotFoundError(path)
            print(f"Loading {filename}...")
            load_csv(connection, table, path)
        connection.commit()

        outputs = SQL_OUTPUTS.items()
        if args.only:
            outputs = [(args.only, SQL_OUTPUTS[args.only])]
        for sql_filename, output_filename in outputs:
            sql_path = output_dir / sql_filename
            sql = sql_path.read_text(encoding="utf-8")
            connection.executescript(sql)
            table = sql_filename.removesuffix(".sql")
            if table == "product_review":
                output_table = "product_review"
            else:
                output_table = table
            count = export_table(connection, output_table, output_dir / output_filename)
            print(f"Wrote {output_filename}: {count:,} rows")
    finally:
        connection.close()
        try:
            Path(temporary_database.name).unlink(missing_ok=True)
        except PermissionError:
            pass


if __name__ == "__main__":
    main()
