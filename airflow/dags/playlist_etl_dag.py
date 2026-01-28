from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# docker-compose up airflow-init
# docker-compose up
# docker-compose down

# docker exec -it airflow-postgres-1 psql -U airflow -d playlist_db -c "SELECT * FROM playlist_tracks LIMIT 10;"


# Mount points inside container
sys.path.append("/opt/airflow/scripts")

# Import your custom ETL scripts
from extract import spotify_api_setup, extract_playlist_tracks
from transform import transform_playlist_df
import pandas as pd
from load import load_to_postgreSQL


# Define default args
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

# Playlist ID 
# PLAYLIST_ID = "2wazkzhuzpipWcVKjOa7Vg?si=aef86f19c5254c97"  

# File paths
RAW_PATH = "/opt/airflow/data/raw_playlist_data.csv"
CLEAN_PATH = "/opt/airflow/data/cleaned_playlist_data.csv"

# DAG
with DAG(
    dag_id="playlist_etl_dag",
    default_args=default_args,
    description="Spotify Playlist ETL DAG",
    schedule_interval="@daily",  # or None for manual run
    
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["spotify", "ETL"],
) as dag:

    def extract_task(**context):
        playlist_id = context["dag_run"].conf.get("playlist_id", "")
        if not playlist_id:
            # Use default playlist ID if not provided
            playlist_id = "1ssFFcU1hlZnKgNnDshd0F"
            print(f"[INFO] No playlist_id passed. Using default: {playlist_id}")
        sp = spotify_api_setup()
        df, _ = extract_playlist_tracks(sp, playlist_id)
        df.to_csv(RAW_PATH, index=False)
        print(f"Extracted and saved {len(df)} tracks")
        # Push playlist_id to XCom for downstream tasks
        context["task_instance"].xcom_push(key="playlist_id", value=playlist_id)

    def transform_task():
        import pandas as pd
        df = pd.read_csv(RAW_PATH)
        transformed_df = transform_playlist_df(df)
        transformed_df.to_csv(CLEAN_PATH, index=False)
        print(f"Transformed and saved {len(transformed_df)} records")

    def load_task(**context):
        # Pull playlist_id from XCom
        playlist_id = context["task_instance"].xcom_pull(task_ids="extract_playlist_data", key="playlist_id")
        df = pd.read_csv(CLEAN_PATH)
        df['playlist_id'] = playlist_id
        load_to_postgreSQL(df, table_name="playlist_tracks")
        
    extract_op = PythonOperator(
        task_id="extract_playlist_data",
        python_callable=extract_task,
    )

    transform_op = PythonOperator(
        task_id="transform_playlist_data",
        python_callable=transform_task,
    )

    load_op = PythonOperator(
        task_id="load_playlist_data",
        python_callable=load_task,
    )

    extract_op >> transform_op >> load_op