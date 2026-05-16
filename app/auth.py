import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["anon_key"])


def auth_page():
    st.title("🎵 Spotify Playlist Analyzer")
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary", key="login_btn"):
            try:
                res = get_supabase().auth.sign_in_with_password({"email": email, "password": password})
                st.session_state["user"] = res.user
                st.session_state["access_token"] = res.session.access_token
                st.rerun()
            except Exception:
                st.error("Login failed. Please check your email and password.")

    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password (min 6 chars)", type="password", key="signup_password")
        if st.button("Create Account", type="primary", key="signup_btn"):
            try:
                res = get_supabase().auth.sign_up({"email": email, "password": password})
                if res.user and res.session:
                    st.session_state["user"] = res.user
                    st.session_state["access_token"] = res.session.access_token
                    st.rerun()
                else:
                    st.error("Sign up failed. Please try again.")
            except Exception:
                st.error("Sign up failed. Please try a different email or password.")


def logout():
    get_supabase().auth.sign_out()
    st.session_state.pop("user", None)
    st.session_state.pop("access_token", None)
    st.rerun()
