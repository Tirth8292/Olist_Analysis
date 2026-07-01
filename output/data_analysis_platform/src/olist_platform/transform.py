from pathlib import Path

from .config import PROJECT_ROOT
from .db import connect


SQL_FILES = [
    PROJECT_ROOT / "sql" / "01_staging.sql",
    PROJECT_ROOT / "sql" / "02_marts.sql",
    PROJECT_ROOT / "sql" / "03_views.sql",
]


def main() -> None:
    with connect() as conn:
        for sql_file in SQL_FILES:
            sql = Path(sql_file).read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.commit()
            print(f"ran {sql_file.name}")


if __name__ == "__main__":
    main()

