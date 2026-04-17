from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
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
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dbt", "spotify"],
) as dag:

    wait_for_etl = ExternalTaskSensor(
        task_id="wait_for_etl",
        external_dag_id="playlist_etl_dag",
        external_task_id="load_playlist_data",
        timeout=600,
        poke_interval=30,
        mode="poke",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="docker exec airflow-dbt-1 dbt run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="docker exec airflow-dbt-1 dbt test",
    )

    dbt_run >> dbt_test