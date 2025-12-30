# Spotify Playlist Analytics Pipeline

A production-ready data engineering project demonstrating end-to-end ETL pipeline development, workflow orchestration, and analytical data modeling using real-world music streaming data.

## Project Overview

This project showcases core data engineering competencies through building a scalable ETL pipeline that extracts playlist metadata from the Spotify Web API, transforms it into structured analytical datasets, and loads it into a relational data warehouse. The pipeline is orchestrated with Apache Airflow and serves insights through a Django web application.

**Key Engineering Challenges Solved:**
- API rate limiting and pagination handling for large-scale data extraction
- Idempotent data loading with UPSERT operations to handle incremental updates
- Nested JSON data normalization and schema design
- Workflow orchestration and dependency management
- Environment-agnostic configuration for local and containerized deployments

## Technical Architecture

### Data Pipeline Flow

```
Spotify API → Extract → Transform → Load → PostgreSQL → Django Dashboard
                ↓          ↓          ↓
            Raw JSON   Pandas DF   UPSERT
                                    ↓
                            Primary Key Constraint
```

### Core Components

#### 1. **Data Extraction Layer** ([scripts/extract.py](scripts/extract.py))
- **API Integration**: Implements OAuth2 authentication with Spotify Web API using client credentials flow
- **Pagination Handling**: Processes playlists with 100+ tracks using cursor-based pagination
- **Rate Limiting**: Built-in delays (100ms) between artist genre lookups to respect API limits
- **Error Recovery**: Try-except blocks for graceful handling of missing artist data
- **Data Enrichment**: Fetches artist genres through additional API calls, joining data from multiple endpoints

**Technical Highlights:**
- Dynamic environment variable loading based on deployment mode (local vs Docker)
- Extracts 12+ attributes per track including metadata, album info, and artist relationships
- Handles many-to-many relationships (tracks ↔ artists, artists ↔ genres)

#### 2. **Data Transformation Layer** ([scripts/transform.py](scripts/transform.py))
- **Data Cleaning**: Type conversions, null handling, and data validation
- **Feature Engineering**: Duration conversion (ms → minutes), date parsing, genre aggregation
- **Normalization**: Flattens nested JSON structures (artist arrays, genre lists) into tabular format
- **Aggregation**: Calculates top artists, genres, and track statistics for analytical queries
- **Data Quality**: Deduplication and schema enforcement before loading

**Technical Highlights:**
- Pandas-based transformations for efficient in-memory processing
- Exports to multiple formats (CSV, Parquet) for data archival and downstream consumption
- Handles missing values and inconsistent API responses

#### 3. **Data Loading Layer** ([scripts/load.py](scripts/load.py))
- **Database Connection**: SQLAlchemy engine with PostgreSQL dialect for database-agnostic code
- **UPSERT Pattern**: Implements `INSERT ... ON CONFLICT DO UPDATE` for idempotent loads
- **Transactional Loading**: Uses temporary tables and atomic operations to prevent partial loads
- **JSONB Storage**: Stores array fields (genres, artist_ids) as JSONB for flexible querying
- **Type Casting**: Explicit CAST operations during insert for data type validation

**Technical Highlights:**
```sql
-- Idempotent UPSERT logic preventing duplicates
ON CONFLICT (playlist_id, track_id) DO UPDATE SET
    track_name = EXCLUDED.track_name,
    track_popularity = EXCLUDED.track_popularity,
    ...
```

#### 4. **Workflow Orchestration** (Apache Airflow)
- **DAG Definition**: Defines task dependencies and execution order (extract → transform → load)
- **Scheduling**: Supports cron-based scheduling and on-demand triggering
- **Monitoring**: Web UI for pipeline observability, logs, and failure detection
- **Containerization**: Runs in Docker with separate webserver, scheduler, and worker containers

#### 5. **Data Warehouse Schema** (PostgreSQL)

**Table: `playlist_tracks`**
```sql
CREATE TABLE playlist_tracks (
    playlist_id INTEGER NOT NULL,
    track_id VARCHAR(255) NOT NULL,
    track_name VARCHAR(500),
    track_duration_ms INTEGER,
    track_popularity INTEGER,
    track_genres JSONB,              -- Flexible schema for array data
    album_id VARCHAR(255),
    album_name VARCHAR(500),
    album_release_date DATE,
    album_label VARCHAR(500),
    artist_ids JSONB,
    artist_names JSONB,
    PRIMARY KEY (playlist_id, track_id)  -- Composite key for idempotency
);
```

**Design Decisions:**
- Composite primary key on `(playlist_id, track_id)` enables UPSERT operations
- JSONB fields for denormalized artist/genre data (optimized for read-heavy analytics)
- VARCHAR lengths sized for Spotify's data constraints
- Date types for temporal analysis capabilities

#### 6. **Application Layer** (Django)
- RESTful interface for playlist submission and result visualization
- ORM-based queries to PostgreSQL for data retrieval
- User authentication and session management

## Technologies & Tools

**Data Engineering Stack:**
- **Python 3.x**: Core scripting language
- **Apache Airflow**: Workflow orchestration and scheduling
- **PostgreSQL**: Relational data warehouse
- **Pandas**: Data transformation and analysis
- **SQLAlchemy**: Database abstraction and ORM
- **Spotipy**: Spotify Web API client library

**DevOps & Infrastructure:**
- **Docker & Docker Compose**: Containerization and local development
- **Git**: Version control
- **python-dotenv**: Environment configuration management

**Web Framework:**
- **Django**: Application server and admin interface

## Key Data Engineering Concepts Demonstrated

### 1. **ETL Pipeline Design**
- Separation of concerns: Extract, Transform, Load as independent modules
- Modular, reusable code structure
- Environment-based configuration for portability

### 2. **Data Modeling**
- Star schema design with denormalized dimensions (JSONB fields)
- Primary key constraints for data integrity
- Idempotent operations for reliable re-runs

### 3. **Workflow Orchestration**
- DAG-based task scheduling
- Dependency management between pipeline stages
- Retry logic and failure handling

### 4. **Scalability Patterns**
- Pagination for large dataset processing
- Batch processing with temporary staging tables
- Stateless pipeline design for horizontal scaling

### 5. **Data Quality**
- Schema validation through explicit type casting
- Null handling and default values
- Error logging and monitoring

## Local Development Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Spotify Developer Account ([Get credentials here](https://developer.spotify.com/dashboard))
- Virtual environment tool (venv, conda)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/spotify-playlist-analyzer.git
   cd spotify-playlist-analyzer
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Create `.env.local` in the project root:
   ```bash
   # Spotify API Credentials
   SPOTIPY_CLIENT_ID=your_client_id_here
   SPOTIPY_CLIENT_SECRET=your_client_secret_here

   # PostgreSQL Connection
   DB_NAME=playlist_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432

   # Environment Mode
   ENV_MODE=local
   ```

4. **Set up PostgreSQL database**
   ```sql
   CREATE DATABASE playlist_db;

   -- Create table with composite primary key
   CREATE TABLE playlist_tracks (
       playlist_id INTEGER NOT NULL,
       track_id VARCHAR(255) NOT NULL,
       track_name VARCHAR(500),
       track_duration_ms INTEGER,
       track_popularity INTEGER,
       track_genres JSONB,
       album_id VARCHAR(255),
       album_name VARCHAR(500),
       album_release_date DATE,
       album_label VARCHAR(500),
       artist_ids JSONB,
       artist_names JSONB,
       PRIMARY KEY (playlist_id, track_id)
   );
   ```

5. **Run the ETL pipeline manually**
   ```bash
   # Extract data from Spotify API
   python scripts/extract.py

   # Transform data
   python scripts/transform.py

   # Load into PostgreSQL
   python scripts/load.py
   ```

6. **Launch Django application**
   ```bash
   cd playlist_analyzer
   python manage.py migrate
   python manage.py runserver
   ```

   Access at: `http://localhost:8000`

### Docker Deployment (Airflow)

For production-like orchestration with Airflow:

```bash
cd airflow
docker compose up -d
```

Access Airflow UI at `http://localhost:8080` (credentials: `airflow/airflow`)

## Pipeline Execution

**Manual Execution:**
```bash
python scripts/extract.py   # Creates data/raw_playlist_data.csv
python scripts/transform.py # Creates data/cleaned_playlist_data.csv
python scripts/load.py      # Loads to PostgreSQL with UPSERT
```

**Airflow Execution:**
1. Open Airflow UI at `http://localhost:8080`
2. Enable the `playlist_etl_dag`
3. Trigger manually or wait for scheduled run
4. Monitor task execution and logs

## Data Flow Example

**Input:** Spotify Playlist URL
```
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

**Extract Output:** Raw JSON → DataFrame (100+ tracks)
```
track_id, track_name, artist_ids, artist_names, genres, duration_ms, ...
```

**Transform Output:** Cleaned and enriched data
```
track_id, track_name, track_duration_min, top_genre, release_year, ...
```

**Load Output:** PostgreSQL table with composite primary key
```sql
SELECT track_name, artist_names, track_genres
FROM playlist_tracks
WHERE playlist_id = 1;
```

## Project Structure

```
spotify-playlist-analyzer/
├── scripts/
│   ├── extract.py          # API extraction logic
│   ├── transform.py        # Data transformation with Pandas
│   └── load.py             # PostgreSQL loading with UPSERT
├── airflow/
│   ├── dags/
│   │   └── playlist_etl_dag.py  # Airflow DAG definition
│   └── docker-compose.yml       # Airflow containerization
├── playlist_analyzer/           # Django web application
│   ├── dashboard/              # Playlist visualization
│   └── users/                  # User authentication
├── data/                       # Data storage (CSV, Parquet)
├── .env.local                  # Local environment config
├── .env.docker                 # Docker environment config
├── requirements.txt            # Python dependencies
└── README.md
```

## Future Enhancements

**Data Engineering Improvements:**
- Implement incremental loading using Spotify's `snapshot_id` for change data capture
- Add data quality tests with Great Expectations or similar framework
- Implement streaming ingestion with Apache Kafka for real-time updates
- Add data lineage tracking and metadata management
- Migrate to cloud data warehouse (Snowflake/BigQuery/Redshift)
- Implement dbt for transformation layer with version control

**Infrastructure Improvements:**
- CI/CD pipeline with automated testing
- Infrastructure as Code with Terraform
- Monitoring and alerting with Prometheus/Grafana
- Data catalog with Apache Atlas or Amundsen

## Skills Demonstrated

✅ **ETL Development**: End-to-end pipeline implementation

✅ **SQL & Data Modeling**: Schema design, UPSERT operations, JSONB

✅ **Workflow Orchestration**: Apache Airflow DAG development

✅ **Python**: Pandas, SQLAlchemy, API integration

✅ **Database Management**: PostgreSQL, indexing, constraints

✅ **Data Quality**: Validation, deduplication, error handling

✅ **DevOps**: Docker, environment management, configuration

✅ **API Integration**: OAuth, pagination, rate limiting

## Contact & Acknowledgments

This project was built to demonstrate practical data engineering skills for portfolio and job applications.

**License:** MIT
