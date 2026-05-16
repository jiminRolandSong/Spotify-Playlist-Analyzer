import streamlit as st
import pandas as pd
import logging
from app.db import save_tracks_to_db
from app.spotify_client import get_spotify, parse_playlist_id, fetch_playlist_tracks
from app.charts import top_artists_chart, popularity_histogram

logger = logging.getLogger(__name__)


def render(user_id: str):
    st.title("Analyze a Spotify Playlist")
    st.markdown("Paste a Spotify playlist URL or ID to fetch, save, and explore its tracks.")

    url_input = st.text_input(
        "Spotify Playlist URL or ID",
        placeholder="https://open.spotify.com/playlist/...",
    )
    save_to_db = st.checkbox("Save to my dashboard", value=True)

    if not (st.button("Analyze", type="primary") and url_input):
        return

    playlist_id = parse_playlist_id(url_input)

    with st.spinner("Fetching playlist from Spotify — this may take a moment while we enrich genre data..."):
        try:
            sp = get_spotify()
            info, rows = fetch_playlist_tracks(sp, playlist_id)
        except Exception:
            logger.exception("Failed to fetch playlist %s", playlist_id)
            st.error("Could not fetch this playlist. Please check that it is public and the URL is valid.")
            return

    df = pd.DataFrame(rows)

    if df.empty:
        st.warning("No tracks found in this playlist.")
        return

    if save_to_db:
        try:
            save_tracks_to_db(df, playlist_id, user_id)
            st.success(f"Saved {len(df)} tracks to your dashboard.")
        except Exception:
            logger.exception("Failed to save tracks for playlist %s", playlist_id)
            st.warning("Tracks fetched but could not be saved to the database. Try again later.")

    # ── Playlist header ───────────────────────────────────────────────────────
    images = info.get("images", [])
    img_url = images[0]["url"] if images else None
    col1, col2 = st.columns([1, 3])
    with col1:
        if img_url:
            st.image(img_url, width=180)
    with col2:
        st.subheader(info.get("name", ""))
        st.caption(f"Owner: {info['owner']['display_name']}  •  {len(df)} tracks")
        desc = info.get("description", "")
        if desc:
            st.markdown(desc, unsafe_allow_html=True)

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tracks", len(df))
    c2.metric("Avg Popularity", f"{df['track_popularity'].mean():.1f}")
    c3.metric("Avg Duration (min)", f"{(df['track_duration_ms'] / 60000).mean():.2f}")

    # ── Track table ───────────────────────────────────────────────────────────
    display_df = df[["track_name", "artist_names", "album_name", "album_release_date", "track_popularity", "track_duration_ms"]].copy()
    display_df["artist_names"] = display_df["artist_names"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else x
    )
    display_df["duration_min"] = (display_df["track_duration_ms"] / 60000).round(2)
    display_df = display_df.drop(columns=["track_duration_ms"])

    st.subheader("Track List")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.subheader("Top Artists")
    st.plotly_chart(top_artists_chart(df), use_container_width=True)

    st.subheader("Popularity Distribution")
    st.plotly_chart(popularity_histogram(df), use_container_width=True)
