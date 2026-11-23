import streamlit as st

from config import LEVELS
from core import auth


def render():
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(
            """<div class="ec-hero pop" style="text-align:center">
            <div style="font-size:3rem">🦉</div><h1>English Coach</h1>
            <p>Your personal AI English tutor</p></div>""",
            unsafe_allow_html=True,
        )
        login_tab, signup_tab = st.tabs(["Log in", "Create account"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", use_container_width=True):
                    uid, err = auth.login(email, password)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["user_id"] = uid
                        st.rerun()

        with signup_tab:
            with st.form("signup_form"):
                name = st.text_input("Your name")
                email = st.text_input("Email", key="su_email")
                password = st.text_input("Password (min. 8 characters)", type="password", key="su_pw")
                level = st.selectbox("Your English level", LEVELS)
                if st.form_submit_button("Create my account", use_container_width=True):
                    uid, err = auth.register(name, email, password, level)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["user_id"] = uid
                        st.rerun()
