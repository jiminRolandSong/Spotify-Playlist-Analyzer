import pandas as pd
import psycopg2 
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# SQLAlchemy engine
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

# Load CSV
df = pd.read_csv("data/cleaned_playlist_data.csv")

# Load to PostgreSQL
with engine.begin() as connection:
    df.to_sql("playlist_tracks", con=connection, if_exists="replace", index=False)

