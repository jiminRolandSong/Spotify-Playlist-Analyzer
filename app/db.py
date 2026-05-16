import streamlit as st
import pandas as pd
import psycopg2
import json
import ast
import os
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


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


def _get_engine():
    db = st.secrets["postgres"]
    return create_engine(
        f"postgresql+psycopg2://{quote_plus(db['user'])}:{quote_plus(db['password'])}@{db['host']}:{db.get('port', 6543)}/{db['dbname']}",
        connect_args={"sslmode": "require", "client_encoding": "utf8"},
    )


def _safe_json(x):
    if isinstance(x, list):
        return json.dumps(x)
    try:
        val = ast.literal_eval(x) if pd.notna(x) else []
        return json.dumps(val)
    except Exception:
        return json.dumps([])


def save_tracks_to_db(df: pd.DataFrame, playlist_id: str, user_id: str):
    engine = _get_engine()
    df = df.copy()
    df["playlist_id"] = playlist_id
    df["user_id"] = user_id

    for col in ["artist_names", "track_genres", "artist_ids"]:
        if col in df.columns:
            df[col] = df[col].apply(_safe_json)

    if "track_duration_sec" not in df.columns and "track_duration_ms" in df.columns:
        df["track_duration_sec"] = df["track_duration_ms"] / 1000
    if "release_year" not in df.columns and "release_date" in df.columns:
        df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year

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

    logger.info("Saved %d tracks for playlist %s user %s", len(df), playlist_id, user_id)
