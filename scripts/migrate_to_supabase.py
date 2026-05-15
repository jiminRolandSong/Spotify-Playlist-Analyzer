"""
One-time script: loads cleaned_playlist_data.csv into Supabase PostgreSQL.
Run from project root:  python scripts/migrate_to_supabase.py
"""
import pandas as pd
import os
import sys
import ast
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Read credentials directly to avoid encoding issues with dotenv
_env_path = os.path.join(project_root, ".env.supabase")
_creds = {}
with open(_env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            _creds[k.strip()] = v.strip().strip('"').strip("'")

host = _creds.get("DB_HOST", "")
port = _creds.get("DB_PORT", "5432")
name = _creds.get("DB_NAME", "postgres")
user = _creds.get("DB_USER", "postgres")
password = _creds.get("DB_PASSWORD", "")

if "REPLACE_WITH" in host:
    print("ERROR: Fill in .env.supabase with your Supabase credentials first.")
    sys.exit(1)

from urllib.parse import quote_plus

engine = create_engine(
    f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}",
    connect_args={"sslmode": "require", "client_encoding": "utf8"},
)


def safe_parse(x):
    if isinstance(x, list):
        return x
    try:
        return ast.literal_eval(x) if pd.notna(x) else []
    except Exception:
        return []


def create_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id     TEXT,
            track_id        TEXT,
            track_name      TEXT,
            track_duration_ms BIGINT,
            track_popularity  INTEGER,
            track_genres    JSONB,
            album_id        TEXT,
            album_name      TEXT,
            album_release_date DATE,
            album_label     TEXT,
            artist_ids      JSONB,
            artist_names    JSONB,
            release_year    INTEGER,
            track_duration_sec FLOAT,
            PRIMARY KEY (playlist_id, track_id)
        )
    """))


def load(csv_path: str):
    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path)

    # Ensure playlist_id exists
    if "playlist_id" not in df.columns:
        # derive from filename: <playlist_id>_cleaned.csv or fall back
        basename = os.path.basename(csv_path)
        derived = basename.replace("_cleaned.csv", "").replace(".csv", "")
        df["playlist_id"] = derived
        print(f"  playlist_id not in CSV — set to '{derived}'")

    # Parse list columns
    for col in ["artist_names", "track_genres", "artist_ids"]:
        if col in df.columns:
            df[col] = df[col].apply(safe_parse).apply(json.dumps)

    # Derived columns
    if "track_duration_ms" in df.columns and "track_duration_sec" not in df.columns:
        df["track_duration_sec"] = df["track_duration_ms"] / 1000
    if "album_release_date" in df.columns and "release_year" not in df.columns:
        df["release_year"] = pd.to_datetime(df["album_release_date"], errors="coerce").dt.year

    temp = f"temp_migrate_{os.urandom(6).hex()}"

    with engine.begin() as conn:
        create_table(conn)

    df.to_sql(temp, engine, if_exists="replace", index=False)

    upsert_sql = f"""
        INSERT INTO playlist_tracks (
            playlist_id, track_id, track_name, track_duration_ms, track_popularity,
            track_genres, album_id, album_name, album_release_date, album_label,
            artist_ids, artist_names, release_year, track_duration_sec
        )
        SELECT
            playlist_id, track_id, track_name, track_duration_ms, track_popularity,
            CAST(track_genres AS jsonb), album_id, album_name,
            CAST(album_release_date AS DATE), album_label,
            CAST(artist_ids AS jsonb), CAST(artist_names AS jsonb),
            release_year, track_duration_sec
        FROM {temp}
        ON CONFLICT (playlist_id, track_id) DO UPDATE SET
            track_name        = EXCLUDED.track_name,
            track_popularity  = EXCLUDED.track_popularity,
            track_genres      = EXCLUDED.track_genres,
            artist_names      = EXCLUDED.artist_names,
            album_name        = EXCLUDED.album_name,
            album_release_date = EXCLUDED.album_release_date;
        DROP TABLE {temp};
    """

    with engine.begin() as conn:
        conn.execute(text(upsert_sql))

    print(f"  Loaded {len(df)} rows into playlist_tracks.")


if __name__ == "__main__":
    csv_path = os.path.join(project_root, "data", "cleaned_playlist_data.csv")
    load(csv_path)
    print("Migration complete.")
