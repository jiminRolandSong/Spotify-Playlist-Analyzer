import spotipy
import os
import json
from datetime import datetime
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import pandas as pd
import time

def spotify_api_setup():
    load_dotenv()
    #Authentication
    client_id = os.getenv('client_id')
    client_secret = os.getenv('client_secret')
    credentials = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(client_credentials_manager=credentials)
    return sp


def extract_playlist_tracks(sp, playlist_id):
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
    
    return pd.DataFrame(all_tracks)



if __name__ == "__main__":
    playlist_url = input("Enter Spotify Playlist URL or ID: ").strip()
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    print(f"Extracting playlist ID: {playlist_id}")
    
    sp = spotify_api_setup()
    print("Extracting playlist tracks...")
    df = extract_playlist_tracks(sp, playlist_id)
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/raw_playlist_data.csv", index=False)
    print("Data saved to data/raw_playlist_data.csv")