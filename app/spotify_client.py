import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging

logger = logging.getLogger(__name__)


@st.cache_resource
def get_spotify():
    cfg = st.secrets["spotify"]
    return spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
    ))


def parse_playlist_id(url_or_id: str) -> str:
    return url_or_id.strip().split("/")[-1].split("?")[0]


def _normalize_release_date(release_date: str) -> str:
    if not release_date:
        return release_date
    if len(release_date) == 4:
        return release_date + "-01-01"
    if len(release_date) == 7:
        return release_date + "-01"
    return release_date


def fetch_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> tuple[dict, list]:
    """Returns (playlist_info, list of track dicts)."""
    info = sp.playlist(playlist_id)
    items_result = sp.playlist_items(playlist_id, additional_types=["track"], limit=100)

    rows = []
    artist_genre_cache = {}

    while items_result:
        for item in items_result["items"]:
            track = item.get("track")
            if not track:
                continue
            album = track["album"]
            artists = track["artists"]

            genre_set = set()
            for a in artists:
                aid = a.get("id")
                if not aid:
                    continue
                if aid not in artist_genre_cache:
                    try:
                        artist_genre_cache[aid] = sp.artist(aid).get("genres", [])
                    except Exception:
                        artist_genre_cache[aid] = []
                        logger.warning("Could not fetch genres for artist %s", aid)
                genre_set.update(artist_genre_cache[aid])

            release_date = album.get("release_date", "")
            try:
                release_year = int(str(release_date)[:4]) if release_date else None
            except Exception:
                release_year = None

            rows.append({
                "track_id": track["id"],
                "track_name": track["name"],
                "artist_names": [a["name"] for a in artists],
                "artist_ids": [a.get("id") for a in artists if a.get("id")],
                "album_id": album["id"],
                "album_name": album["name"],
                "album_release_date": _normalize_release_date(release_date),
                "track_popularity": track.get("popularity", 0),
                "track_duration_ms": track["duration_ms"],
                "track_duration_sec": track["duration_ms"] / 1000,
                "track_genres": list(genre_set),
                "release_year": release_year,
            })

        if items_result["next"]:
            items_result = sp.next(items_result)
        else:
            break

    return info, rows


def get_playlist_name(sp: spotipy.Spotify, playlist_id: str) -> str:
    try:
        return sp.playlist(playlist_id, fields="name")["name"]
    except Exception:
        return playlist_id
