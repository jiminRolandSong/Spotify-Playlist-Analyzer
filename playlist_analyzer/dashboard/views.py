from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Playlist, Track
from django.conf import settings
from django.contrib.auth.decorators import login_required
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from scripts.extract import spotify_api_setup, extract_playlist_tracks
from scripts.transform import transform_playlist_df

def load_tracks_to_db(df, playlist_obj):
    """
    Load tracks from dataframe to Django ORM using bulk operations
    Uses get_or_create to avoid duplicates (UPSERT-like behavior)
    """
    tracks_to_create = []

    for _, row in df.iterrows():
        # Check if track already exists for this playlist
        existing_track = Track.objects.filter(
            playlist=playlist_obj,
            track_id=row['track_id']
        ).first()

        if existing_track:
            # Update existing track
            existing_track.track_name = row['track_name']
            existing_track.track_duration_ms = int(row['track_duration_ms'])
            existing_track.track_popularity = int(row.get('track_popularity', 0))
            existing_track.track_genres = row['track_genres'] if isinstance(row['track_genres'], list) else []
            existing_track.album_id = row['album_id']
            existing_track.album_name = row['album_name']
            existing_track.album_release_date = row.get('album_release_date')
            existing_track.album_label = row.get('album_label', '')
            existing_track.artist_ids = row['artist_ids'] if isinstance(row['artist_ids'], list) else []
            existing_track.artist_names = row['artist_names'] if isinstance(row['artist_names'], list) else []
            existing_track.save()
        else:
            # Create new track
            tracks_to_create.append(Track(
                playlist=playlist_obj,
                track_id=row['track_id'],
                track_name=row['track_name'],
                track_duration_ms=int(row['track_duration_ms']),
                track_popularity=int(row.get('track_popularity', 0)),
                track_genres=row['track_genres'] if isinstance(row['track_genres'], list) else [],
                album_id=row['album_id'],
                album_name=row['album_name'],
                album_release_date=row.get('album_release_date'),
                album_label=row.get('album_label', ''),
                artist_ids=row['artist_ids'] if isinstance(row['artist_ids'], list) else [],
                artist_names=row['artist_names'] if isinstance(row['artist_names'], list) else []
            ))

    # Bulk create new tracks
    if tracks_to_create:
        Track.objects.bulk_create(tracks_to_create, ignore_conflicts=True)


def index(request):
    return render(request, 'dashboard/index.html')

def analyze_playlist(request):
    if request.method == 'POST':
        playlist_url = request.POST.get('url')
        playlist_id = playlist_url.split("/")[-1].split("?")[0]

        # Check if user is authenticated (required for now)
        if not request.user.is_authenticated:
            return HttpResponse("You must be logged in to analyze playlists", status=403)

        try:
            # Extract from Spotify API
            sp = spotify_api_setup()
            raw_df, metadata = extract_playlist_tracks(sp, playlist_id)

            # Transform the data
            clean_df = transform_playlist_df(raw_df)

            # Get or create playlist object
            playlist_obj, created = Playlist.objects.get_or_create(
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
                # Update existing playlist metadata
                playlist_obj.playlist_url = playlist_url
                playlist_obj.playlist_name = metadata["name"]
                playlist_obj.playlist_owner = metadata["owner"]
                playlist_obj.playlist_image = metadata.get("image", "")
                playlist_obj.playlist_description = metadata.get("description", "")
                playlist_obj.save()

            # Save locally as backup (optional)
            os.makedirs(os.path.join(settings.BASE_DIR, "webData"), exist_ok=True)
            clean_df.to_csv(os.path.join(settings.BASE_DIR, f"webData/{playlist_id}_cleaned.csv"), index=False)

            # Load tracks to database using Django ORM
            load_tracks_to_db(clean_df, playlist_obj)

            return redirect('dashboard:dashboard', playlist_id=playlist_id)

        except Exception as e:
            import traceback
            error_msg = f"Error analyzing playlist: {str(e)}<br><pre>{traceback.format_exc()}</pre>"
            return HttpResponse(error_msg, status=500)

    return HttpResponse("Invalid method", status=405)


@login_required
def user_playlists(request):
    """Display all playlists for the current user"""
    playlists = Playlist.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "dashboard/user_playlists.html", {"playlists": playlists})


def dashboard(request, playlist_id):
    """
    Display dashboard for a specific playlist
    Now uses Django ORM instead of raw SQLite queries
    """
    try:
        # Get the playlist object
        playlist_obj = Playlist.objects.filter(
            user=request.user,
            playlist_id=playlist_id
        ).first()

        if not playlist_obj:
            return HttpResponse("Playlist not found. Please analyze it first.", status=404)

        # Get all tracks for this playlist using Django ORM
        tracks = Track.objects.filter(playlist=playlist_obj).select_related('playlist')

        if not tracks.exists():
            return HttpResponse("No tracks found. Please re-analyze the playlist.", status=404)

        # Calculate top artists
        from collections import Counter
        artist_counter = Counter()
        genre_counter = Counter()

        track_data = []
        for track in tracks:
            # Count artists
            for artist in track.artist_names:
                artist_counter[artist] += 1

            # Count genres
            for genre in track.track_genres:
                genre_counter[genre] += 1

            # Prepare track data for template
            track_data.append({
                'track_name': track.track_name,
                'artist_names': track.artist_names,
                'album_name': track.album_name,
                'track_popularity': track.track_popularity,
                'track_duration_sec': track.track_duration_ms / 1000,
                'track_genres': track.track_genres
            })

        # Get top 10 artists and genres
        top_artists = dict(artist_counter.most_common(10))
        top_genres = dict(genre_counter.most_common(10))

        context = {
            "top_artists": top_artists,
            "top_genres": top_genres,
            "track_count": len(track_data),
            "playlist_name": playlist_obj.playlist_name,
            "playlist_owner": playlist_obj.playlist_owner,
            "track_table": track_data
        }

        return render(request, "dashboard/dashboard.html", context)

    except Exception as e:
        import traceback
        error_msg = f"Error loading dashboard: {str(e)}<br><pre>{traceback.format_exc()}</pre>"
        return HttpResponse(error_msg, status=500)
