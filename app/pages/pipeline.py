import streamlit as st
import logging
from app.db import query_df
from app.charts import mart_bar_chart, mart_scatter_chart, duration_by_year_chart

logger = logging.getLogger(__name__)


def render():
    st.title("Data Pipeline")
    st.markdown(
        "An end-to-end data engineering pipeline that ingests Spotify playlist data, "
        "orchestrates ETL with Apache Airflow, transforms it with dbt, and serves "
        "analytics via a cloud PostgreSQL database."
    )

    st.info(
        "**Note:** The dbt mart (`mart_track_stats`) is pre-built and updated manually by running "
        "`dbt run --target supabase` locally. The live demo queries the latest snapshot."
    )

    st.markdown("---")

    # ── Tech stack ────────────────────────────────────────────────────────────
    st.subheader("Tech Stack")
    t1, t2, t3, t4, t5, t6, t7 = st.columns(7)
    t1.markdown("**Spotify API**\n\nData source")
    t2.markdown("**Python**\n\nExtract & transform")
    t3.markdown("**Apache Airflow**\n\nOrchestration")
    t4.markdown("**Docker**\n\nContainerisation")
    t5.markdown("**PostgreSQL**\n\nData warehouse")
    t6.markdown("**dbt**\n\nTransformations")
    t7.markdown("**Streamlit**\n\nDashboard")

    st.markdown("---")

    # ── Architecture diagram ──────────────────────────────────────────────────
    st.subheader("Architecture")
    st.markdown("""
    ```
    ┌──────────────────────────────────────────────────────────┐
    │                      Spotify Web API                     │
    │          track metadata · artist genres · popularity     │
    └─────────────────────────┬────────────────────────────────┘
                              │  spotipy (Python)
                              ▼
    ┌──────────────────────────────────────────────────────────┐
    │               Apache Airflow  (Docker)                   │
    │  ┌─────────────────────────────────────────────────┐     │
    │  │  playlist_etl_dag                               │     │
    │  │  ├── extract.py   fetch raw tracks from API     │     │
    │  │  ├── transform.py clean dates, durations, nulls │     │
    │  │  ├── load.py      UPSERT into PostgreSQL         │     │
    │  │  └── dbt_dag      run dbt models                 │     │
    │  └─────────────────────────────────────────────────┘     │
    └─────────────────────────┬────────────────────────────────┘
                              │  SQLAlchemy + psycopg2
                              ▼
    ┌──────────────────────────────────────────────────────────┐
    │              PostgreSQL — Supabase (cloud)               │
    │              table: playlist_tracks                      │
    │              raw per-user track data · JSONB arrays      │
    └──────────┬───────────────────────────────────────────────┘
               │  dbt run (run manually / via Airflow locally)
               ▼
    ┌──────────────────────────────────────────────────────────┐
    │                     dbt Core                             │
    │  ┌──────────────────────┐   ┌────────────────────────┐  │
    │  │  stg_tracks          │ → │  mart_track_stats       │  │
    │  │  staging model       │   │  mart model             │  │
    │  │  · type casting      │   │  · group by album/year  │  │
    │  │  · null filtering    │   │  · avg/max/min pop.     │  │
    │  │  · column renaming   │   │  · avg duration         │  │
    │  └──────────────────────┘   └────────────────────────┘  │
    └──────────┬───────────────────────────────────────────────┘
               │  SQL query
               ▼
    ┌──────────────────────────────────────────────────────────┐
    │                  Streamlit Cloud                         │
    │       Analyze · My Dashboard · Data Pipeline             │
    └──────────────────────────────────────────────────────────┘
    ```
    """)

    st.markdown("---")

    # ── Layer cards ───────────────────────────────────────────────────────────
    st.subheader("Pipeline Layers")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("##### Extract")
        st.markdown("""
`scripts/extract.py`
- Calls Spotify Web API via `spotipy`
- Fetches tracks, albums, artist metadata
- Enriches each track with artist genres
- Handles pagination (100 tracks/page)
        """)
    with col2:
        st.markdown("##### Transform")
        st.markdown("""
`scripts/transform.py`
- Parses `album_release_date` → `release_year`
- Converts `track_duration_ms` → seconds
- Fills null popularity scores with `0`
- Normalises list columns to JSON arrays
        """)
    with col3:
        st.markdown("##### Orchestrate")
        st.markdown("""
`airflow/dags/playlist_etl_dag.py`
- Runs the full ETL on trigger
- Chains extract → transform → load → dbt
- Dockerised with `docker-compose`
- Airflow logs every run with status
        """)
    with col4:
        st.markdown("##### Transform (dbt)")
        st.markdown("""
`spotify_dbt/models/`
- `stg_tracks` — staging view:
  casts types, filters nulls
- `mart_track_stats` — mart table:
  album-level aggregates
- Schema tests: `not_null`, `unique`
        """)

    st.markdown("---")

    # ── Live mart output ──────────────────────────────────────────────────────
    st.subheader("Live dbt Output")
    st.caption("mart_track_stats — pre-built album-level aggregates from dbt")

    try:
        mart_df = query_df("SELECT * FROM mart_track_stats ORDER BY avg_popularity DESC")
    except Exception:
        logger.exception("Failed to query mart_track_stats")
        st.error("Could not load pipeline data. Please try again later.")
        return

    if mart_df.empty:
        st.info("mart_track_stats is empty — run `dbt run --target supabase` in the spotify_dbt folder first.")
        return

    try:
        raw_count = int(query_df("SELECT COUNT(*) as cnt FROM playlist_tracks")["cnt"].iloc[0])
    except Exception:
        raw_count = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Raw Tracks", raw_count, help="Rows in playlist_tracks (source table)")
    c2.metric("Albums in Mart", len(mart_df), help="Distinct albums after dbt aggregation")
    c3.metric("Total Tracks in Mart", int(mart_df["track_count"].sum()))
    c4.metric("Overall Avg Popularity", f"{mart_df['avg_popularity'].mean():.1f}")

    st.subheader("Top 20 Albums by Avg Popularity")
    st.plotly_chart(mart_bar_chart(mart_df), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Track Count vs Avg Popularity")
        st.plotly_chart(mart_scatter_chart(mart_df), use_container_width=True)
    with col_b:
        if "release_year" in mart_df.columns and "avg_duration_sec" in mart_df.columns:
            st.subheader("Avg Duration by Release Year")
            st.plotly_chart(duration_by_year_chart(mart_df), use_container_width=True)

    st.subheader("mart_track_stats — Full Table")
    st.dataframe(mart_df, use_container_width=True, hide_index=True)
