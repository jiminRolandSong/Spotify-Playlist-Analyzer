import streamlit as st
import logging
from app.db import query_df
from app.spotify_client import get_spotify, get_playlist_name
from app.charts import top_artists_chart, top_genres_chart, popularity_by_year_chart

logger = logging.getLogger(__name__)


def render(user_id: str):
    st.title("My Dashboard")
    st.markdown("Your saved playlists.")

    try:
        playlists_df = query_df(
            "SELECT DISTINCT playlist_id FROM playlist_tracks WHERE user_id = %s ORDER BY playlist_id",
            params=(user_id,),
        )
    except Exception:
        logger.exception("Failed to load playlists for user %s", user_id)
        st.error("Could not load your playlists. Please try again later.")
        return

    if playlists_df.empty:
        st.info("No playlists saved yet. Go to Analyze Playlist and check 'Save to my dashboard'.")
        return

    sp = get_spotify()
    playlist_options = {
        get_playlist_name(sp, pid): pid
        for pid in playlists_df["playlist_id"].tolist()
    }

    selected_name = st.selectbox("Select Playlist", list(playlist_options.keys()))
    selected_id = playlist_options[selected_name]

    try:
        df = query_df(
            "SELECT * FROM playlist_tracks WHERE user_id = %s AND playlist_id = %s",
            params=(user_id, selected_id),
        )
    except Exception:
        logger.exception("Failed to load tracks for playlist %s", selected_id)
        st.error("Could not load tracks for this playlist. Please try again later.")
        return

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tracks", len(df))
    avg_pop = df["track_popularity"].mean() if "track_popularity" in df.columns else 0
    c2.metric("Avg Popularity", f"{avg_pop:.1f}")
    if "track_duration_sec" in df.columns:
        c3.metric("Avg Duration (min)", f"{df['track_duration_sec'].mean() / 60:.2f}")

    if "artist_names" in df.columns:
        st.subheader("Top 10 Artists")
        st.plotly_chart(top_artists_chart(df), use_container_width=True)

    if "track_genres" in df.columns:
        fig = top_genres_chart(df)
        if fig:
            st.subheader("Top 10 Genres")
            st.plotly_chart(fig, use_container_width=True)

    if "release_year" in df.columns and "track_popularity" in df.columns:
        st.subheader("Avg Popularity by Release Year")
        st.plotly_chart(popularity_by_year_chart(df), use_container_width=True)

    st.subheader("Full Track Table")
    st.dataframe(df, use_container_width=True, hide_index=True)
