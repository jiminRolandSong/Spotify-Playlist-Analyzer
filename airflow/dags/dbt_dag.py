from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import http.client
import json
import os
import socket

DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")
DBT_CONTAINER_NAME = os.getenv("DBT_CONTAINER_NAME", "airflow-dbt-1")


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)


def docker_request(method, path, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    conn = UnixSocketHTTPConnection(DOCKER_SOCKET_PATH)
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()

    if response.status >= 300:
        raise AirflowException(
            "Docker API request failed: {} {} -> {} {}".format(
                method, path, response.status, data.decode("utf-8", errors="replace")
            )
        )
    return data


def run_dbt_command(command):
    create_payload = {
        "AttachStdout": True,
        "AttachStderr": True,
        "Tty": True,
        "Cmd": ["sh", "-lc", "cd /usr/app/dbt && {}".format(command)],
        "Env": ["DBT_PROFILES_DIR=/root/.dbt"],
    }
    create_response = docker_request(
        "POST",
        "/containers/{}/exec".format(DBT_CONTAINER_NAME),
        create_payload,
    )
    exec_id = json.loads(create_response.decode("utf-8"))["Id"]

    output = docker_request(
        "POST",
        "/exec/{}/start".format(exec_id),
        {"Detach": False, "Tty": True},
    )
    if output:
        print(output.decode("utf-8", errors="replace"))

    inspect_response = docker_request("GET", "/exec/{}/json".format(exec_id))
    exit_code = json.loads(inspect_response.decode("utf-8")).get("ExitCode")
    if exit_code != 0:
        raise AirflowException("dbt command failed with exit code {}".format(exit_code))

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

    dbt_run = PythonOperator(
        task_id="dbt_run",
        python_callable=run_dbt_command,
        op_args=["dbt run"],
    )

    dbt_test = PythonOperator(
        task_id="dbt_test",
        python_callable=run_dbt_command,
        op_args=["dbt test"],
    )

    dbt_run >> dbt_test
