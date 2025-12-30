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

This project consists of **two complementary systems** that demonstrate different aspects of data engineering:

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

┌─────────────────────────────────────────────────────────────────────┐
│                    WEB APPLICATION (Django)                         │
│                   User-Facing Analytics Interface                   │
├─────────────────────────────────────────────────────────────────────┤
│  User → Submit URL → extract.py → transform.py                     │
│                                               ↓                     │
│                              load_tracks_to_db() (Django ORM)       │
│                                               ↓                     │
│                          Django Database (SQLite/PostgreSQL)        │
│                         (Playlist & Track models)                   │
│                                               ↓                     │
│                          Dashboard Visualization                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Architecture Highlights

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
- Django ORM with SQLite for development (PostgreSQL-ready for production)
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

#### 6. **Application Layer** ([playlist_analyzer/dashboard/views.py](playlist_analyzer/dashboard/views.py))
- **Web Interface**: Django-based application for user-facing playlist analysis
- **Data Loading**: `load_tracks_to_db()` function implements UPSERT logic using Django ORM
- **Query Optimization**: Uses `select_related()` for efficient database queries
- **User Authentication**: Per-user playlist isolation with Django's auth system
- **Real-time Processing**: On-demand ETL execution when users submit playlist URLs

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

**Load Output:** PostgreSQL table with composite primary key
```sql
SELECT track_name, artist_names, track_genres
FROM playlist_tracks
WHERE playlist_id = 1;
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
│   ├── db.sqlite3                  # Django database (dev: SQLite, prod: PostgreSQL)
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
| **Database** | PostgreSQL (Docker container) | SQLite (dev) / PostgreSQL (prod) |
| **Execution** | Scheduled/triggered DAGs | On-demand via HTTP requests |
| **Load Strategy** | Raw SQL UPSERT (high-performance) | Django ORM (database-agnostic) |
| **Data Scope** | Centralized analytics datasets | Per-user isolated playlists |
| **Orchestration** | Apache Airflow | Django request/response cycle |
| **Optimization** | Bulk operations, temp tables | Query optimization, `select_related()` |
| **Use Case** | Production data pipelines | Interactive user dashboards |

**Why Two Systems?**
- **Code Reusability**: Shared extract/transform logic demonstrates modular design
- **Different Patterns**: Shows both batch processing (Airflow) and request-driven ETL (Django)
- **Scalability Options**: Airflow for bulk, Django for real-time user needs
- **Portfolio Breadth**: Demonstrates expertise in both workflow orchestration and web development

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
- Switch Django database to PostgreSQL for production consistency

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

## Contact & Acknowledgments

This project was built to demonstrate practical data engineering skills for portfolio and job applications.

**License:** MIT
