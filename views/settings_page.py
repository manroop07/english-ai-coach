import streamlit as st

from config import GEMINI_MODEL
from core import ai, auth
from core.ui import hero, section


def render(profile):
    hero("Settings", "Account security and AI connection")

    section("🤖 AI connection")
    if ai.is_configured():
        st.success(f"Gemini is connected (model: {GEMINI_MODEL}).")
    else:
        st.error("No Gemini API key found. Add GEMINI_API_KEY to your .env file and restart the app.")
    if st.button("Test AI connection", type="secondary"):
        try:
            with st.spinner("Contacting Gemini…"):
                reply = ai.generate_text("Reply with the single word: ready", temperature=0)
            st.success(f"Gemini answered: {reply[:60]}")
        except ai.AIError as e:
            st.error(str(e))

    section("🔒 Change password")
    with st.form("pw_form", clear_on_submit=True):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password (min. 8 characters)", type="password")
        if st.form_submit_button("Update password"):
            err = auth.change_password(profile["id"], old, new)
            st.error(err) if err else st.success("Password updated.")
