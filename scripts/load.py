import pandas as pd
import psycopg2 
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import ARRAY, TEXT

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
    df["artist_names"] = df["artist_names"].apply(safe_parse)
    df["track_genres"] = df["track_genres"].apply(safe_parse)
    df["artist_ids"] = df["artist_ids"].apply(safe_parse)

    with engine.begin() as connection:
        df.to_sql(table_name, con=connection, if_exists="replace", index=False)

if __name__=="__main__":
    df = pd.read_csv("data/cleaned_playlist_data.csv")
    load_to_postgreSQL(df)