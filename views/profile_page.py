import streamlit as st

from config import AVATARS, LEVELS
from core import auth
from core import gamification as gm
from core.ui import esc, hero, stat_card


def render(profile):
    uid = profile["id"]
    hero("My Profile", "Make English Coach yours")
    stats = gm.get_stats(uid, profile["timezone_offset_min"])

    c1, c2, c3 = st.columns(3)
    with c1:
        stat_card("⚡", stats["total_xp"], "Total XP", "#E9E2FF")
    with c2:
        stat_card("🎓", f"Level {stats['level']}", "Learner level", "#DDF0FF")
    with c3:
        stat_card("🔥", stats["longest_streak"], "Longest streak", "#FFE3DC")

    st.markdown(
        f'<div class="ec-card" style="text-align:center"><div style="font-size:3.4rem">{esc(profile["avatar"])}</div>'
        f'<b style="font-size:1.3rem">{esc(profile["name"])}</b><br>{esc(profile["email"])}</div>',
        unsafe_allow_html=True)

    with st.form("profile_form"):
        name = st.text_input("Name", value=profile["name"])
        avatar = st.radio("Avatar", AVATARS, index=AVATARS.index(profile["avatar"]) if profile["avatar"] in AVATARS else 0,
                          horizontal=True)
        level = st.selectbox("English level", LEVELS, index=LEVELS.index(profile["level"]))
        goal = st.number_input("Daily goal (XP)", min_value=10, max_value=1000, step=10, value=profile["daily_goal_xp"],
                               help="A short conversation turn is 5 XP; a quiz is about 30–50 XP.")
        prefs = st.text_area("Learning preferences (the AI teacher reads this)", value=profile["preferences"],
                             placeholder="e.g. I want to prepare for job interviews. Please explain mistakes slowly.",
                             max_chars=500)
        tz = st.number_input("Your time zone, minutes from UTC", step=30, value=profile["timezone_offset_min"],
                             min_value=-720, max_value=840, help="India is 330. This decides when your day (and streak) rolls over.")
        if st.form_submit_button("Save changes"):
            err = auth.update_profile(uid, name, avatar, level, goal, prefs, tz)
            if err:
                st.error(err)
            else:
                st.session_state["pending_toast"] = "Profile saved ✅"
                st.rerun()
