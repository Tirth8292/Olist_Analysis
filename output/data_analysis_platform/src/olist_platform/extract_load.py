import argparse
import csv
from pathlib import Path

from .config import RAW_FILES
from .db import connect


def infer_columns(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return [column.lstrip("\ufeff") for column in next(csv.reader(handle))]


def create_raw_table(conn, table_name: str, columns: list[str]) -> None:
    quoted_columns = ", ".join(f'"{column}" TEXT' for column in columns)
    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(f'CREATE TABLE "{table_name}" ({quoted_columns})')


def load_csv(conn, table_name: str, csv_path: Path) -> int:
    columns = infer_columns(csv_path)
    create_raw_table(conn, table_name, columns)
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'

    count = 0
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames:
            reader.fieldnames = [column.lstrip("\ufeff") for column in reader.fieldnames]
        batch = []
        for row in reader:
            batch.append([row.get(column) or None for column in columns])
            if len(batch) >= 10000:
                conn.executemany(insert_sql, batch)
                count += len(batch)
                batch.clear()
        if batch:
            conn.executemany(insert_sql, batch)
            count += len(batch)
    conn.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Olist CSVs into the local warehouse.")
    parser.add_argument("--data-dir", required=True, help="Folder containing the Olist CSV files.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    with connect() as conn:
        for table_name, file_name in RAW_FILES.items():
            csv_path = data_dir / file_name
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing required file: {csv_path}")
            count = load_csv(conn, table_name, csv_path)
            print(f"loaded {table_name}: {count:,} rows")


if __name__ == "__main__":
    main()
