import pandas as pd 
import os
import ast 

from dotenv import load_dotenv
load_dotenv(dotenv_path="/opt/airflow/.env")

def transform_playlist_df(df):

    # date
    df['album_release_date'] = pd.to_datetime(df['album_release_date'], errors='coerce')
    df['release_year'] = df['album_release_date'].dt.year

    # duration
    df['track_duration_sec'] = df['track_duration_ms'] / 1000

    # null
    df['track_popularity'] = df['track_popularity'].fillna(0).astype(int)
    df['album_name'] = df['album_name'].fillna("Unknown")

    # string to list '["pop", "dance"]' -> ["pop", "dance"]
    def safe_parse(x):
        if isinstance(x, list):
            return x
        try:
            return ast.literal_eval(x) if pd.notna(x) else []
        except Exception:
            return []

    df["artist_names"] = df["artist_names"].apply(safe_parse)
    df["track_genres"] = df["track_genres"].apply(safe_parse)
    df["artist_ids"] = df["artist_ids"].apply(safe_parse)
    
    return df

def transform_data():
    input_path = "/opt/airflow/data/raw_playlist_data.csv"
    output_csv_path = "/opt/airflow/data/cleaned_playlist_data.csv"
    output_parquet_path = "/opt/airflow/data/cleaned_playlist_data.parquet"

    if not os.path.exists(input_path):
        raise FileNotFoundError("raw_playlist_data.csv not found")

    df = pd.read_csv(input_path)
    df = transform_playlist_df(df)

    df.to_csv(output_csv_path, index=False)
    df.to_parquet(output_parquet_path, index=False)
    print("[Transform] Saved CSV and Parquet versions of cleaned playlist data")

if __name__ == "__main__":
    transform_data()
     
    input_path = "data/raw_playlist_data.csv"
    output_csv_path = "data/cleaned_playlist_data.csv"
    output_parquet_path = "data/cleaned_playlist_data.parquet"
    
    if not os.path.exists(input_path):
        print("FILE NOT FOUND")
    else:
        os.makedirs("data", exist_ok=True)
        df = pd.read_csv(input_path)
        # For PostgreSQL
        df.to_csv("data/cleaned_playlist_data.csv", index=False)
        # For Analytics
        df.to_parquet("data/cleaned_playlist_data.parquet", index=False)
        print("Transform complete: saved to data/cleaned_playlist_data.csv and data/cleaned_playlist_data.parquet")