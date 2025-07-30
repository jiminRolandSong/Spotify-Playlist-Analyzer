from unittest import result
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Playlist
import os
import sys
import pandas as pd
import sqlite3
import ast
from django.conf import settings
from sqlalchemy import create_engine
from django.contrib.auth.decorators import login_required

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)


from scripts.extract import spotify_api_setup, extract_playlist_tracks
from scripts.transform import transform_playlist_df

SQLITE_DB_FILE = os.path.join(settings.BASE_DIR, "webData", "playlist_data.db")
SQLITE_ENGINE = create_engine(f"sqlite:///{SQLITE_DB_FILE}")

def load_to_sqlite(df, table_name="playlist_tracks"):

    def safe_parse(x):
        if isinstance(x, list):
            return x
        try:
            import ast
            return ast.literal_eval(x)
        except:
            return []

    df["artist_names"] = df["artist_names"].apply(safe_parse)
    df["track_genres"] = df["track_genres"].apply(safe_parse)
    df["artist_ids"] = df["artist_ids"].apply(safe_parse)

   
    df["artist_names"] = df["artist_names"].apply(lambda x: ", ".join(x))
    df["track_genres"] = df["track_genres"].apply(lambda x: ", ".join(x))
    df["artist_ids"] = df["artist_ids"].apply(lambda x: ", ".join(x))

    conn = sqlite3.connect(SQLITE_DB_FILE)
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()


def index(request):
    return render(request, 'dashboard/index.html')

def analyze_playlist(request):
    if request.method == 'POST':
        playlist_url = request.POST.get('url')
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        
        # Extract
        sp = spotify_api_setup()
        raw_df, metadata = extract_playlist_tracks(sp, playlist_id)
        
        # Transform
        clean_df = transform_playlist_df(raw_df)
        clean_df["source_playlist_id"] = playlist_id
        clean_df["playlist_name"] = metadata["name"]
        clean_df["playlist_owner"] = metadata["owner"]
        
        if request.user.is_authenticated:
            clean_df["user_id"] = request.user.id
        else:
            clean_df["user_id"] = None
    

        print("--- Debugging clean_df before load ---")
        print(clean_df["artist_names"].head())
        print(clean_df["artist_names"].apply(type).value_counts())
        print(clean_df["artist_names"].apply(lambda x: [type(item) for item in x if not isinstance(item, str)]).explode().value_counts())

        print(clean_df["track_genres"].head())
        print(clean_df["track_genres"].apply(type).value_counts())
        print(clean_df["track_genres"].apply(lambda x: [type(item) for item in x if not isinstance(item, str)]).explode().value_counts())

        print(clean_df["artist_ids"].head())
        print(clean_df["artist_ids"].apply(type).value_counts())
        print(clean_df["artist_ids"].apply(lambda x: [type(item) for item in x if not isinstance(item, str)]).explode().value_counts())
        
       
        # Save locally
        os.makedirs(os.path.join(settings.BASE_DIR, "webData"), exist_ok=True) # Ensure path is absolute
        clean_df.to_csv(os.path.join(settings.BASE_DIR, f"webData/{playlist_id}_cleaned.csv"), index=False) # Ensure path is absolute


        # Load to SQLite
        load_to_sqlite(clean_df, table_name="web_playlist_tracks")
        
        if request.user.is_authenticated:
            # Save to user's playlist model
            from .models import Playlist
            playlist, created = Playlist.objects.get_or_create(
                user=request.user,
                playlist_id=playlist_id,
                defaults={
                    'playlist_url': playlist_url,
                    'playlist_name': metadata["name"],
                    'playlist_owner': metadata["owner"],
                    'playlist_image': metadata.get("image", ""),
                    'playlist_description': metadata.get("description", "")
                }
            )
            if not created:
                # Update existing playlist
                playlist.playlist_url = playlist_url
                playlist.playlist_name = metadata["name"]
                playlist.playlist_owner = metadata["owner"]
                playlist.save()

        return redirect('dashboard:dashboard', playlist_id=playlist_id)
    return HttpResponse("invalid method", status=405)

from sqlalchemy import create_engine
from dotenv import load_dotenv

@login_required
def user_playlists(request):
    playlists = Playlist.objects.filter(user=request.user)
    return render(request, "dashboard/user_playlists.html", {"playlists": playlists})
    
# DASHBOARD

def dashboard(request, playlist_id):
    try:
        with SQLITE_ENGINE.connect() as connection: #Get a connection from the engine
            from sqlalchemy import text # Import text from sqlalchemy for parameterized queries
            sql_query = text("""
                SELECT * FROM web_playlist_tracks 
                WHERE source_playlist_id = :playlist_id AND user_id = :user_id
            """)
            
            result = connection.execute(sql_query, {
                "playlist_id": playlist_id,
                "user_id": request.user.id
            })
            
            
            df = pd.DataFrame(result.fetchall(), columns=result.keys()) #Create DataFrame from fetched results

        def parse_str_to_list(x):
            if isinstance(x, str):
                return [item.strip() for item in x.split(',') if item.strip()] # Split by comma, strip spaces, remove empty strings
            return [] # Return empty list if not a string (e.g., NaN)
        
        df["artist_names"] = df["artist_names"].apply(parse_str_to_list)
        df["track_genres"] = df["track_genres"].apply(parse_str_to_list)
        df["artist_ids"] = df["artist_ids"].apply(parse_str_to_list)

        top_artists = (
            # Flatten the lists of values
            df.explode("artist_names")["artist_names"]
            .value_counts()
            .head(10)
            .to_dict()
        )
        
        top_genres = (
            df.explode("track_genres")["track_genres"]
            .value_counts()
            .head(10)
            .to_dict()
        )
        
        track_table = df[["track_name", "artist_names", "album_name", "track_popularity", "track_duration_sec", "track_genres"]].to_dict(orient="records")
        
        # Metadata from the first row
        playlist_name = df["playlist_name"].iloc[0] if "playlist_name" in df else ""
        playlist_owner = df["playlist_owner"].iloc[0] if "playlist_owner" in df else ""
        
        context = {
            "top_artists": top_artists,
            "top_genres": top_genres,
            "track_count": len(df),
            "playlist_name": playlist_name,
            "playlist_owner": playlist_owner,
            "track_table": track_table
        }
        
        return render(request, "dashboard/dashboard.html", context)
    
    except Exception as e:
        import traceback
        return HttpResponse(f"Error: {str(e)}<br>{traceback.format_exc()}")

from django.http import JsonResponse

def debug_playlist_ids(request):
    try:
        with SQLITE_ENGINE.connect() as connection:
            from sqlalchemy import text
            query = text("SELECT DISTINCT source_playlist_id FROM web_playlist_tracks")
            result = connection.execute(query)
            ids = [row[0] for row in result.fetchall()]
        return JsonResponse({"playlist_ids": ids})
    except Exception as e:
        import traceback
        return HttpResponse(f"Error: {str(e)}<br>{traceback.format_exc()}")
