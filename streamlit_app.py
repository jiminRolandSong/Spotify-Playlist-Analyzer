import streamlit as st
from app.auth import auth_page, logout
from app.pages import analyze, dashboard, pipeline

st.set_page_config(
    page_title="Spotify Playlist Analyzer",
    page_icon="🎵",
    layout="wide",
)

if "user" not in st.session_state:
    auth_page()
    st.stop()

user = st.session_state["user"]
user_id = user.id

st.sidebar.title("🎵 Playlist Analyzer")
st.sidebar.caption(f"Logged in as {user.email}")
page = st.sidebar.radio("Navigate", ["Analyze Playlist", "My Dashboard", "Data Pipeline"])
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    logout()

if page == "Analyze Playlist":
    analyze.render(user_id)
elif page == "My Dashboard":
    dashboard.render(user_id)
elif page == "Data Pipeline":
    pipeline.render()
