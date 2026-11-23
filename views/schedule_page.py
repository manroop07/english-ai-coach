from datetime import datetime, timedelta

import streamlit as st

from core import ai, schedule
from core import gamification as gm
from core.schedule import ACTIVITY_TYPES, TYPE_TO_PAGE
from core.ui import empty_state, esc, hero, ring, section


def _t(hhmm):
    return datetime.strptime(hhmm, "%H:%M").time()


def _pill(status, overdue=False):
    if status == "done":
        return '<span class="ec-pill" style="background:#E5F8EC">Done</span>'
    if overdue:
        return '<span class="ec-pill" style="background:#FFE3DC">Missed</span>'
    return '<span class="ec-pill" style="background:#FFF3C4">Pending</span>'


def _task_row(uid, t, today, prefix, overdue=False):
    kind = ACTIVITY_TYPES.get(t["activity_type"], ACTIVITY_TYPES["general"])
    st.markdown(
        f'<div class="ec-card" style="padding:.7rem 1rem;margin-bottom:.3rem">'
        f'<b>{esc(t["scheduled_time"])}</b> · {esc(t["title"])} '
        f'<span style="color:#7A7394">· {esc(kind)} · {t["duration_min"]} min'
        f'{"" if t["scheduled_date"] == today.isoformat() else " · " + esc(t["scheduled_date"])}</span>'
        f'<span style="float:right">{_pill(t["status"], overdue)}</span></div>', unsafe_allow_html=True)

    cols = st.columns(5)
    k = f"{prefix}_{t['id']}"
    page = TYPE_TO_PAGE.get(t["activity_type"])
    if t["status"] == "pending":
        if page and not overdue and cols[0].button("▶ Start", key=f"{k}_go"):
            st.session_state["goto"] = page
            st.rerun()
        if cols[1].button("✅ Done", key=f"{k}_done", type="secondary", help="Marks the task done. No XP is given – XP comes from real practice."):
            schedule.set_status(uid, t["id"], "done")
            st.rerun()
    else:
        if cols[1].button("↩ Undo", key=f"{k}_undo", type="secondary"):
            schedule.set_status(uid, t["id"], "pending")
            st.rerun()
    if overdue:
        if cols[2].button("→ Today", key=f"{k}_rt", type="secondary"):
            schedule.reschedule(uid, t["id"], today)
            st.rerun()
        if cols[3].button("→ Tomorrow", key=f"{k}_rm", type="secondary"):
            schedule.reschedule(uid, t["id"], today + timedelta(days=1))
            st.rerun()
    if cols[4].button("🗑 Delete", key=f"{k}_del", type="secondary"):
        schedule.delete_task(uid, t["id"])
        st.rerun()

    with st.expander("✏️ Edit"):
        with st.form(f"{k}_form"):
            title = st.text_input("Title", value=t["title"])
            types = list(ACTIVITY_TYPES)
            atype = st.selectbox("Type", types, index=types.index(t["activity_type"]) if t["activity_type"] in types else 0,
                                 format_func=ACTIVITY_TYPES.get)
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", value=datetime.strptime(t["scheduled_date"], "%Y-%m-%d").date())
            tm = c2.time_input("Time", value=_t(t["scheduled_time"]))
            dur = c3.number_input("Minutes", 5, 240, t["duration_min"], step=5)
            if st.form_submit_button("Save changes"):
                err = schedule.update_task(uid, t["id"], title, atype, d, tm.strftime("%H:%M"), dur)
                if err:
                    st.error(err)
                else:
                    st.session_state["pending_toast"] = "Task updated ✅"
                    st.rerun()


def render(profile):
    uid, tz = profile["id"], profile["timezone_offset_min"]
    today = gm.local_today(tz)
    hero("My Schedule", "Plan your practice and let reminders keep you on track")

    t_today, t_week, t_plan, t_targets = st.tabs(["📅 Today", "🗓️ Week", "➕ Plan", "🎯 Targets & reminders"])
    with t_today:
        _today_tab(uid, today)
    with t_week:
        _week_tab(uid, today)
    with t_plan:
        _plan_tab(profile, today)
    with t_targets:
        _targets_tab(profile, today)


def _today_tab(uid, today):
    todays = schedule.tasks_between(uid, today, today)
    section(f"Today · {today.strftime('%A, %d %B')}")
    if not todays:
        empty_state("📭", "Nothing planned for today. Add an activity in the Plan tab.")
    for t in todays:
        _task_row(uid, t, today, "td")

    missed = schedule.missed_tasks(uid, today)
    if missed:
        section(f"⚠️ Missed ({len(missed)})")
        st.caption("Move them to today or tomorrow, or open Edit to pick another day.")
        for t in missed[:10]:
            _task_row(uid, t, today, "ms", overdue=True)

    section("Coming up (next 7 days)")
    upcoming = schedule.tasks_between(uid, today + timedelta(days=1), today + timedelta(days=7))
    if not upcoming:
        empty_state("🔭", "No upcoming activities yet.")
    for t in upcoming:
        _task_row(uid, t, today, "up")


def _week_tab(uid, today):
    ss = st.session_state
    ss.setdefault("week_offset", 0)
    a, b, c = st.columns([1, 3, 1])
    if a.button("◀ Previous", key="wk_prev", type="secondary"):
        ss["week_offset"] -= 1
        st.rerun()
    if c.button("Next ▶", key="wk_next", type="secondary"):
        ss["week_offset"] += 1
        st.rerun()
    start, end = schedule.week_bounds(today + timedelta(weeks=ss["week_offset"]))
    b.markdown(f"<h4 style='text-align:center'>{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}</h4>",
               unsafe_allow_html=True)
    if ss["week_offset"] and b.button("Back to this week", key="wk_now", type="secondary"):
        ss["week_offset"] = 0
        st.rerun()

    tasks = schedule.tasks_between(uid, start, end)
    if not tasks:
        empty_state("🗓️", "No activities this week.")
    cols = st.columns(7)
    for i, col in enumerate(cols):
        d = start + timedelta(days=i)
        with col:
            hl = "background:#7C5CFC;color:#fff" if d == today else "background:#fff"
            st.markdown(f'<div class="ec-card" style="{hl};padding:.4rem;text-align:center;margin-bottom:.4rem">'
                        f'<b>{d.strftime("%a")}</b><br>{d.day}</div>', unsafe_allow_html=True)
            for t in [x for x in tasks if x["scheduled_date"] == d.isoformat()]:
                done = t["status"] == "done"
                missed = not done and d < today
                bg = "#E5F8EC" if done else ("#FFE3DC" if missed else "#FFF3C4")
                st.markdown(f'<div style="background:{bg};border-radius:12px;padding:.35rem .5rem;margin-bottom:.35rem;'
                            f'font-size:.78rem"><b>{esc(t["scheduled_time"])}</b><br>{esc(t["title"])}</div>',
                            unsafe_allow_html=True)
    st.caption("🟨 pending · 🟩 done · 🟥 missed")


def _plan_tab(profile, today):
    uid = profile["id"]
    section("Add an activity")
    with st.form("add_task", clear_on_submit=True):
        title = st.text_input("What will you practise?", placeholder="e.g. Practise job interview questions")
        types = list(ACTIVITY_TYPES)
        atype = st.selectbox("Type", types, format_func=ACTIVITY_TYPES.get,
                             help="Conversation, quiz, word of the day and flashcard tasks complete automatically "
                                  "when you really do them.")
        c1, c2, c3 = st.columns(3)
        d = c1.date_input("Date", value=today)
        tm = c2.time_input("Time", value=_t(profile["preferred_time"]))
        dur = c3.number_input("Minutes", 5, 240, 15, step=5)
        repeat = st.checkbox("Repeat every day for the next 7 days")
        if st.form_submit_button("Add to my schedule"):
            err = None
            for i in range(7 if repeat else 1):
                err = schedule.add_task(uid, title, atype, d + timedelta(days=i), tm.strftime("%H:%M"), dur)
                if err:
                    break
            if err:
                st.error(err)
            else:
                st.session_state["pending_toast"] = "Added to your schedule 📅"
                st.rerun()

    section("🤖 Let AI plan my week")
    areas = schedule.weak_areas(uid)
    if areas:
        st.info("Weak areas found from your real practice: " + "; ".join(areas))
    else:
        st.caption("No weak areas detected yet – the plan will use your level and available time.")
    c1, c2 = st.columns(2)
    minutes = c1.slider("Minutes available per day", 10, 120, min(max(profile["daily_minutes"], 10), 120), step=5)
    days = c2.slider("Plan length (days)", 3, 7, 7)
    if st.button("✨ Suggest a plan", key="ai_plan_btn", disabled=not ai.is_configured()):
        try:
            with st.spinner("Your coach is building a plan…"):
                st.session_state["ai_plan"] = schedule.suggest_plan(
                    uid, profile["level"], minutes, days, today, profile["preferred_time"], areas,
                    profile["preferences"])
        except ai.AIError as e:
            st.error(f"😕 {e}")
    if not ai.is_configured():
        st.caption("Add your Gemini key to use this feature.")

    plan = st.session_state.get("ai_plan")
    if plan:
        st.markdown("**Suggested plan – untick anything you don't want:**")
        chosen = []
        for i, p in enumerate(plan):
            label = f"{p['date']} {p['time']} · {p['title']} ({ACTIVITY_TYPES[p['activity_type']]}, {p['duration_min']} min)"
            if st.checkbox(label, value=True, key=f"plan_{i}"):
                chosen.append(p)
        c1, c2 = st.columns(2)
        if c1.button("➕ Add selected to my schedule", key="plan_add"):
            for p in chosen:
                schedule.add_task(uid, p["title"], p["activity_type"], p["date"], p["time"], p["duration_min"])
            st.session_state.pop("ai_plan", None)
            st.session_state["pending_toast"] = f"{len(chosen)} activities added 📅"
            st.rerun()
        if c2.button("Discard", key="plan_discard", type="secondary"):
            st.session_state.pop("ai_plan", None)
            st.rerun()


def _targets_tab(profile, today):
    uid = profile["id"]
    w = schedule.week_summary(uid, today)
    goal = profile["weekly_goal_xp"]
    section("This week")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="ec-card">', unsafe_allow_html=True)
        ring(min(100, round(100 * w["xp"] / goal)) if goal else 0, f"{w['xp']} / {goal} XP this week")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ec-card">', unsafe_allow_html=True)
        pct = round(100 * w["done"] / w["planned"]) if w["planned"] else 0
        ring(pct, f"{w['done']} of {w['planned']} planned tasks done" if w["planned"] else "No tasks planned this week")
        st.markdown("</div>", unsafe_allow_html=True)

    section("Targets & study time")
    with st.form("targets_form"):
        c1, c2, c3 = st.columns(3)
        daily = c1.number_input("Daily goal (XP)", 10, 1000, profile["daily_goal_xp"], step=10)
        weekly = c2.number_input("Weekly goal (XP)", 50, 7000, profile["weekly_goal_xp"], step=50)
        pref = c3.time_input("Preferred study time", value=_t(profile["preferred_time"]))
        mins = st.number_input("Minutes I can study per day", 5, 480, profile["daily_minutes"], step=5)
        if st.form_submit_button("Save targets"):
            from core import auth
            err = schedule.update_planner_settings(uid, weekly, pref.strftime("%H:%M"), mins)
            if not err:
                err = auth.update_profile(uid, profile["name"], profile["avatar"], profile["level"], daily,
                                          profile["preferences"], profile["timezone_offset_min"])
            if err:
                st.error(err)
            else:
                st.session_state["pending_toast"] = "Targets saved 🎯"
                st.rerun()

    section("🔔 Reminders")
    st.write("In-app reminders appear at the top of every page when an activity is due or starting within 30 minutes.")
    # No widget key on purpose: keyed widget state is dropped when you leave this page.
    on = st.toggle("Also send browser notifications (works while this tab is open)",
                   value=st.session_state.get("browser_notif", False))
    st.session_state["browser_notif"] = on
