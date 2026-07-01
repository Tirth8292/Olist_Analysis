from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/olist_analytics_platform"
DATA_DIR = "/opt/airflow/data/olist"


with DAG(
    dag_id="olist_marketplace_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["olist", "analytics-engineering"],
) as dag:
    load_raw = BashOperator(
        task_id="load_raw_csvs",
        bash_command=f"cd {PROJECT_DIR} && python -m src.olist_platform.extract_load --data-dir {DATA_DIR}",
    )

    transform = BashOperator(
        task_id="build_star_schema",
        bash_command=f"cd {PROJECT_DIR} && python -m src.olist_platform.transform",
    )

    quality_checks = BashOperator(
        task_id="run_quality_checks",
        bash_command=f"cd {PROJECT_DIR} && python -m src.olist_platform.run_quality_checks",
    )

    features = BashOperator(
        task_id="build_feature_exports",
        bash_command=f"cd {PROJECT_DIR} && python -m src.olist_platform.feature_engineering",
    )

    load_raw >> transform >> quality_checks >> features

