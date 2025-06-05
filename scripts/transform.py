import pandas as pd 
import os
import ast 

df = pd.read_csv("data/raw_playlist_data.csv")

# date
df['album_release_date'] = pd.to_datetime(df['album_release_date'], errors='coerce')
df['release_year'] = df['album_release_date'].dt.year

# duration
df['track_duration_sec'] = df['track_duration_ms'] / 1000

# null
df['track_popularity'] = df['track_popularity'].fillna(0).astype(int)
df['album_name'] = df['album_name'].fillna("Unknown")

# string to list '["pop", "dance"]' -> ["pop", "dance"]
df['track_genres'] = df['track_genres'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
df['artist_names'] = df['artist_names'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
df['artist_ids'] = df['artist_ids'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])

os.makedirs("data", exist_ok=True)
# For PostgreSQL
df.to_csv("data/cleaned_playlist_data.csv", index=False)
# For Analytics
df.to_parquet("data/cleaned_playlist_data.parquet", index=False)
print("Transform complete: saved to data/cleaned_playlist_data.csv and data/cleaned_playlist_data.parquet")