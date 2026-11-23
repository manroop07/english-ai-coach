"""Streaks & Achievements: streak calendar, badges, daily/weekly challenges, leaderboard."""
import calendar
from datetime import timedelta

import streamlit as st

from core import achievements as ach
from core import gamification as gm
from core.ui import empty_state, esc, hero, section, stat_card


def render(profile):
    uid, tz = profile["id"], profile["timezone_offset_min"]
    hero("Streaks & Achievements", "Build habits, unlock badges and climb the leaderboard")
    t1, t2, t3, t4 = st.tabs(["🔥 Streak", "🏅 Badges", "🎯 Challenges", "🏆 Leaderboard"])
    today = gm.local_today(tz)
    with t1:
        _streak(uid, tz, today)
    with t2:
        _badges(uid)
    with t3:
        _challenges(profile, uid, today)
    with t4:
        _leaderboard(profile, uid, today)


# ------------------------------------------------------------------ streak
def _streak(uid, tz, today):
    stats = gm.get_stats(uid, tz)
    c1, c2, c3 = st.columns(3)
    with c1:
        stat_card("🔥", stats["current_streak"], "Current streak (days)", "#FFE3DC", "flame")
    with c2:
        stat_card("🏆", stats["longest_streak"], "Longest streak", "#FFF3C4")
    with c3:
        stat_card("⚡", stats["total_xp"], "Total XP", "#E9E2FF")
    if stats["current_streak"] and not stats["active_today"]:
        st.warning("Your streak is alive – practise today to keep it going!")

    section("🎯 Milestones")
    longest = stats["longest_streak"]
    nxt = ach.next_milestone(longest)
    cols = st.columns(len(ach.STREAK_MILESTONES))
    for col, m in zip(cols, ach.STREAK_MILESTONES):
        got = longest >= m
        col.markdown(f'<div class="ec-card" style="text-align:center;padding:.8rem;{"" if got else "opacity:.55"}">'
                     f'<div style="font-size:1.8rem">{"✅" if got else "🔒"}</div><b>{m} days</b></div>',
                     unsafe_allow_html=True)
    if nxt:
        st.progress(min(longest / nxt, 1.0), text=f"{longest} / {nxt} days – {nxt - longest} to go for your next milestone")
    else:
        st.success("You've reached every streak milestone. Legendary! 👑")

    section("🗓️ Streak calendar")
    ss = st.session_state
    ym = ss.setdefault("cal_ym", (today.year, today.month))
    a, b, c = st.columns([1, 3, 1])
    if a.button("◀", key="cal_prev", type="secondary"):
        y, m = ym
        ss["cal_ym"] = (y - (m == 1), 12 if m == 1 else m - 1)
        st.rerun()
    if c.button("▶", key="cal_next", type="secondary", disabled=ym >= (today.year, today.month)):
        y, m = ym
        ss["cal_ym"] = (y + (m == 12), 1 if m == 12 else m + 1)
        st.rerun()
    year, month = ss["cal_ym"]
    b.markdown(f'<div style="text-align:center;font-weight:900;font-size:1.2rem">{calendar.month_name[month]} {year}</div>',
               unsafe_allow_html=True)
    active = ach.active_dates(uid, year, month)
    cells = "".join(f'<div style="text-align:center;font-weight:800;color:#7A7394;font-size:.8rem">{d}</div>'
                    for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))
    for week in calendar.Calendar(0).monthdayscalendar(year, month):
        for day in week:
            if day == 0:
                cells += "<div></div>"
                continue
            iso = f"{year}-{month:02d}-{day:02d}"
            is_today = iso == today.isoformat()
            future = iso > today.isoformat()
            if iso in active:
                style = "background:linear-gradient(135deg,#7C5CFC,#FF7A6B);color:#fff"
                label = "🔥"
            else:
                style = "background:#F1ECFF;color:#7A7394" + (";opacity:.45" if future else "")
                label = str(day)
            border = ";outline:3px solid #FFD84D" if is_today else ""
            cells += (f'<div title="{iso}" style="{style}{border};border-radius:14px;aspect-ratio:1;display:grid;'
                      f'place-items:center;font-weight:800">{label}</div>')
    st.markdown(f'<div class="ec-card"><div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px">'
                f'{cells}</div></div>', unsafe_allow_html=True)
    st.caption("🔥 = a day with at least one real learning activity (your local date). Yellow outline = today.")


# ------------------------------------------------------------------ badges
def _badges(uid):
    badges = ach.badge_list(uid)
    got = sum(b["unlocked"] for b in badges)
    st.progress(got / len(badges), text=f"{got} of {len(badges)} badges unlocked")
    cols = st.columns(3)
    for i, b in enumerate(badges):
        with cols[i % 3]:
            if b["unlocked"]:
                st.markdown(f'<div class="ec-card pop" style="text-align:center"><div style="font-size:2.4rem">{b["icon"]}</div>'
                            f'<b>{esc(b["name"])}</b><br><small>{esc(b["description"])}</small><br>'
                            f'<span class="ec-pill" style="background:#E5F8EC">Unlocked {esc(b["unlocked_at"])}</span></div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ec-card" style="text-align:center;opacity:.6"><div style="font-size:2.4rem;'
                            f'filter:grayscale(1)">🔒</div><b>{esc(b["name"])}</b><br><small>{esc(b["description"])}</small></div>',
                            unsafe_allow_html=True)


# ------------------------------------------------------------------ challenges
def _challenge_rows(uid, items, today, weekly_goal):
    for c in ach.with_progress(uid, items):
        pct = c["value"] / c["target"] if c["target"] else 0
        st.markdown(f'<div class="ec-card" style="padding:.8rem 1rem;margin-bottom:.3rem">{c["icon"]} <b>{esc(c["title"])}</b>'
                    f'<span class="ec-pill" style="float:right;background:#FFF3C4">+{c["reward"]} XP</span></div>',
                    unsafe_allow_html=True)
        st.progress(min(pct, 1.0), text=f"{c['value']} / {c['target']}")
        if c["claimed"]:
            st.success("Reward claimed ✅")
        elif c["done"]:
            if st.button(f"🎁 Claim +{c['reward']} XP", key=f"claim_{c['key']}"):
                xp, badges = ach.claim(uid, c["key"], today, weekly_goal)
                if xp:
                    st.session_state["pending_toast"] = f"🎁 +{xp} XP challenge reward!"
                    st.session_state["pending_balloons"] = True
                    if badges:
                        st.session_state.setdefault("new_badges", []).extend(badges)
                st.rerun()


def _challenges(profile, uid, today):
    wg = profile["weekly_goal_xp"]
    section("☀️ Daily challenges")
    _challenge_rows(uid, ach.daily_challenges(today), today, wg)
    section("📅 Weekly challenges")
    st.caption("Resets every Monday. Your weekly XP goal is set in My Schedule → Targets.")
    _challenge_rows(uid, ach.weekly_challenges(today, wg), today, wg)


# ------------------------------------------------------------------ leaderboard
def _leaderboard(profile, uid, today):
    visible = st.toggle("Show me on the leaderboard", value=ach.is_visible(uid), key="lb_visible")
    if visible != ach.is_visible(uid):
        ach.set_leaderboard_visibility(uid, visible)
        st.rerun()
    st.caption("Only your name, avatar and XP are shown to other learners – never your email.")
    week_start = today - timedelta(days=today.weekday())
    w, a = st.tabs(["This week", "All time"])
    with w:
        _board(ach.leaderboard(week_start), uid, weekly=True)
    with a:
        _board(ach.leaderboard(), uid, weekly=False)


def _board(rows, uid, weekly):
    if not rows:
        empty_state("🏆", "Nobody is on this board yet. Earn some XP to take the first place!")
        return
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for r in rows:
        me = r["user_id"] == uid
        extra = "" if weekly else f' · Lv {r["level"]}'
        st.markdown(
            f'<div class="ec-card" style="padding:.7rem 1rem;margin-bottom:.4rem;{"border:2px solid #7C5CFC" if me else ""}">'
            f'<b>{medals.get(r["rank"], "#" + str(r["rank"]))}</b> &nbsp; {esc(r["avatar"])} <b>{esc(r["name"])}</b>'
            f'{" (you)" if me else ""}{extra}<span class="ec-pill" style="float:right;background:#E9E2FF">{r["xp"]} XP</span></div>',
            unsafe_allow_html=True)
    if len(rows) == 1:
        st.info("Invite a friend to create an account – the board gets more fun with more learners!")
