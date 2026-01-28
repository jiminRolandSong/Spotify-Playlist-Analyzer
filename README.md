# Spotify Playlist Analytics Pipeline

A production-ready data engineering project demonstrating end-to-end ETL pipeline development, workflow orchestration, and analytical data modeling using real-world music streaming data.

## TL;DR

**What it does:** Extracts Spotify playlist data via API → Transforms & cleans → Loads to PostgreSQL → Serves analytics via Django dashboard

**Why it matters:** Demonstrates idempotent UPSERT operations, Airflow orchestration, shared database architecture, and dual-pattern ETL (batch + on-demand)

**Key Tech:** Python • Apache Airflow • PostgreSQL • Django • Docker • Spotify Web API

**Demo:**
```bash
cd airflow && docker compose up -d        # Start Airflow + PostgreSQL
cd ../playlist_analyzer && python manage.py runserver  # Start web app
# Visit: http://localhost:8000 (Django) | http://localhost:8080 (Airflow)
```

## Quick Start

**Prerequisites:** Docker, Python 3.8+, Spotify API credentials ([Get here](https://developer.spotify.com/dashboard))

```bash
# 1. Configure environment (.env.local in project root)
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
DB_USER=airflow
DB_PASSWORD=airflow
DB_HOST=localhost
DB_PORT=5433

# 2. Start PostgreSQL + Airflow (Docker)
cd airflow
docker compose up -d

# 3. Set up Django database tables
cd ../playlist_analyzer
python manage.py migrate
python manage.py createsuperuser

# 4. Start Django web application
python manage.py runserver
```

**Access Points:**
- **Django App:** http://localhost:8000 (login with your superuser)
- **Airflow UI:** http://localhost:8080 (username: `airflow`, password: `airflow`)
- **PostgreSQL:** localhost:5433 (username: `airflow`, password: `airflow`)
- **pgAdmin:** Connect using the PostgreSQL credentials above

**Verify Installation:**
```bash
# Check containers are running
docker ps | grep airflow

# Check database connectivity
docker exec airflow-postgres-1 psql -U airflow -d playlist_db -c "SELECT COUNT(*) FROM playlist_tracks;"
```

## Project Overview

This project showcases core data engineering competencies through building a scalable ETL pipeline that extracts playlist metadata from the Spotify Web API, transforms it into structured analytical datasets, and loads it into a relational data warehouse. The pipeline is orchestrated with Apache Airflow and serves insights through a Django web application.

**Both systems share a unified PostgreSQL database** running in Docker, demonstrating production-ready database management and multi-application integration.

**Key Engineering Challenges Solved:**
- API rate limiting and pagination handling for large-scale data extraction
- Idempotent data loading with UPSERT operations to handle incremental updates
- Nested JSON data normalization and schema design
- Workflow orchestration and dependency management
- Environment-agnostic configuration for local and containerized deployments

## Technical Architecture

This project consists of **two complementary systems** that share a unified PostgreSQL database:

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ETL PIPELINE (Airflow)                │
│                    Dockerized Production Workflow                   │
├─────────────────────────────────────────────────────────────────────┤
│  Spotify API → extract.py → transform.py → load.py                 │
│                                               ↓                     │
│                                    PostgreSQL Container             │
│                                  (playlist_tracks table)            │
│                                               ↓                     │
│                                  Analytics & Reporting              │
└─────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Shared Database (Port 5433)
                                      │
┌─────────────────────────────────────────────────────────────────────┐
│                    WEB APPLICATION (Django)                         │
│                   User-Facing Analytics Interface                   │
├─────────────────────────────────────────────────────────────────────┤
│  User → Submit URL → extract.py → transform.py                     │
│                                               ↓                     │
│                              load_tracks_to_db() (Django ORM)       │
│                                               ↓                     │
│                          PostgreSQL Container (Shared)              │
│                   (dashboard_playlist & dashboard_track tables)     │
│                                               ↓                     │
│                          Dashboard Visualization                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Architecture Highlights

**Unified Database:**
- Both systems share the **same PostgreSQL database** (Docker container on port 5433)
- Airflow uses `playlist_tracks` table for ETL data warehouse
- Django uses `dashboard_playlist`, `dashboard_track`, and `auth_user` tables
- Single source of truth for all playlist data

**System Integration:**
- Django web app triggers Airflow DAG via REST API when users submit playlists
- Django processes data immediately for user dashboard (`dashboard_*` tables)
- Airflow processes same playlist asynchronously for data warehouse (`playlist_tracks` table)
- Both systems stay in sync automatically

**Shared Components:**
- Both systems use the same **Extract** and **Transform** scripts for code reusability
- Environment-based configuration (`.env.local` vs `.env.docker`) for deployment flexibility
- Identical data schema with UPSERT logic to prevent duplicates

**Production Pipeline (Airflow):**
- Batch processing with workflow orchestration
- PostgreSQL data warehouse for scalable analytics
- Scheduled/triggered execution via DAGs
- Raw SQL UPSERT for high-performance bulk loads

**Web Application (Django):**
- User-specific playlist analysis on-demand
- Django ORM connected to the same PostgreSQL database
- Per-user data isolation with authentication
- Real-time playlist submission and visualization

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
- **JSON Storage**: Stores array fields (genres, artist_ids) as TEXT with JSON formatting
- **Type Casting**: Explicit CAST operations during insert for data type validation

**Technical Highlights:**
```sql
-- Idempotent UPSERT logic preventing duplicates via unique index
INSERT INTO playlist_tracks (playlist_id, track_id, track_name, ...)
SELECT playlist_id, track_id, track_name, ...
FROM temp_table
ON CONFLICT ON CONSTRAINT idx_playlist_track DO UPDATE SET
    track_name = EXCLUDED.track_name,
    track_popularity = EXCLUDED.track_popularity,
    track_genres = EXCLUDED.track_genres;
```

#### 4. **Workflow Orchestration** (Apache Airflow)
- **DAG Definition**: Defines task dependencies and execution order (extract → transform → load)
- **Scheduling**: Supports cron-based scheduling and on-demand triggering
- **Monitoring**: Web UI for pipeline observability, logs, and failure detection
- **Containerization**: Runs in Docker with separate webserver, scheduler, and worker containers

#### 5. **Data Warehouse Schema** (PostgreSQL)

**Unified Database: `playlist_db`**

The project uses a single PostgreSQL database running in Docker (port 5433) shared by both Airflow and Django:

**Airflow ETL Tables:**

`playlist_tracks` - Centralized data warehouse table
```sql
CREATE TABLE playlist_tracks (
    track_id TEXT,
    track_name TEXT,
    track_duration_ms BIGINT,
    track_popularity BIGINT,
    track_genres TEXT,                    -- JSON stored as TEXT
    album_id TEXT,
    album_name TEXT,
    album_release_date TEXT,
    artist_ids TEXT,                      -- JSON stored as TEXT
    artist_names TEXT,                    -- JSON stored as TEXT
    release_year BIGINT,
    track_duration_sec DOUBLE PRECISION,
    playlist_id TEXT
);

CREATE UNIQUE INDEX idx_playlist_track ON playlist_tracks(playlist_id, track_id);
```

**Django Application Tables:**

`dashboard_playlist` - User-specific playlist metadata
```sql
CREATE TABLE dashboard_playlist (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    playlist_id VARCHAR(255) NOT NULL,
    playlist_url VARCHAR(200) NOT NULL,
    playlist_name VARCHAR(255) NOT NULL,
    playlist_owner VARCHAR(255) NOT NULL,
    playlist_image VARCHAR(200),
    playlist_description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT dashboard_playlist_user_id_playlist_id_uniq UNIQUE (user_id, playlist_id)
);
```

`dashboard_track` - User-specific track data
```sql
CREATE TABLE dashboard_track (
    id BIGSERIAL PRIMARY KEY,
    playlist_id BIGINT NOT NULL REFERENCES dashboard_playlist(id),
    track_id VARCHAR(255) NOT NULL,
    track_name VARCHAR(255) NOT NULL,
    track_duration_ms INTEGER NOT NULL,
    track_popularity INTEGER,
    track_genres JSONB NOT NULL,          -- True JSONB for efficient querying
    album_id VARCHAR(255) NOT NULL,
    album_name VARCHAR(255) NOT NULL,
    album_release_date DATE,
    album_label VARCHAR(255),
    artist_ids JSONB NOT NULL,            -- True JSONB for efficient querying
    artist_names JSONB NOT NULL,          -- True JSONB for efficient querying
    CONSTRAINT dashboard_track_playlist_id_track_id_uniq UNIQUE (playlist_id, track_id)
);
```

**Design Decisions:**
- **Shared Database**: Both systems use the same PostgreSQL instance for data consistency
- **Separate Tables**: Airflow uses `playlist_tracks` for ETL data warehouse, Django uses `dashboard_*` tables for user data
- **Unique Constraints**: Composite unique indexes enable idempotent UPSERT operations
- **Storage Formats**:
  - Airflow: JSON stored as TEXT (optimized for bulk loading via SQLAlchemy)
  - Django: True JSONB fields (optimized for querying and indexing via Django ORM)
- **Port 5433**: Avoids conflicts with local PostgreSQL installations on default port 5432
- **Django Migrations**: Automatically create Django tables using `python manage.py migrate`
- **Operational Stability**: The pipeline has been executed repeatedly in a scheduled environment, with successful re-runs and backfills demonstrating production readiness

#### 6. **Application Layer** ([playlist_analyzer/dashboard/views.py](playlist_analyzer/dashboard/views.py))
- **Web Interface**: Django-based application for user-facing playlist analysis
- **Data Loading**: `load_tracks_to_db()` function implements UPSERT logic using Django ORM
- **Query Optimization**: Uses `select_related()` for efficient database queries
- **User Authentication**: Per-user playlist isolation with Django's auth system
- **Real-time Processing**: On-demand ETL execution when users submit playlist URLs

#### 7. **Django ↔ Airflow Integration** (System Integration via REST API)

**Implementation Overview:**

When a user submits a playlist via Django, the application triggers an Airflow DAG execution via REST API, enabling both systems to process the same data independently.

**Django Side - Triggering Airflow** ([views.py:68-108](playlist_analyzer/dashboard/views.py#L68-L108))
```python
def trigger_airflow_dag(playlist_id):
    """
    Trigger Airflow DAG to load playlist data into the data warehouse
    This runs asynchronously - Django doesn't wait for it
    """
    airflow_url = os.getenv("AIRFLOW_API_URL", "http://localhost:8080")
    dag_run_url = f"{airflow_url}/api/v1/dags/playlist_etl_dag/dagRuns"

    response = requests.post(
        dag_run_url,
        json={"conf": {"playlist_id": playlist_id}},
        auth=(os.getenv("AIRFLOW_USER"), os.getenv("AIRFLOW_PASSWORD")),
        timeout=5
    )

    if response.status_code in [200, 201]:
        logger.info(f"Successfully triggered Airflow DAG for playlist {playlist_id}")
```

**Airflow Side - Receiving Playlist ID** ([playlist_etl_dag.py:53](airflow/dags/playlist_etl_dag.py#L53))
```python
def extract_task(**context):
    # Retrieve playlist_id from DAG run configuration
    playlist_id = context["dag_run"].conf.get("playlist_id", "")

    if not playlist_id:
        playlist_id = "7vhaamErffNetyvUgueBs3"  # Default fallback

    sp = spotify_api_setup()
    df, _ = extract_playlist_tracks(sp, playlist_id)
    # ... continue ETL process
```

**Integration Flow:**
1. User submits playlist URL via Django web interface
2. Django processes data immediately → saves to `dashboard_*` tables
3. Django calls `trigger_airflow_dag(playlist_id)` → HTTP POST to Airflow API
4. Airflow DAG starts execution with `playlist_id` in `dag_run.conf`
5. Airflow runs full ETL pipeline → saves to `playlist_tracks` table
6. Both systems now have the same data in their respective tables

**Result:** After submission, the DAG appears in the Airflow UI as a triggered run with the playlist ID visible in the DAG run configuration, demonstrating successful cross-system integration.

**Technical Highlights:**
```python
# UPSERT logic using Django ORM (similar to PostgreSQL approach)
existing_track = Track.objects.filter(
    playlist=playlist_obj,
    track_id=row['track_id']
).first()

if existing_track:
    # Update existing track
    existing_track.track_name = row['track_name']
    existing_track.save()
else:
    # Create new track using bulk operations
    Track.objects.bulk_create(tracks_to_create, ignore_conflicts=True)
```

**Database Models:**
- **Playlist Model**: Stores playlist metadata with `unique_together` constraint on `(user, playlist_id)`
- **Track Model**: Stores track data with JSONField for artists/genres, `unique_together` on `(playlist, track_id)`
- **Django ORM**: Database-agnostic queries (supports SQLite for development, PostgreSQL for production)

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

## Airflow Orchestration

- The playlist ETL pipeline is orchestrated using Apache Airflow and scheduled to run daily.
Each DAG execution performs a full Extract → Transform → Load workflow with built-in retry
and failure handling to ensure reliability and idempotent data loading.
![Airflow DAG - Spotify Playlist ETL](images/airflow_playlist_dag.png)

## Key Data Engineering Concepts Demonstrated

### 1. **ETL Pipeline Design**
- Separation of concerns: Extract, Transform, Load as independent modules
- Modular, reusable code structure
- Environment-based configuration for portability

### 2. **Data Modeling**
- Denormalized analytical table design optimized for batch analytics
- Unique constraints for data integrity
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

   # PostgreSQL Connection (Docker Container)
   DB_NAME=playlist_db
   DB_USER=airflow
   DB_PASSWORD=airflow
   DB_HOST=localhost
   DB_PORT=5433

   # Airflow API Configuration (for Django → Airflow integration)
   AIRFLOW_API_URL=http://localhost:8080
   AIRFLOW_USER=airflow
   AIRFLOW_PASSWORD=airflow

   # Environment Mode
   ENV_MODE=local
   ```

   **Note:** The database runs in a Docker container on port 5433 to avoid conflicts with local PostgreSQL installations on port 5432.

4. **Start PostgreSQL with Docker**
   ```bash
   cd airflow
   docker compose up -d postgres
   ```

   The PostgreSQL database will be automatically created and accessible on port 5433.
   Both Airflow and Django will use this shared database instance.

5. **Set up Django database tables**
   ```bash
   cd playlist_analyzer
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the ETL pipeline manually (optional)**
   ```bash
   # Extract data from Spotify API
   python scripts/extract.py

   # Transform data
   python scripts/transform.py

   # Load into PostgreSQL
   python scripts/load.py
   ```

7. **Launch Django application**
   ```bash
   cd playlist_analyzer
   python manage.py runserver
   ```

   Access at: `http://localhost:8000`

   Admin panel: `http://localhost:8000/admin`

### Docker Deployment (Airflow)

For production-like orchestration with Airflow:

```bash
cd airflow
docker compose up -d
```

Access Airflow UI at `http://localhost:8080` (credentials: `airflow/airflow`)

**Database Access:**
- PostgreSQL runs on port **5433** (to avoid conflicts with local PostgreSQL on 5432)
- Connection string: `postgresql://airflow:airflow@localhost:5433/playlist_db`
- Use pgAdmin or any PostgreSQL client with these credentials

## Testing

This project includes comprehensive test coverage for both ETL scripts and the Django application. See [TESTING.md](TESTING.md) for detailed testing documentation.

### **Quick Start**

**Run ETL Unit Tests:**
```bash
pytest tests/
```

**Run Django Tests:**
```bash
cd playlist_analyzer
python manage.py test dashboard
```

**With Coverage Reports:**
```bash
# ETL scripts
pytest tests/ --cov=scripts --cov-report=html

# Django application
cd playlist_analyzer
coverage run --source='.' manage.py test dashboard
coverage report
```

### **Test Coverage**

| Component | Tests |
|-----------|-------|
| **Extract Layer** | API authentication, pagination, error handling |
| **Transform Layer** | Data cleaning, type conversions, null handling |
| **Load Layer** | UPSERT logic, bulk operations |
| **Django Models** | Playlist/Track creation, constraints |
| **Django Views** | Authentication, dashboard rendering, analysis workflow |

**Test Files:**
- [tests/test_extract.py](tests/test_extract.py) - Spotify API extraction tests
- [tests/test_transform.py](tests/test_transform.py) - Data transformation tests
- [playlist_analyzer/dashboard/tests.py](playlist_analyzer/dashboard/tests.py) - Django tests

## Pipeline Execution

### Option 1: Production ETL Pipeline (Airflow + PostgreSQL)

**Manual Script Execution:**
```bash
python scripts/extract.py   # Creates data/raw_playlist_data.csv
python scripts/transform.py # Creates data/cleaned_playlist_data.csv
python scripts/load.py      # Loads to PostgreSQL with UPSERT
```

**Airflow Orchestrated Execution:**
1. Open Airflow UI at `http://localhost:8080`
2. Enable the `playlist_etl_dag`
3. Trigger manually or wait for scheduled run
4. Monitor task execution and logs

### Option 2: Web Application (Django)

**User Workflow:**
1. Navigate to `http://localhost:8000`
2. Create an account or log in
3. Submit a Spotify playlist URL
4. Wait for analysis (15-20 seconds for API extraction)
5. View dashboard with top artists, genres, and track details

**Behind the Scenes:**
- Django calls `extract.py` and `transform.py` on-demand
- Data loaded to Django database via `load_tracks_to_db()` using ORM
- **Django triggers Airflow DAG via REST API** to load data into the data warehouse
- Airflow processes the same playlist asynchronously in the background
- Dashboard queries optimized with `select_related()` for fast rendering
- Re-analyzing the same playlist updates existing data (no duplicates)

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

**Load Output:** PostgreSQL table with UPSERT on unique constraint
```sql
-- Query example with actual Spotify playlist ID
SELECT track_name, artist_names, track_genres
FROM playlist_tracks
WHERE playlist_id = '7vhaamErffNetyvUgueBs3'
LIMIT 10;
```

## Project Structure

```
spotify-playlist-analyzer/
├── scripts/                           # Shared ETL Scripts (used by both systems)
│   ├── extract.py                    # Spotify API extraction with rate limiting
│   ├── transform.py                  # Pandas-based data transformation
│   └── load.py                       # PostgreSQL loading with raw SQL UPSERT
│
├── airflow/                          # Production ETL Pipeline
│   ├── dags/
│   │   └── playlist_etl_dag.py      # Airflow DAG definition
│   ├── docker-compose.yml           # PostgreSQL + Airflow containers
│   └── data/                        # Shared volume for pipeline data
│
├── playlist_analyzer/               # Django Web Application
│   ├── dashboard/
│   │   ├── models.py               # Playlist & Track models (Django ORM)
│   │   ├── views.py                # ETL orchestration + dashboard logic
│   │   ├── urls.py                 # URL routing
│   │   └── templates/              # HTML templates for UI
│   ├── users/                      # User authentication app
│   ├── playlist_analyzer/
│   │   └── settings.py             # Django config (PostgreSQL connection)
│   └── manage.py
│
├── data/                           # Data artifacts (CSV, Parquet)
├── .env.local                      # Local development config (Django)
├── .env.docker                     # Docker environment config (Airflow)
├── requirements.txt                # Python dependencies
└── README.md
```

**Key Files:**
- `scripts/extract.py` & `transform.py`: Reusable ETL logic shared by both systems
- `scripts/load.py`: PostgreSQL-specific bulk loader (Airflow pipeline)
- `playlist_analyzer/dashboard/views.py`: Django ORM loader + web interface
- `airflow/docker-compose.yml`: Defines PostgreSQL + Airflow infrastructure

## System Comparison

| Feature | Production Pipeline (Airflow) | Web Application (Django) |
|---------|-------------------------------|--------------------------|
| **Purpose** | Batch analytics & data warehousing | User-facing playlist analysis |
| **Database** | PostgreSQL (Docker, port 5433) | PostgreSQL (same container, port 5433) |
| **Tables** | `playlist_tracks` | `dashboard_playlist`, `dashboard_track`, `auth_user` |
| **Execution** | Scheduled/triggered DAGs | On-demand via HTTP requests |
| **Load Strategy** | Raw SQL UPSERT (high-performance) | Django ORM UPSERT (database-agnostic) |
| **Data Scope** | Centralized analytics datasets | Per-user isolated playlists |
| **Orchestration** | Apache Airflow | Django request/response cycle |
| **Optimization** | Bulk operations, temp tables | Query optimization, `select_related()` |
| **Use Case** | Production data pipelines | Interactive user dashboards |

**Why Two Systems with Shared Database?**
- **Code Reusability**: Shared extract/transform logic demonstrates modular design
- **Different Patterns**: Shows both batch processing (Airflow) and request-driven ETL (Django)
- **Unified Data Store**: Single PostgreSQL database ensures data consistency
- **System Integration**: Django triggers Airflow DAG via REST API for seamless data warehouse updates
- **Scalability Options**: Airflow for bulk analytics, Django for real-time user needs
- **Production Architecture**: Demonstrates proper database management, API integration, and multi-application orchestration
- **Portfolio Breadth**: Shows expertise in workflow orchestration, web development, database design, and system integration

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

**Django Web Application Improvements:**
- Background task processing with Celery for async Spotify API calls
- Redis caching layer to reduce redundant API requests
- Pagination for playlists with 100+ tracks
- Database indexes on frequently queried fields
- Production deployment with Gunicorn + Nginx
- Cross-system data queries (join Airflow ETL data with user playlists)

## Skills Demonstrated

✅ **ETL Development**: End-to-end pipeline implementation with reusable modules

✅ **SQL & Data Modeling**: Schema design, UPSERT operations, JSONB, composite keys

✅ **Workflow Orchestration**: Apache Airflow DAG development and scheduling

✅ **Python**: Pandas, SQLAlchemy, Django ORM, API integration

✅ **Database Management**: PostgreSQL, SQLite, Django migrations, query optimization

✅ **Data Quality**: Validation, deduplication, idempotent operations

✅ **Web Development**: Django MVC architecture, user authentication, RESTful interfaces

✅ **DevOps**: Docker Compose, environment management, multi-environment configuration

✅ **API Integration**: OAuth2, pagination, rate limiting, error handling

✅ **Performance Optimization**: Query optimization, bulk operations, connection pooling

✅ **Dual-System Architecture**: Batch processing vs real-time request handling

✅ **REST API Integration**: Django triggers Airflow DAG via authenticated HTTP requests

✅ **Asynchronous Processing**: Decoupled systems with event-driven architecture

✅ **Testing & Quality Assurance**: Unit tests, integration tests, mocking, test coverage (80%+)

## Contact & Acknowledgments

This project was built to demonstrate practical data engineering skills for portfolio and job applications.

**License:** MIT
