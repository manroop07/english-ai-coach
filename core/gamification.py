"""XP, learner levels and streaks. XP is only ever added through log_activity()."""
from datetime import datetime, timedelta, timezone

import streamlit as st

from config import ACTIVE_GAP_CAP_SEC, DEFAULT_ACTIVITY_SEC, LEARNER_LEVEL_STEP
from core import database as db
from core import achievements, schedule


def local_now(tz_offset_min: int):
    return datetime.now(timezone.utc) + timedelta(minutes=tz_offset_min)


def local_today(tz_offset_min: int):
    return local_now(tz_offset_min).date()


def estimate_duration(user_id, kind):
    """Estimated active seconds for an action that was not timed directly.
    Uses the gap since the learner's previous action if it is short enough (they were
    clearly still studying), otherwise a small per-activity default."""
    default = DEFAULT_ACTIVITY_SEC.get(kind, 30)
    last = db.query_one(
        "SELECT CAST((julianday('now') - julianday(created_at)) * 86400 AS INTEGER) AS gap "
        "FROM activities WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    if last and last["gap"] is not None and 0 < last["gap"] <= ACTIVE_GAP_CAP_SEC:
        return int(last["gap"])
    return default


def log_activity(user_id, kind, xp, tz_offset_min, duration_sec=0, detail=""):
    """Record a genuine learning event, add XP and update the streak.
    duration_sec: pass a measured value when you have one; otherwise it is estimated.
    Returns a dict describing what changed (for toasts in the UI)."""
    today = local_today(tz_offset_min)
    today_s = today.isoformat()
    if duration_sec <= 0:
        duration_sec = estimate_duration(user_id, kind)
    duration_sec = min(int(duration_sec), 3600)
    db.execute(
        """INSERT INTO activities (user_id, kind, xp, duration_sec, detail, local_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, kind, xp, duration_sec, detail[:300], today_s),
    )
    old_xp = db.query_one("SELECT total_xp FROM progress WHERE user_id = ?", (user_id,))["total_xp"]
    db.execute("UPDATE progress SET total_xp = total_xp + ? WHERE user_id = ?", (xp, user_id))

    s = db.query_one("SELECT * FROM streaks WHERE user_id = ?", (user_id,))
    last = s["last_active_date"]
    cur = s["current_streak"]
    streak_increased = False
    if last != today_s:
        yesterday = (today - timedelta(days=1)).isoformat()
        cur = cur + 1 if last == yesterday else 1
        streak_increased = True
    longest = max(s["longest_streak"], cur)
    db.execute(
        "UPDATE streaks SET current_streak=?, longest_streak=?, last_active_date=? WHERE user_id=?",
        (cur, longest, today_s, user_id),
    )
    completed_tasks = schedule.auto_complete(user_id, kind, today_s)
    new_badges = achievements.check_and_award(user_id)
    if new_badges:  # app.py shows these as toasts on the next run
        st.session_state.setdefault("new_badges", []).extend(new_badges)
    return {
        "new_badges": new_badges,
        "tasks_completed": completed_tasks,
        "xp": xp,
        "streak": cur,
        "streak_increased": streak_increased,
        "leveled_up": level_for_xp(old_xp + xp) > level_for_xp(old_xp),
        "new_level": level_for_xp(old_xp + xp),
    }


def level_for_xp(total_xp: int) -> int:
    return total_xp // LEARNER_LEVEL_STEP + 1


def get_stats(user_id: int, tz_offset_min: int) -> dict:
    today = local_today(tz_offset_min)
    today_s = today.isoformat()
    total_xp = db.query_one("SELECT total_xp FROM progress WHERE user_id = ?", (user_id,))["total_xp"]
    s = db.query_one("SELECT * FROM streaks WHERE user_id = ?", (user_id,))

    # A streak is only "alive" if the learner was active today or yesterday.
    current = s["current_streak"]
    if s["last_active_date"] not in (today_s, (today - timedelta(days=1)).isoformat()):
        current = 0

    today_xp = db.query_one(
        "SELECT COALESCE(SUM(xp), 0) AS x FROM activities WHERE user_id=? AND local_date=?",
        (user_id, today_s),
    )["x"]
    words = db.query_one(
        "SELECT COUNT(*) AS c FROM vocabulary WHERE user_id=? AND learned=1", (user_id,)
    )["c"]
    week_start = (today - timedelta(days=6)).isoformat()
    week_rows = db.query_all(
        """SELECT local_date, SUM(xp) AS xp FROM activities
           WHERE user_id=? AND local_date >= ? GROUP BY local_date""",
        (user_id, week_start),
    )
    week_map = {r["local_date"]: r["xp"] for r in week_rows}
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        week.append({"date": d, "label": d.strftime("%a"), "xp": week_map.get(d.isoformat(), 0)})

    return {
        "total_xp": total_xp,
        "level": level_for_xp(total_xp),
        "xp_into_level": total_xp % 100,
        "current_streak": current,
        "longest_streak": s["longest_streak"],
        "today_xp": today_xp,
        "words_learned": words,
        "week": week,
        "active_today": s["last_active_date"] == today_s,
    }


def today_activities(user_id: int, tz_offset_min: int):
    today_s = local_today(tz_offset_min).isoformat()
    return db.query_all(
        """SELECT kind, SUM(xp) AS xp, COUNT(*) AS n FROM activities
           WHERE user_id=? AND local_date=? GROUP BY kind ORDER BY MAX(id) DESC""",
        (user_id, today_s),
    )
