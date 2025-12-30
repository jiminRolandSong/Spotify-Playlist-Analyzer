import spotipy
import os
import json
from datetime import datetime
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import pandas as pd
import time

from dotenv import load_dotenv
load_dotenv()

# venv\scripts\activate


def spotify_api_setup():
    # Get the project root directory (parent of 'scripts' directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    env_mode = os.getenv("ENV_MODE", "local")
    if env_mode == "docker":
        dotenv_path = os.path.join(project_root, ".env.docker")
    else:
        dotenv_path = os.path.join(project_root, ".env.local")

    print(f"Debug - Loading env from: {dotenv_path}")
    print(f"Debug - File exists: {os.path.exists(dotenv_path)}")

    load_dotenv(dotenv_path=dotenv_path, override=True)
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    print(f"Debug - client_id: {client_id}")
    print(f"Debug - client_secret: {client_secret}")

    credentials = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(client_credentials_manager=credentials)
    return sp


def extract_playlist_tracks(sp, playlist_id):
    playlist_info = sp.playlist(playlist_id)
    playlist_metadata = {
        "name": playlist_info.get("name", ""),
        "owner": playlist_info.get("owner", {}).get("display_name", ""),
    }
    all_tracks = []
    results = sp.playlist_items(playlist_id, additional_types=['track'], limit=100)
    
    while results:
        for item in results['items']:
            track = item['track']
            if not track:
                continue
            album = track['album']
            artists = track['artists']
            
            artist_names = [a['name'] for a in artists]
            artist_ids = [a['id'] for a in artists]
            
            genre_set = set()
            for aid in artist_ids:
                try:
                    artist_info = sp.artist(aid)
                    genres = artist_info.get("genres", [])
                    genre_set.update(genres)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Failed to fetch genres for artist ID {aid}")
            
            all_tracks.append({
                "track_id": track['id'],
                "track_name": track['name'],
                "track_duration_ms": track['duration_ms'],
                "track_popularity": track.get('popularity', None),
                
                "track_genres": list(genre_set),
                
                "album_id": album['id'],
                "album_name": album['name'],
                "album_release_date": album.get('release_date'),
                "album_label": album.get('label', None),
                
                "artist_ids": artist_ids,
                "artist_names": artist_names,
            })
        if results['next']:
            results = sp.next(results)
        else:
            break
    
    return pd.DataFrame(all_tracks), playlist_metadata

def extract_data():
    playlist_id = "2wazkzhuzpipWcVKjOa7Vg" 
    sp = spotify_api_setup()
    df_tracks, playlist_meta = extract_playlist_tracks(sp, playlist_id)
    os.makedirs("/opt/airflow/data", exist_ok=True)
    
    df_tracks.to_csv("data/raw_playlist_data.csv", index=False)
    df_tracks.to_csv("/opt/airflow/data/raw_playlist_data.csv", index=False)
    print("[Extract] Data saved to /opt/airflow/data/raw_playlist_data.csv")

if __name__ == "__main__":
    extract_data()