"""
One-time migration: adds user_id column to playlist_tracks in Supabase.
Run from project root: python scripts/add_user_id_column.py
"""
import os
import sys
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

_creds = {}
with open(os.path.join(project_root, ".env.supabase"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            _creds[k.strip()] = v.strip().strip('"').strip("'")

host = _creds["DB_HOST"]
port = _creds.get("DB_PORT", "6543")
name = _creds.get("DB_NAME", "postgres")
user = _creds["DB_USER"]
password = _creds["DB_PASSWORD"]

engine = create_engine(
    f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}",
    connect_args={"sslmode": "require", "client_encoding": "utf8"},
)

with engine.begin() as conn:
    conn.execute(text("""
        ALTER TABLE playlist_tracks
        ADD COLUMN IF NOT EXISTS user_id TEXT;
    """))
    print("Added user_id column to playlist_tracks.")

    # Fill existing rows with a sentinel so the PK constraint can be applied
    conn.execute(text("""
        UPDATE playlist_tracks SET user_id = 'migrated' WHERE user_id IS NULL;
    """))
    print("Backfilled existing rows with user_id = 'migrated'.")

    conn.execute(text("""
        ALTER TABLE playlist_tracks
        DROP CONSTRAINT IF EXISTS playlist_tracks_pkey;
    """))
    conn.execute(text("""
        ALTER TABLE playlist_tracks
        ADD CONSTRAINT playlist_tracks_pkey
        PRIMARY KEY (user_id, playlist_id, track_id);
    """))
    print("Updated primary key to (user_id, playlist_id, track_id).")

print("Migration complete.")
