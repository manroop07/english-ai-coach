from datetime import timedelta

import streamlit as st

from core import database as db
from core import gamification as gm
from core import schedule, vocab
from core.ui import empty_state, hero, ring, section, stat_card, week_bars, esc

KIND_LABELS = {
    "conversation_turn": ("💬", "Conversation practice"),
    "quiz_complete": ("📝", "Vocabulary quiz"),
    "quiz_correct": ("📝", "Vocabulary quiz"),
    "word_of_day": ("🌟", "Word of the day"),
    "flashcard_review": ("🃏", "Flashcards"),
    "targeted_practice": ("🎯", "Targeted practice"),
    "grammar_lesson": ("🧩", "Grammar lesson"),
    "writing": ("✍️", "Writing"),
    "pronunciation": ("🎤", "Pronunciation practice"),
}
# The three habits Phase 1 asks learners to do each day.
DAILY_CHECKLIST = [
    ("word_of_day", "🌟", "Claim today's word of the day", "📚  Vocabulary"),
    ("conversation_turn", "💬", "Practise a short AI conversation", "💬  AI Conversation"),
    ("quiz_complete", "📝", "Finish a vocabulary quiz", "📚  Vocabulary"),
]


def _recommendations(user_id, done_kinds):
    """Rule-based, using only the learner's real data (no invented progress)."""
    recs = []
    q = vocab.quiz_summary(user_id)
    if q["total"] >= 5 and q["accuracy"] is not None and q["accuracy"] < 70:
        recs.append(("🔁", f"Your quiz accuracy is {q['accuracy']}% – revise your difficult words.", "📚  Vocabulary"))
    top = db.query_one(
        """SELECT category, COUNT(*) AS c FROM grammar_mistakes WHERE user_id=?
           GROUP BY category ORDER BY c DESC LIMIT 1""", (user_id,))
    if top and top["c"] >= 2:
        recs.append(("🧩", f"You often slip on “{top['category']}”. Practise it in a conversation.", "💬  AI Conversation"))
    if not recs:
        for kind, icon, text, page in DAILY_CHECKLIST:
            if kind not in done_kinds:
                recs.append((icon, text, page))
    return recs[:3]


def render(profile):
    uid, tz = profile["id"], profile["timezone_offset_min"]
    stats = gm.get_stats(uid, tz)
    done = gm.today_activities(uid, tz)
    done_kinds = {d["kind"] for d in done}
    if "quiz_correct" in done_kinds:
        done_kinds.add("quiz_complete")

    hour_msg = "Ready for today's practice?" if not stats["active_today"] else "Great job showing up today! 🎉"
    hero(f"Hi {profile['name']}! 👋", hour_msg)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("🔥", stats["current_streak"], "Day streak", "#FFE3DC", "flame")
    with c2:
        stat_card("🏆", stats["longest_streak"], "Longest streak", "#FFF3C4")
    with c3:
        stat_card("⚡", stats["total_xp"], "Total XP", "#E9E2FF")
    with c4:
        stat_card("🎓", f"Lv {stats['level']}", f"{profile['level']} learner", "#DDF0FF")

    left, right = st.columns([1.15, 1])
    with left:
        section("🎯 Today's Goals")
        goal = profile["daily_goal_xp"]
        pct = min(100, round(100 * stats["today_xp"] / goal)) if goal else 0
        st.markdown('<div class="ec-card">', unsafe_allow_html=True)
        ring(pct, f"{stats['today_xp']} / {goal} XP today")
        st.markdown("</div>", unsafe_allow_html=True)

        section("✅ Today's checklist")
        for kind, icon, text, page in DAILY_CHECKLIST:
            ok = kind in done_kinds
            st.markdown(
                f'<div class="ec-card" style="padding:.7rem 1rem;margin-bottom:.5rem">'
                f'{"✅" if ok else "⬜"} {icon} <b>{esc(text)}</b>'
                f'<span class="ec-pill" style="float:right;background:{"#E5F8EC" if ok else "#FFF3C4"}">'
                f'{"Done" if ok else "Pending"}</span></div>', unsafe_allow_html=True)

        section("📅 Completed today")
        if done:
            for d in done:
                icon, label = KIND_LABELS.get(d["kind"], ("⭐", d["kind"]))
                st.markdown(f'<div class="ec-good">{icon} {esc(label)} · +{d["xp"]} XP</div>', unsafe_allow_html=True)
        else:
            empty_state("🌱", "Nothing completed yet today. Pick an activity to get started!")

    with right:
        section("▶️ Continue Learning")
        recs = _recommendations(uid, done_kinds)
        for i, (icon, text, page) in enumerate(recs):
            st.markdown(f'<div class="ec-tip">{icon} {esc(text)}</div>', unsafe_allow_html=True)
            if st.button(f"Go to {page.split('  ')[1]}", key=f"rec_{i}", type="secondary"):
                st.session_state["goto"] = page
                st.rerun()
        if not recs:
            empty_state("🎉", "You have finished today's checklist. Amazing!")

        section("🗓️ Upcoming")
        today_d = gm.local_today(tz)
        upcoming = [t for t in schedule.tasks_between(uid, today_d, today_d + timedelta(days=3))
                    if t["status"] == "pending"][:4]
        if upcoming:
            for t in upcoming:
                when = "Today" if t["scheduled_date"] == today_d.isoformat() else t["scheduled_date"]
                st.markdown(f'<div class="ec-tip">⏰ <b>{esc(when)} {esc(t["scheduled_time"])}</b> · {esc(t["title"])}</div>',
                            unsafe_allow_html=True)
        else:
            empty_state("📅", "No upcoming activities. Plan some in My Schedule!")
            if st.button("Open My Schedule", key="dash_sched", type="secondary"):
                st.session_state["goto"] = "🗓️  My Schedule"
                st.rerun()

        section("📊 This week (XP per day)")
        if sum(d["xp"] for d in stats["week"]) == 0:
            empty_state("📉", "No activity this week yet. Your chart will appear after your first lesson.")
        else:
            week_bars(stats["week"])

        c5, c6 = st.columns(2)
        with c5:
            stat_card("📖", stats["words_learned"], "Words learned", "#E0F7EC")
        with c6:
            q = vocab.quiz_summary(uid)
            stat_card("🎯", f"{q['accuracy']}%" if q["accuracy"] is not None else "–", "Quiz accuracy", "#FFE9D6")
