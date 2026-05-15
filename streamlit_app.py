import streamlit as st
import pandas as pd
import psycopg2
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import Counter
import plotly.express as px
from supabase import create_client
import os

st.set_page_config(
    page_title="Spotify Playlist Analyzer",
    page_icon="🎵",
    layout="wide",
)

# ── Supabase auth client ─────────────────────────────────────────────────────

@st.cache_resource
def get_supabase():
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["anon_key"])


# ── Auth UI ──────────────────────────────────────────────────────────────────

def auth_page():
    st.title("🎵 Spotify Playlist Analyzer")
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary", key="login_btn"):
            try:
                res = get_supabase().auth.sign_in_with_password({"email": email, "password": password})
                st.session_state["user"] = res.user
                st.session_state["access_token"] = res.session.access_token
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password (min 6 chars)", type="password", key="signup_password")
        if st.button("Create Account", type="primary", key="signup_btn"):
            try:
                res = get_supabase().auth.sign_up({"email": email, "password": password})
                if res.user and res.session:
                    st.session_state["user"] = res.user
                    st.session_state["access_token"] = res.session.access_token
                    st.rerun()
                else:
                    st.error("Sign up failed. Try again.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")


if "user" not in st.session_state:
    auth_page()
    st.stop()

user = st.session_state["user"]
user_id = user.id

# ── DB connection ────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    db = st.secrets["postgres"]
    return psycopg2.connect(
        host=db["host"],
        port=db.get("port", 6543),
        dbname=db["dbname"],
        user=db["user"],
        password=db["password"],
        sslmode=db.get("sslmode", "require"),
        client_encoding="utf8",
    )


def query_df(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(sql, conn, params=params)


def run_dbt():
    import subprocess, shutil
    if not shutil.which("dbt"):
        return
    dbt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotify_dbt")
    subprocess.Popen(
        ["dbt", "run", "--target", "supabase"],
        cwd=dbt_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def save_tracks_to_db(df: pd.DataFrame, playlist_id: str, uid: str):
    from urllib.parse import quote_plus
    import json, ast
    from sqlalchemy import create_engine, text

    db = st.secrets["postgres"]
    engine = create_engine(
        f"postgresql+psycopg2://{quote_plus(db['user'])}:{quote_plus(db['password'])}@{db['host']}:{db.get('port', 6543)}/{db['dbname']}",
        connect_args={"sslmode": "require", "client_encoding": "utf8"},
    )

    df = df.copy()
    df["playlist_id"] = playlist_id
    df["user_id"] = uid

    # Ensure list columns are JSON strings
    for col in ["artist_names", "track_genres", "artist_ids"]:
        if col in df.columns:
            def safe_json(x):
                if isinstance(x, list):
                    return json.dumps(x)
                try:
                    val = ast.literal_eval(x) if pd.notna(x) else []
                    return json.dumps(val)
                except Exception:
                    return json.dumps([])
            df[col] = df[col].apply(safe_json)

    if "track_duration_sec" not in df.columns and "track_duration_ms" in df.columns:
        df["track_duration_sec"] = df["track_duration_ms"] / 1000
    if "release_year" not in df.columns and "release_date" in df.columns:
        df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year

    import os
    temp = f"temp_st_{os.urandom(6).hex()}"
    df.to_sql(temp, engine, if_exists="replace", index=False)

    cols = [c for c in df.columns if c in [
        "user_id", "playlist_id", "track_id", "track_name", "track_duration_ms",
        "track_popularity", "track_genres", "album_id", "album_name",
        "album_release_date", "album_label", "artist_ids", "artist_names",
        "release_year", "track_duration_sec",
    ]]

    cast_map = {
        "track_genres": "CAST(track_genres AS jsonb)",
        "artist_ids": "CAST(artist_ids AS jsonb)",
        "artist_names": "CAST(artist_names AS jsonb)",
        "album_release_date": "CAST(album_release_date AS DATE)",
    }
    select_parts = [cast_map.get(c, c) for c in cols]

    update_cols = [c for c in cols if c not in ("user_id", "playlist_id", "track_id")]
    update_parts = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    upsert_sql = f"""
        INSERT INTO playlist_tracks ({", ".join(cols)})
        SELECT {", ".join(select_parts)} FROM {temp}
        ON CONFLICT (user_id, playlist_id, track_id) DO UPDATE SET {update_parts};
        DROP TABLE {temp};
    """
    with engine.begin() as conn:
        conn.execute(text(upsert_sql))


# ── Spotify client ───────────────────────────────────────────────────────────

@st.cache_resource
def get_spotify():
    sp_cfg = st.secrets["spotify"]
    return spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
        client_id=sp_cfg["client_id"],
        client_secret=sp_cfg["client_secret"],
    ))


def parse_playlist_id(url_or_id: str) -> str:
    return url_or_id.strip().split("/")[-1].split("?")[0]


# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("🎵 Playlist Analyzer")
st.sidebar.caption(f"Logged in as {user.email}")
page = st.sidebar.radio(
    "Navigate",
    ["Analyze Playlist", "My Dashboard", "Data Pipeline"],
)
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    get_supabase().auth.sign_out()
    del st.session_state["user"]
    del st.session_state["access_token"]
    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Analyze Playlist
# ════════════════════════════════════════════════════════════════════════════

if page == "Analyze Playlist":
    st.title("Analyze a Spotify Playlist")
    st.markdown("Paste a Spotify playlist URL or ID to fetch, save, and explore its tracks.")

    url_input = st.text_input("Spotify Playlist URL or ID", placeholder="https://open.spotify.com/playlist/...")
    save_to_db = st.checkbox("Save to my dashboard", value=True)

    if st.button("Analyze", type="primary") and url_input:
        playlist_id = parse_playlist_id(url_input)

        with st.spinner("Fetching playlist from Spotify..."):
            try:
                sp = get_spotify()
                info = sp.playlist(playlist_id)
                items_result = sp.playlist_items(playlist_id, additional_types=["track"], limit=100)

                rows = []
                artist_genre_cache = {}

                while items_result:
                    for item in items_result["items"]:
                        track = item.get("track")
                        if not track:
                            continue
                        album = track["album"]
                        artists = track["artists"]

                        genre_set = set()
                        for a in artists:
                            aid = a["id"]
                            if aid not in artist_genre_cache:
                                try:
                                    artist_genre_cache[aid] = sp.artist(aid).get("genres", [])
                                except Exception:
                                    artist_genre_cache[aid] = []
                            genre_set.update(artist_genre_cache[aid])

                        release_date = album.get("release_date", "")
                        try:
                            release_year = int(str(release_date)[:4]) if release_date else None
                        except Exception:
                            release_year = None

                        rows.append({
                            "track_id": track["id"],
                            "track_name": track["name"],
                            "artist_names": [a["name"] for a in artists],
                            "artist_ids": [a["id"] for a in artists],
                            "album_id": album["id"],
                            "album_name": album["name"],
                            "album_release_date": (release_date + "-01-01") if release_date and len(release_date) == 4 else (release_date + "-01") if release_date and len(release_date) == 7 else release_date,
                            "track_popularity": track.get("popularity", 0),
                            "track_duration_ms": track["duration_ms"],
                            "track_duration_sec": track["duration_ms"] / 1000,
                            "track_genres": list(genre_set),
                            "release_year": release_year,
                        })
                    if items_result["next"]:
                        items_result = sp.next(items_result)
                    else:
                        break

                df = pd.DataFrame(rows)

                if save_to_db and not df.empty:
                    save_tracks_to_db(df, playlist_id, user_id)
                    run_dbt()
                    st.success(f"Saved {len(df)} tracks to your dashboard. Pipeline is updating in the background.")

                # Display
                images = info.get("images", [])
                img_url = images[0]["url"] if images else None
                col1, col2 = st.columns([1, 3])
                with col1:
                    if img_url:
                        st.image(img_url, width=180)
                with col2:
                    st.subheader(info.get("name", ""))
                    st.caption(f"Owner: {info['owner']['display_name']}  •  {len(df)} tracks")
                    desc = info.get("description", "")
                    if desc:
                        st.markdown(desc, unsafe_allow_html=True)

                st.markdown("---")

                display_df = df[["track_name", "artist_names", "album_name", "album_release_date", "track_popularity", "track_duration_ms"]].copy()
                display_df["artist_names"] = display_df["artist_names"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
                display_df["duration_min"] = (display_df["track_duration_ms"] / 60000).round(2)
                display_df = display_df.drop(columns=["track_duration_ms"])

                c1, c2, c3 = st.columns(3)
                c1.metric("Tracks", len(df))
                c2.metric("Avg Popularity", f"{df['track_popularity'].mean():.1f}")
                c3.metric("Avg Duration (min)", f"{(df['track_duration_ms'] / 60000).mean():.2f}")

                st.subheader("Track List")
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                artist_counts = Counter(
                    a for cell in df["artist_names"] for a in (cell if isinstance(cell, list) else [cell])
                )
                top_artists = pd.DataFrame(artist_counts.most_common(10), columns=["Artist", "Tracks"])
                st.subheader("Top Artists")
                st.plotly_chart(
                    px.bar(top_artists, x="Tracks", y="Artist", orientation="h",
                           color="Tracks", color_continuous_scale="Tealgrn"),
                    use_container_width=True,
                )

                st.subheader("Popularity Distribution")
                st.plotly_chart(
                    px.histogram(df, x="track_popularity", nbins=20,
                                 color_discrete_sequence=["#1DB954"]),
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Failed to fetch playlist: {e}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — My Dashboard (per-user)
# ════════════════════════════════════════════════════════════════════════════

elif page == "My Dashboard":
    st.title("My Dashboard")
    st.markdown("Your saved playlists.")

    try:
        playlists_df = query_df(
            "SELECT DISTINCT playlist_id FROM playlist_tracks WHERE user_id = %s ORDER BY playlist_id",
            params=(user_id,),
        )
        if playlists_df.empty:
            st.info("No playlists saved yet. Go to Analyze Playlist and check 'Save to my dashboard'.")
            st.stop()

        sp = get_spotify()
        playlist_options = {}
        for pid in playlists_df["playlist_id"].tolist():
            try:
                info = sp.playlist(pid, fields="name")
                playlist_options[info["name"]] = pid
            except Exception:
                playlist_options[pid] = pid

        selected_name = st.selectbox("Select Playlist", list(playlist_options.keys()))
        selected_id = playlist_options[selected_name]

        df = query_df(
            "SELECT * FROM playlist_tracks WHERE user_id = %s AND playlist_id = %s",
            params=(user_id, selected_id),
        )

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Tracks", len(df))
        avg_pop = df["track_popularity"].mean() if "track_popularity" in df.columns else 0
        c2.metric("Avg Popularity", f"{avg_pop:.1f}")
        if "track_duration_sec" in df.columns:
            c3.metric("Avg Duration (min)", f"{df['track_duration_sec'].mean() / 60:.2f}")

        if "artist_names" in df.columns:
            artist_counts = Counter()
            for cell in df["artist_names"]:
                names = cell if isinstance(cell, list) else []
                for name in names:
                    if name:
                        artist_counts[str(name).strip()] += 1
            top_a = pd.DataFrame(artist_counts.most_common(10), columns=["Artist", "Tracks"])
            st.subheader("Top 10 Artists")
            st.plotly_chart(
                px.bar(top_a, x="Tracks", y="Artist", orientation="h",
                       color="Tracks", color_continuous_scale="Tealgrn"),
                use_container_width=True,
            )

        if "track_genres" in df.columns:
            genre_counts = Counter()
            for cell in df["track_genres"]:
                genres = cell if isinstance(cell, list) else []
                for g in genres:
                    if g:
                        genre_counts[str(g).strip()] += 1
            top_g = pd.DataFrame(genre_counts.most_common(10), columns=["Genre", "Count"])
            if not top_g.empty:
                st.subheader("Top 10 Genres")
                st.plotly_chart(
                    px.pie(top_g, names="Genre", values="Count", hole=0.4),
                    use_container_width=True,
                )

        if "release_year" in df.columns and "track_popularity" in df.columns:
            year_df = df.dropna(subset=["release_year"]).copy()
            year_df["release_year"] = year_df["release_year"].astype(int)
            year_df = year_df[year_df["release_year"] > 1900]
            year_df = year_df.groupby("release_year")["track_popularity"].mean().reset_index()
            year_df.columns = ["Year", "Avg Popularity"]
            st.subheader("Avg Popularity by Release Year")
            st.plotly_chart(
                px.line(year_df, x="Year", y="Avg Popularity", markers=True,
                        color_discrete_sequence=["#1DB954"]),
                use_container_width=True,
            )

        st.subheader("Full Track Table")
        st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Database error: {e}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Data Pipeline
# ════════════════════════════════════════════════════════════════════════════

elif page == "Data Pipeline":
    st.title("Data Pipeline")
    st.markdown("An end-to-end data engineering pipeline that ingests Spotify playlist data, orchestrates ETL with Apache Airflow, transforms it with dbt, and serves analytics via a cloud PostgreSQL database.")

    st.markdown("---")

    # ── Tech stack ───────────────────────────────────────────────────────────
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

    # ── Architecture diagram ─────────────────────────────────────────────────
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
               │  dbt run
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

    # ── Layer cards ──────────────────────────────────────────────────────────
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

    # ── Live mart output ─────────────────────────────────────────────────────
    st.subheader("Live dbt Output")
    st.caption("mart_track_stats — album-level aggregates produced by dbt from the raw playlist_tracks table")

    try:
        mart_df = query_df("SELECT * FROM mart_track_stats ORDER BY avg_popularity DESC")

        if mart_df.empty:
            st.info("mart_track_stats is empty — run `dbt run --target supabase` in the spotify_dbt folder first.")
            st.stop()

        raw_df = query_df("SELECT COUNT(*) as cnt FROM playlist_tracks")
        raw_count = int(raw_df["cnt"].iloc[0]) if not raw_df.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Raw Tracks", raw_count, help="Rows in playlist_tracks (source table)")
        c2.metric("Albums in Mart", len(mart_df), help="Distinct albums after dbt aggregation")
        c3.metric("Total Tracks in Mart", int(mart_df["track_count"].sum()))
        c4.metric("Overall Avg Popularity", f"{mart_df['avg_popularity'].mean():.1f}")

        st.subheader("Top 20 Albums by Avg Popularity")
        st.plotly_chart(
            px.bar(mart_df.head(20), x="avg_popularity", y="album_name", orientation="h",
                   color="avg_popularity", color_continuous_scale="Tealgrn",
                   labels={"avg_popularity": "Avg Popularity", "album_name": "Album"}),
            use_container_width=True,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Track Count vs Avg Popularity")
            st.plotly_chart(
                px.scatter(mart_df, x="track_count", y="avg_popularity",
                           hover_name="album_name", size="track_count",
                           color="avg_popularity", color_continuous_scale="Tealgrn",
                           labels={"track_count": "Tracks", "avg_popularity": "Avg Popularity"}),
                use_container_width=True,
            )
        with col_b:
            st.subheader("Avg Duration by Release Year")
            if "release_year" in mart_df.columns and "avg_duration_sec" in mart_df.columns:
                year_dur = mart_df.dropna(subset=["release_year"]).copy()
                year_dur = year_dur[year_dur["release_year"] > 1900]
                year_dur = year_dur.groupby("release_year")["avg_duration_sec"].mean().reset_index()
                year_dur.columns = ["Year", "Avg Duration (sec)"]
                st.plotly_chart(
                    px.line(year_dur, x="Year", y="Avg Duration (sec)", markers=True,
                            color_discrete_sequence=["#1DB954"]),
                    use_container_width=True,
                )

        st.subheader("mart_track_stats — Full Table")
        st.dataframe(mart_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Database error: {e}")
        st.info("Run `dbt run --target supabase` inside the spotify_dbt folder to populate mart_track_stats.")
