import pandas as pd
import plotly.express as px
from collections import Counter


def top_artists_chart(df: pd.DataFrame, n: int = 10):
    counts = Counter()
    for cell in df["artist_names"]:
        names = cell if isinstance(cell, list) else [cell]
        for name in names:
            if name:
                counts[str(name).strip()] += 1
    top = pd.DataFrame(counts.most_common(n), columns=["Artist", "Tracks"])
    return px.bar(top, x="Tracks", y="Artist", orientation="h",
                  color="Tracks", color_continuous_scale="Tealgrn")


def top_genres_chart(df: pd.DataFrame, n: int = 10):
    counts = Counter()
    for cell in df["track_genres"]:
        genres = cell if isinstance(cell, list) else [cell]
        for g in genres:
            if g:
                counts[str(g).strip()] += 1
    top = pd.DataFrame(counts.most_common(n), columns=["Genre", "Count"])
    if top.empty:
        return None
    return px.pie(top, names="Genre", values="Count", hole=0.4)


def popularity_by_year_chart(df: pd.DataFrame):
    year_df = df.dropna(subset=["release_year"]).copy()
    year_df["release_year"] = year_df["release_year"].astype(int)
    year_df = year_df[year_df["release_year"] > 1900]
    year_df = year_df.groupby("release_year")["track_popularity"].mean().reset_index()
    year_df.columns = ["Year", "Avg Popularity"]
    return px.line(year_df, x="Year", y="Avg Popularity", markers=True,
                   color_discrete_sequence=["#1DB954"])


def popularity_histogram(df: pd.DataFrame):
    return px.histogram(df, x="track_popularity", nbins=20,
                        color_discrete_sequence=["#1DB954"])


def mart_bar_chart(mart_df: pd.DataFrame):
    return px.bar(mart_df.head(20), x="avg_popularity", y="album_name", orientation="h",
                  color="avg_popularity", color_continuous_scale="Tealgrn",
                  labels={"avg_popularity": "Avg Popularity", "album_name": "Album"})


def mart_scatter_chart(mart_df: pd.DataFrame):
    return px.scatter(mart_df, x="track_count", y="avg_popularity",
                      hover_name="album_name", size="track_count",
                      color="avg_popularity", color_continuous_scale="Tealgrn",
                      labels={"track_count": "Tracks", "avg_popularity": "Avg Popularity"})


def duration_by_year_chart(mart_df: pd.DataFrame):
    year_dur = mart_df.dropna(subset=["release_year"]).copy()
    year_dur = year_dur[year_dur["release_year"] > 1900]
    year_dur = year_dur.groupby("release_year")["avg_duration_sec"].mean().reset_index()
    year_dur.columns = ["Year", "Avg Duration (sec)"]
    return px.line(year_dur, x="Year", y="Avg Duration (sec)", markers=True,
                   color_discrete_sequence=["#1DB954"])
