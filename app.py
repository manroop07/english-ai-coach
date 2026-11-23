"""English Coach – entry point. Run with:  streamlit run app.py"""
import streamlit as st

from core import auth, database as db
from core.ui import inject_css, esc
from views import (achievements_page, conversation_page, dashboard, grammar_page, login, placeholder, profile_page,
                   progress_page, reminders, schedule_page, settings_page, speaking_page, vocabulary_page)

import os
api_key= st.secrets["GEMINI_API_KEY"]
st.set_page_config(page_title="English Coach", page_icon="🦉", layout="wide")
db.init_db()
inject_css()


NAV = [
    ("🏠  Dashboard", dashboard.render),
    ("💬  AI Conversation", conversation_page.render),
    ("📚  Vocabulary", vocabulary_page.render),
    ("🎤  Speaking Practice", speaking_page.render),
    ("✍️  Grammar & Writing", grammar_page.render),
    ("🗓️  My Schedule", schedule_page.render),
    ("🔥  Streaks & Achievements", achievements_page.render),
    ("📈  My Progress", progress_page.render),
    ("👤  My Profile", profile_page.render),
    ("⚙️  Settings", settings_page.render),
]

user_id = st.session_state.get("user_id")
if not user_id:
    login.render()
    st.stop()

profile = auth.get_profile(user_id)
if not profile:  # account removed or stale session
    st.session_state.clear()
    st.rerun()

with st.sidebar:
    st.markdown(
        f"""<div style="text-align:center;padding:.5rem 0 1rem">
        <div style="font-size:2.6rem">🦉</div>
        <div style="font-size:1.5rem;font-weight:900">English Coach</div>
        <div style="opacity:.85;font-weight:700;font-size:.85rem">Speak. Learn. Shine.</div></div>
        <div style="background:rgba(255,255,255,.15);border-radius:18px;padding:.6rem .9rem;margin-bottom:1rem">
        <span style="font-size:1.6rem">{esc(profile['avatar'])}</span>
        <b style="margin-left:.4rem">{esc(profile['name'])}</b><br>
        <span style="opacity:.85;font-size:.8rem">{esc(profile['level'])} learner</span></div>""",
        unsafe_allow_html=True,
    )
    # Allows other pages to jump somewhere via st.session_state["goto"].
    labels = [n[0] for n in NAV]
    goto = st.session_state.pop("goto", None)
    if goto in labels:
        st.session_state["nav"] = goto
    choice = st.radio("Navigation", labels, key="nav", label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪  Log out"):
        st.session_state.clear()
        st.rerun()

# Messages queued by a page just before st.rerun() are shown here so they are not lost.
if msg := st.session_state.pop("pending_toast", None):
    st.toast(msg)
if st.session_state.pop("pending_balloons", False):
    st.balloons()
for b in st.session_state.pop("new_badges", []):
    st.toast(f"{b['icon']} Badge unlocked: {b['name']}!")
    st.balloons()

reminders.render(profile)
dict(NAV)[choice](profile)
