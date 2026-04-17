from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dbt_transformation_dag",
    default_args=default_args,
    description="Run dbt models after Spotify ETL",
    schedule_interval=None,  # playlist_etl_dag 끝나면 수동 or 연결
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dbt", "spotify"],
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/airflow/dbt/spotify_dbt && dbt run --profiles-dir /opt/airflow/dbt",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/dbt/spotify_dbt && dbt test --profiles-dir /opt/airflow/dbt",
    )

    dbt_run >> dbt_test