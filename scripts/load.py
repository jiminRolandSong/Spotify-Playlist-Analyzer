import pandas as pd
import psycopg2 
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import ARRAY, TEXT

load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# SQLAlchemy engine
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

import ast

def safe_parse(x):
    if isinstance(x, list):
        return x
    try:
        return ast.literal_eval(x) if pd.notna(x) else []
    except Exception:
        return []

# Load to PostgreSQL

def load_to_postgreSQL(df, table_name="playlist_tracks"):
    df["artist_names"] = df["artist_names"].apply(safe_parse)
    df["track_genres"] = df["track_genres"].apply(safe_parse)
    df["artist_ids"] = df["artist_ids"].apply(safe_parse)

    with engine.begin() as connection:
        df.to_sql(table_name, con=connection, if_exists="replace", index=False,  dtype={
            "artist_names": ARRAY(TEXT),
            "track_genres": ARRAY(TEXT),
            "artist_ids": ARRAY(TEXT),
        })

if __name__=="__main__":
    df = pd.read_csv("data/cleaned_playlist_data.csv")
    load_to_postgreSQL(df)