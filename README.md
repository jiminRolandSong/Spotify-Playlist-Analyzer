# Spotify Playlist Analyzer


## Overview

The Spotify Playlist Analyzer is a robust data engineering and web application project designed to extract, transform, load (ETL), and visualize data from Spotify playlists. It leverages modern data pipelines and web frameworks to provide insights into playlist characteristics such as top artists, genres, and track details. While Spotify's direct audio features API is no longer available for new applications, this project focuses on maximizing insights from available metadata and providing a scalable, maintainable architecture.

## Features

* **Playlist Submission**: Users can input a Spotify playlist URL for analysis.
* **User Authentication**: Secure user login and registration for personalized experience.
* **ETL Pipeline Orchestration**: Automated data extraction, transformation, and loading using Apache Airflow.
* **Persistent Data Storage**: Analyzed playlist and track data are stored in a PostgreSQL database, ensuring data integrity and persistence across user sessions.
* **Interactive Dashboard (Planned/Enhancement)**: A Django-powered web interface to display aggregated playlist insights.
    * Currently displays basic track information and aggregated lists.
    * **Future Enhancement**: Integrate interactive charts for better visualization of artist and genre distribution, release year trends, and track duration insights.
* **Data Transformation**: Cleans, enriches, and structures raw Spotify data for analytical use.
* **Containerized Environment**: Easy setup and deployment using Docker and Docker Compose.

## Architecture

The project follows a decoupled, modular architecture:

1.  **Data Extraction (`scripts/extract.py`)**:
    * Connects to the Spotify Web API using `spotipy`.
    * Extracts comprehensive metadata for playlists and their tracks.
    * **Note**: Due to recent Spotify API changes (November 2024), direct access to `audio-features` and `audio-analysis` endpoints is deprecated for new applications. The project focuses on leveraging available track and artist metadata.
2.  **Data Transformation (`scripts/transform.py`)**:
    * Utilizes Pandas for data manipulation.
    * Performs data cleaning, type conversions (e.g., milliseconds to minutes), handling of missing values, and parsing of nested data (e.g., artists, genres).
    * Aggregates data for high-level insights (e.g., top artists, top genres).
3.  **Data Loading (`scripts/load.py`)**:
    * Connects to a PostgreSQL database using SQLAlchemy and Psycopg2.
    * Implements **UPSERT (Update or Insert)** logic to ensure data idempotency and prevent duplicate entries for tracks and playlists upon re-analysis.
    * Also saves transformed data locally in CSV and Parquet formats for data archival/inspection.
4.  **ETL Orchestration (`airflow/dags/playlist_etl_dag.py`)**:
    * An Apache Airflow DAG defines the sequence and dependencies of the ETL tasks (extract -> transform -> load).
    * Allows for scheduled execution and dynamic triggering of analyses based on user input.
5.  **Web Interface (`playlist_analyzer/`)**:
    * A Django application serves as the frontend dashboard.
    * Manages user authentication (`users` app).
    * Handles playlist submission, initiating the Airflow DAG via a management command (or API trigger).
    * Retrieves and displays processed data from the PostgreSQL database in a user-friendly format.
6.  **Containerization**:
    * `docker-compose.yml` sets up the entire development environment, including:
        * PostgreSQL database
        * Redis (for Airflow and potential future Celery integration)
        * Airflow components (Webserver, Scheduler, Worker)
        * Django application

## Technologies Used

* **Python**: Core programming language.
* **Django**: Web framework for the dashboard.
* **Pandas**: Data manipulation and analysis.
* **Spotipy**: Python library for Spotify Web API interaction.
* **Apache Airflow**: Workflow orchestration for ETL pipelines.
* **PostgreSQL**: Primary relational database for analytical data.
* **SQLAlchemy**: ORM/SQL Toolkit for Python database interactions.
* **Psycopg2**: PostgreSQL adapter for Python.
* **Docker & Docker Compose**: Containerization for environment setup.
* **HTML/CSS/JavaScript**: Frontend development.
* **SQLite**: (Used for temporary dashboard display; planned to be replaced by direct PostgreSQL queries for scalability).

## Enhancements & Future Work

This project is continuously evolving. Planned enhancements focus on refining the data engineering pipeline and improving the user experience:

* **Advanced Data Visualization**: Implement interactive charts (e.g., using Chart.js, Plotly.js) on the Django dashboard to visualize:
    * Top Artists and Genres (bar charts)
    * Release Year Distribution (histogram/bar chart)
    * Track Duration Distribution (histogram)
    * Playlist Popularity Score
* **Improved ETL Robustness**:
    * **Idempotent Data Loading**: Fully implement UPSERT logic for `Track` records in PostgreSQL to ensure that re-analyzing the same playlist updates existing data and avoids duplicates.
    * **Granular Error Handling**: Enhance `try-except` blocks and logging in ETL scripts for better debugging and resilience against API issues or data inconsistencies.
    * **Incremental Loading**: Explore strategies to only process new or changed tracks within a playlist when re-analyzing, based on Spotify's `snapshot_id` or track `added_at` timestamps.
* **Enhanced User Experience**:
    * **Asynchronous Feedback**: Provide immediate feedback to users when a playlist analysis is initiated, indicating that the process is running in the background.
    * **Direct PostgreSQL Queries for Dashboard**: Transition dashboard data retrieval from temporary SQLite loads to direct queries against the main PostgreSQL database using Django ORM for consistency and scalability.
    * **Playlist Management**: Allow users to easily view and manage their previously analyzed playlists, with quick summaries.
* **Data Quality**: Further normalize and enrich genre data for more consistent analysis.
* **Deployment**: Prepare for production deployment considerations (e.g., Gunicorn/Nginx, scalable Airflow executor).

## Setup and Installation

### Prerequisites

* Docker and Docker Compose
* A Spotify Developer Account (for API credentials)

### Steps

1.  **Clone the Repository**:
    ```bash
    git clone [https://github.com/your-username/spotify-playlist-analyzer.git](https://github.com/your-username/spotify-playlist-analyzer.git)
    cd spotify-playlist-analyzer
    ```

2.  **Configure Environment Variables**:
    Create a `.env` file in the project root with your Spotify API credentials and PostgreSQL database settings:
    ```
    SPOTIPY_CLIENT_ID=your_spotify_client_id
    SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
    DATABASE_URL=postgresql://user:password@db:5432/spotify_db
    SECRET_KEY=your_django_secret_key # Use a strong, random string for production
    DJANGO_SUPERUSER_USERNAME=admin
    DJANGO_SUPERUSER_EMAIL=admin@example.com
    DJANGO_SUPERUSER_PASSWORD=password
    ```
    Ensure your `airflow/.env` file also contains relevant database and Airflow specific variables.

3.  **Build and Run Docker Containers**:
    Navigate to the `airflow` directory first to build and start Airflow services:
    ```bash
    cd airflow
    docker compose up --build -d
    ```
    Then, build and run the Django application (from the project root):
    ```bash
    cd ..
    docker compose up --build -d
    ```

4.  **Initialize Django Database & Create Superuser**:
    ```bash
    docker compose exec django python manage.py migrate
    docker compose exec django python manage.py createsuperuser --noinput
    ```

5.  **Access Services**:
    * **Django Application**: `http://localhost:8000`
    * **Airflow UI**: `http://localhost:8080` (Login with `airflow/airflow` or your configured credentials)

6.  **Unpause Airflow DAG**:
    In the Airflow UI, navigate to `DAGs`, find `playlist_etl_dag`, and toggle it to "On" (unpause).

## Usage

1.  **Register/Login** on the Django dashboard (`http://localhost:8000`).
2.  Navigate to the **Submit Playlist** section.
3.  Enter a **Spotify Playlist URL** (e.g., `https://open.spotify.com/playlist/...`).
4.  Click **Analyze**.
5.  The Django app will trigger the Airflow DAG. You can monitor the progress in the Airflow UI.
6.  Once the DAG completes successfully, navigate to **My Playlists** or the **Dashboard** link for the specific playlist to view the analysis.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests for bug fixes, new features, or improvements.

## License

This project is licensed under the MIT License.