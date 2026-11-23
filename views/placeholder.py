import streamlit as st

from core.ui import hero, empty_state

PHASES = {
    2: "Phase 2 – study schedule, daily goals, reminders",
    3: "Phase 3 – analytics, Plotly charts, weekly reports and AI recommendations",
    4: "Phase 4 – grammar lessons, writing feedback and speaking practice",
    5: "Phase 5 – achievements, challenges, badges and leaderboard",
}


def render(title, icon, phase):
    hero(title, "Coming in a later phase")
    empty_state(icon, f"{title} is planned for {PHASES[phase]}. Nothing here is faked – it will appear once it really works.")
