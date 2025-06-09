from django.shortcuts import render, redirect
from django.http import HttpResponse
import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from scripts.extract import spotify_api_setup, extract_playlist_tracks
from scripts.transform import transform_playlist_df
from scripts.load import load_to_postgreSQL

# Create your views here.


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
        clean_df["playlist_total_tracks"] = metadata["total_tracks"]
        
        # Save locally
        os.makedirs("webData", exist_ok=True)
        clean_df.to_csv(f"webData/{playlist_id}_cleaned.csv", index=False)
        
        # Load to SQL
        load_to_postgreSQL(clean_df, table_name="web_playlist_tracks")
        
        return redirect('dashboard', playlist_id = playlist_id)
    return HttpResponse("invalid method", status=405)

from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

# DASHBOARD

def dashboard(request, playlist_id):
    try:
        df = pd.read_sql(
            "SELECT * FROM web_playlist_tracks WHERE source_playlist_id = %s",
            engine,
            params=[(playlist_id,)]
        )

        def parse_pg_array(x):
            if isinstance(x, str) and x.startswith('{') and x.endswith('}'):
                return [item.strip().strip('"') for item in x.strip('{}').split(',')]
            return x
        
        df["artist_names"] = df["artist_names"].apply(parse_pg_array)
        df["track_genres"] = df["track_genres"].apply(parse_pg_array)
        df["artist_ids"] = df["artist_ids"].apply(parse_pg_array)


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
        
        # Metadata from the first row
        playlist_name = df["playlist_name"].iloc[0] if "playlist_name" in df else ""
        playlist_owner = df["playlist_owner"].iloc[0] if "playlist_owner" in df else ""
        playlist_total_tracks = df["playlist_total_tracks"].iloc[0] if "playlist_total_tracks" in df else ""
        
        context = {
            "top_artists": top_artists,
            "top_genres": top_genres,
            "track_count": len(df),
            "playlist_name": playlist_name,
            "playlist_owner": playlist_owner,
            "playlist_total_tracks": playlist_total_tracks
        }
        
        return render(request, "dashboard/dashboard.html", context)
    
    except Exception as e:
        import traceback
        return HttpResponse(f"Error: {str(e)}<br>{traceback.format_exc()}")
