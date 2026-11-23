"""Badges, daily/weekly challenges and the leaderboard. Everything is computed from real records.

- Badges are unlocked automatically by check_and_award(), called after every genuine activity.
- Challenges are defined by date (no fake data); progress is counted from the learner's own records
  and the reward is paid only when the learner claims it AND the progress is re-verified.
- Challenge bonus XP goes straight to total XP; it does not create activity rows or touch streaks.
"""
import random
from datetime import date, timedelta

from config import LEARNER_LEVEL_STEP, PRONUNCIATION_PASS
from core import database as db

STREAK_MILESTONES = [7, 15, 30, 100]


# ------------------------------------------------------------------ facts used by badges
def _facts(uid):
    one = lambda sql, p=(): db.query_one(sql, (uid, *p))
    kinds = one("SELECT COUNT(DISTINCT kind) AS c FROM activities WHERE user_id=?")["c"]
    return {
        "any": one("SELECT COUNT(*) AS c FROM activities WHERE user_id=?")["c"],
        "kinds": kinds,
        "longest_streak": one("SELECT longest_streak AS c FROM streaks WHERE user_id=?")["c"],
        "total_xp": one("SELECT total_xp AS c FROM progress WHERE user_id=?")["c"],
        "chat": one("SELECT COUNT(*) AS c FROM activities WHERE user_id=? AND kind='conversation_turn'")["c"],
        "perfect_quiz": one("SELECT COUNT(*) AS c FROM quiz_results WHERE user_id=? AND total>=5 AND correct=total")["c"],
        "words": one("SELECT COUNT(*) AS c FROM vocabulary WHERE user_id=? AND learned=1")["c"],
        "writing": one("SELECT COUNT(*) AS c FROM writing_assessments WHERE user_id=?")["c"],
        "best_writing": one("SELECT COALESCE(MAX(score),0) AS c FROM writing_assessments WHERE user_id=?")["c"],
        "speak_good": one("SELECT COUNT(*) AS c FROM pronunciation_attempts WHERE user_id=? AND score>=?",
                          (PRONUNCIATION_PASS,))["c"],
        "grammar_sets": one("SELECT COUNT(*) AS c FROM exercise_results WHERE user_id=?")["c"],
        "claims": one("SELECT COUNT(*) AS c FROM challenge_claims WHERE user_id=?")["c"],
    }


# code: (icon, name, description, test(facts))
BADGES = {
    "first_steps": ("🌱", "First Steps", "Complete your first learning activity", lambda f: f["any"] >= 1),
    "streak_7": ("🔥", "Week Warrior", "Reach a 7-day streak", lambda f: f["longest_streak"] >= 7),
    "streak_15": ("⚡", "Fortnight Fighter", "Reach a 15-day streak", lambda f: f["longest_streak"] >= 15),
    "streak_30": ("🏅", "Monthly Master", "Reach a 30-day streak", lambda f: f["longest_streak"] >= 30),
    "streak_100": ("👑", "Century Legend", "Reach a 100-day streak", lambda f: f["longest_streak"] >= 100),
    "chat_25": ("💬", "Chatterbox", "Send 25 conversation messages", lambda f: f["chat"] >= 25),
    "chat_100": ("🗣️", "Fluent Talker", "Send 100 conversation messages", lambda f: f["chat"] >= 100),
    "quiz_perfect": ("🎯", "Perfect Score", "Get every answer right in a quiz of 5+ words", lambda f: f["perfect_quiz"] >= 1),
    "words_25": ("📖", "Word Collector", "Learn 25 words", lambda f: f["words"] >= 25),
    "words_100": ("📚", "Walking Dictionary", "Learn 100 words", lambda f: f["words"] >= 100),
    "writer": ("✍️", "Budding Writer", "Get your first writing assessed", lambda f: f["writing"] >= 1),
    "writing_star": ("🌟", "Writing Star", "Score 85+ on a piece of writing", lambda f: f["best_writing"] >= 85),
    "speaker": ("🎤", "Brave Speaker", f"Match a sentence at {PRONUNCIATION_PASS}%+ when speaking", lambda f: f["speak_good"] >= 1),
    "speaker_10": ("🎙️", "Confident Speaker", "10 good speaking attempts", lambda f: f["speak_good"] >= 10),
    "grammar_5": ("🧩", "Grammar Gardener", "Finish 5 grammar or practice sets", lambda f: f["grammar_sets"] >= 5),
    "xp_500": ("💎", "500 XP Club", "Earn 500 XP", lambda f: f["total_xp"] >= 500),
    "xp_2000": ("🚀", "2000 XP Club", "Earn 2000 XP", lambda f: f["total_xp"] >= 2000),
    "level_5": ("🎓", "Level 5 Scholar", "Reach learner level 5", lambda f: f["total_xp"] // LEARNER_LEVEL_STEP + 1 >= 5),
    "challenger": ("🏁", "Challenger", "Claim 5 challenge rewards", lambda f: f["claims"] >= 5),
    "all_rounder": ("🌈", "All-Rounder", "Try 5 different kinds of activity", lambda f: f["kinds"] >= 5),
}


def check_and_award(uid):
    """Unlock every badge whose condition is now true. Returns the newly unlocked badges."""
    have = {r["code"] for r in db.query_all("SELECT code FROM achievements WHERE user_id=?", (uid,))}
    facts = _facts(uid)
    new = []
    for code, (icon, name, desc, test) in BADGES.items():
        if code not in have and test(facts):
            db.execute("INSERT OR IGNORE INTO achievements (user_id, code) VALUES (?, ?)", (uid, code))
            new.append({"code": code, "icon": icon, "name": name})
    return new


def badge_list(uid):
    got = {r["code"]: r["unlocked_at"] for r in db.query_all(
        "SELECT code, unlocked_at FROM achievements WHERE user_id=?", (uid,))}
    return [{"code": c, "icon": b[0], "name": b[1], "description": b[2], "unlocked": c in got,
             "unlocked_at": (got.get(c) or "")[:10]} for c, b in BADGES.items()]


def next_milestone(longest):
    for m in STREAK_MILESTONES:
        if longest < m:
            return m
    return None


# ------------------------------------------------------------------ challenges
def _count_kind(*kinds):
    marks = ",".join("?" * len(kinds))
    return lambda uid, s, e: db.query_one(
        f"SELECT COUNT(*) AS c FROM activities WHERE user_id=? AND kind IN ({marks}) AND local_date BETWEEN ? AND ?",
        (uid, *kinds, s, e))["c"]


def _sum_xp(uid, s, e):
    return db.query_one("SELECT COALESCE(SUM(xp),0) AS c FROM activities WHERE user_id=? AND local_date BETWEEN ? AND ?",
                        (uid, s, e))["c"]


def _active_days(uid, s, e):
    return db.query_one("SELECT COUNT(DISTINCT local_date) AS c FROM activities WHERE user_id=? AND local_date BETWEEN ? AND ?",
                        (uid, s, e))["c"]


def _quiz_questions(uid, s, e):
    return db.query_one("SELECT COALESCE(SUM(total),0) AS c FROM quiz_results WHERE user_id=? AND local_date BETWEEN ? AND ?",
                        (uid, s, e))["c"]


def _distinct_kinds(uid, s, e):
    return db.query_one("SELECT COUNT(DISTINCT kind) AS c FROM activities WHERE user_id=? AND local_date BETWEEN ? AND ?",
                        (uid, s, e))["c"]


# id: (icon, title, target, reward_xp, metric)
DAILY_POOL = {
    "chat5": ("💬", "Send 5 conversation messages", 5, 15, _count_kind("conversation_turn")),
    "quiz1": ("📝", "Complete a vocabulary quiz", 1, 15, _count_kind("quiz_complete")),
    "word1": ("🌟", "Claim today's word of the day", 1, 10, _count_kind("word_of_day")),
    "write1": ("✍️", "Get a piece of writing assessed", 1, 20, _count_kind("writing")),
    "speak2": ("🎤", "Match 2 sentences when speaking", 2, 20, _count_kind("pronunciation")),
    "grammar1": ("🧩", "Finish a grammar lesson or practice set", 1, 15, _count_kind("grammar_lesson", "targeted_practice")),
}


def daily_challenges(today: date):
    """Always 'earn 40 XP' plus 2 others, chosen by the date so everyone gets the same set."""
    rng = random.Random(today.toordinal())
    picks = rng.sample(sorted(DAILY_POOL), 2)
    out = [{"key": f"daily:{today.isoformat()}:xp40", "icon": "⚡", "title": "Earn 40 XP today",
            "target": 40, "reward": 10, "metric": _sum_xp, "start": today, "end": today}]
    for p in picks:
        icon, title, target, reward, metric = DAILY_POOL[p]
        out.append({"key": f"daily:{today.isoformat()}:{p}", "icon": icon, "title": title, "target": target,
                    "reward": reward, "metric": metric, "start": today, "end": today})
    return out


def weekly_challenges(today: date, weekly_goal_xp):
    mon = today - timedelta(days=today.weekday())
    sun = mon + timedelta(days=6)
    k = f"weekly:{mon.isoformat()}"
    defs = [("days5", "📅", "Practise on 5 different days", 5, 50, _active_days),
            ("xpgoal", "🎯", f"Reach your weekly goal of {weekly_goal_xp} XP", weekly_goal_xp, 40, _sum_xp),
            ("quiz20", "📝", "Answer 20 quiz questions", 20, 40, _quiz_questions),
            ("kinds3", "🌈", "Try 3 different kinds of activity", 3, 30, _distinct_kinds)]
    return [{"key": f"{k}:{c}", "icon": i, "title": t, "target": tg, "reward": r, "metric": m,
             "start": mon, "end": sun} for c, i, t, tg, r, m in defs]


def with_progress(uid, challenges):
    claimed = {r["challenge_key"] for r in db.query_all(
        "SELECT challenge_key FROM challenge_claims WHERE user_id=?", (uid,))}
    out = []
    for c in challenges:
        value = c["metric"](uid, c["start"].isoformat(), c["end"].isoformat())
        out.append({**{k: c[k] for k in ("key", "icon", "title", "target", "reward")},
                    "value": min(value, c["target"]), "done": value >= c["target"], "claimed": c["key"] in claimed})
    return out


def claim(uid, key, today: date, weekly_goal_xp):
    """Re-verifies the progress, then pays the reward once. Returns (xp, new_badges) or (0, [])."""
    current = {c["key"]: c for c in with_progress(uid, daily_challenges(today) + weekly_challenges(today, weekly_goal_xp))}
    c = current.get(key)
    if not c or not c["done"] or c["claimed"]:
        return 0, []
    db.execute("INSERT INTO challenge_claims (user_id, challenge_key, xp) VALUES (?,?,?)", (uid, key, c["reward"]))
    db.execute("UPDATE progress SET total_xp = total_xp + ? WHERE user_id=?", (c["reward"], uid))
    return c["reward"], check_and_award(uid)


# ------------------------------------------------------------------ streak calendar
def active_dates(uid, year, month):
    first = date(year, month, 1)
    last = (date(year + (month == 12), month % 12 + 1, 1)) - timedelta(days=1)
    return {r["local_date"] for r in db.query_all(
        "SELECT DISTINCT local_date FROM activities WHERE user_id=? AND local_date BETWEEN ? AND ?",
        (uid, first.isoformat(), last.isoformat()))}


# ------------------------------------------------------------------ leaderboard
def set_leaderboard_visibility(uid, visible):
    db.execute("UPDATE profiles SET show_on_leaderboard=? WHERE user_id=?", (1 if visible else 0, uid))


def is_visible(uid):
    return bool(db.query_one("SELECT show_on_leaderboard AS v FROM profiles WHERE user_id=?", (uid,))["v"])


def leaderboard(week_start: date = None, limit=20):
    """Name, avatar and XP only – never emails. Learners who opted out are left out."""
    if week_start:
        end = week_start + timedelta(days=6)
        rows = db.query_all(
            """SELECT p.user_id, p.name, p.avatar, SUM(a.xp) AS xp FROM activities a
               JOIN profiles p ON p.user_id = a.user_id
               WHERE p.show_on_leaderboard = 1 AND a.local_date BETWEEN ? AND ?
               GROUP BY p.user_id HAVING xp > 0 ORDER BY xp DESC, p.name LIMIT ?""",
            (week_start.isoformat(), end.isoformat(), limit))
    else:
        rows = db.query_all(
            """SELECT p.user_id, p.name, p.avatar, g.total_xp AS xp FROM progress g
               JOIN profiles p ON p.user_id = g.user_id
               WHERE p.show_on_leaderboard = 1 AND g.total_xp > 0 ORDER BY g.total_xp DESC, p.name LIMIT ?""",
            (limit,))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["level"] = r["xp"] // LEARNER_LEVEL_STEP + 1 if not week_start else None
    return rows
