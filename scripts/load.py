import pandas as pd
import psycopg2 
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
import json

env_mode = os.getenv("ENV_MODE", "local")  # 기본값은 local

if env_mode == "docker":
    dotenv_path = ".env.docker"
else:
    dotenv_path = ".env.local"

load_dotenv(dotenv_path=dotenv_path)

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

print(f"🔧 Loaded config from: {dotenv_path}")
print(f"📡 DB_HOST = {db_host}")



# SQLAlchemy engine
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

import ast
print(f"DB_HOST: {os.getenv('DB_HOST')}")

def safe_parse(x):
    if isinstance(x, list):
        return x
    try:
        return ast.literal_eval(x) if pd.notna(x) else []
    except Exception:
        return []


# Load to PostgreSQL

def load_to_postgreSQL(df, table_name="playlist_tracks"):
    
    if df.empty:
        print("DataFrame is empty. Skipping database load.")
        return
    
    df["artist_names"] = df["artist_names"].apply(safe_parse).apply(json.dumps)
    df["track_genres"] = df["track_genres"].apply(safe_parse).apply(json.dumps)
    df["artist_ids"] = df["artist_ids"].apply(safe_parse).apply(json.dumps)
    
    temp_table_name = f'temp_{table_name}_{os.urandom(8).hex()}'
    
    try:
         # Step 1: Load data into a temporary table
        df.to_sql(temp_table_name, engine, if_exists='replace', index=False, dtype={
            'track_genres': TEXT,
            'artist_ids': TEXT,
            'artist_names': TEXT,
        })
        
        # Step 2: Execute the UPSERT query
        # This query will insert rows from the temp table into the main table.
        # If a conflict occurs on (playlist_id, track_id), it updates the existing row.
        upsert_query = f"""
        INSERT INTO {table_name} (
            playlist_id, track_id, track_name, track_duration_ms, track_popularity, 
            track_genres, album_id, album_name, album_release_date, album_label,
            artist_ids, artist_names
        )
        SELECT
            playlist_id, track_id, track_name, track_duration_ms, track_popularity, 
            CAST(track_genres AS jsonb), album_id, album_name, CAST(album_release_date AS DATE), album_label,
            CAST(artist_ids AS jsonb), CAST(artist_names AS jsonb)
        FROM {temp_table_name}
        ON CONFLICT (playlist_id, track_id) DO UPDATE SET
            track_name = EXCLUDED.track_name,
            track_duration_ms = EXCLUDED.track_duration_ms,
            track_popularity = EXCLUDED.track_popularity,
            track_genres = EXCLUDED.track_genres,
            album_id = EXCLUDED.album_id,
            album_name = EXCLUDED.album_name,
            album_release_date = EXCLUDED.album_release_date,
            album_label = EXCLUDED.album_label,
            artist_ids = EXCLUDED.artist_ids,
            artist_names = EXCLUDED.artist_names;
        -- Clean up the temporary table
        DROP TABLE {temp_table_name};
        """
        with engine.begin() as connection:
            connection.execute(text(upsert_query))
    except Exception as e:
        print(f"Error during UPSERT operation: {e}")
    
     
if __name__=="__main__":
    df = pd.read_csv("data/cleaned_playlist_data.csv")
    df['playlist_id'] = 1
    load_to_postgreSQL(df)
    print("Data loaded to PostgreSQL successfully.")