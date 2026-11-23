"""Study planner: tasks, targets, reminders and AI-suggested plans.

Honesty rules:
- Tasks whose type matches a real activity (conversation, quiz, word of the day, flashcards)
  complete automatically when the learner genuinely does that activity.
- Marking a task done by hand never awards XP.
"""
from datetime import date, datetime, timedelta

from core import ai
from core import database as db

ACTIVITY_TYPES = {
    "conversation": "💬 AI conversation",
    "vocabulary_quiz": "📝 Vocabulary quiz",
    "word_of_day": "🌟 Word of the day",
    "flashcards": "🃏 Flashcards / revision",
    "grammar": "🧩 Grammar practice",
    "writing": "✍️ Writing",
    "speaking": "🎤 Speaking practice",
    "general": "📌 Other",
}

# Which logged activity completes which task type, and how many are needed that day.
AUTO_COMPLETE = {
    "conversation_turn": ("conversation", 3),   # a real conversation = at least 3 messages
    "quiz_complete": ("vocabulary_quiz", 1),
    "word_of_day": ("word_of_day", 1),
    "flashcard_review": ("flashcards", 1),
    "targeted_practice": ("grammar", 1),
    "grammar_lesson": ("grammar", 1),
    "writing": ("writing", 1),
    "pronunciation": ("speaking", 1),
}

# Where the "Start" button sends the learner.
TYPE_TO_PAGE = {
    "conversation": "💬  AI Conversation",
    "vocabulary_quiz": "📚  Vocabulary",
    "word_of_day": "📚  Vocabulary",
    "flashcards": "📚  Vocabulary",
    "grammar": "✍️  Grammar & Writing",
    "writing": "✍️  Grammar & Writing",
    "speaking": "🎤  Speaking Practice",
}


def _valid_time(t: str) -> bool:
    try:
        datetime.strptime(t, "%H:%M")
        return True
    except (ValueError, TypeError):
        return False


def _validate(title, activity_type, scheduled_date, scheduled_time, duration_min):
    title = (title or "").strip()
    if len(title) < 2:
        return None, "Please give the activity a title (at least 2 characters)."
    if len(title) > 80:
        return None, "Title is too long (max 80 characters)."
    if activity_type not in ACTIVITY_TYPES:
        return None, "Unknown activity type."
    try:
        date.fromisoformat(str(scheduled_date))
    except ValueError:
        return None, "Please choose a valid date."
    if not _valid_time(scheduled_time):
        return None, "Please choose a valid time."
    if not 5 <= int(duration_min) <= 240:
        return None, "Duration must be between 5 and 240 minutes."
    return (title, activity_type, str(scheduled_date), scheduled_time, int(duration_min)), None


def add_task(user_id, title, activity_type, scheduled_date, scheduled_time, duration_min):
    vals, err = _validate(title, activity_type, scheduled_date, scheduled_time, duration_min)
    if err:
        return err
    db.execute(
        """INSERT INTO study_schedule (user_id, title, activity_type, scheduled_date,
           scheduled_time, duration_min) VALUES (?,?,?,?,?,?)""", (user_id, *vals))
    return None


def update_task(user_id, task_id, title, activity_type, scheduled_date, scheduled_time, duration_min):
    vals, err = _validate(title, activity_type, scheduled_date, scheduled_time, duration_min)
    if err:
        return err
    db.execute(
        """UPDATE study_schedule SET title=?, activity_type=?, scheduled_date=?, scheduled_time=?,
           duration_min=? WHERE id=? AND user_id=?""", (*vals, task_id, user_id))
    return None


def delete_task(user_id, task_id):
    db.execute("DELETE FROM study_schedule WHERE id=? AND user_id=?", (task_id, user_id))


def set_status(user_id, task_id, status):
    if status in ("pending", "done"):
        db.execute("UPDATE study_schedule SET status=? WHERE id=? AND user_id=?",
                   (status, task_id, user_id))


def reschedule(user_id, task_id, new_date):
    db.execute("UPDATE study_schedule SET scheduled_date=?, status='pending' WHERE id=? AND user_id=?",
               (str(new_date), task_id, user_id))


def tasks_between(user_id, start: date, end: date):
    return db.query_all(
        """SELECT * FROM study_schedule WHERE user_id=? AND scheduled_date BETWEEN ? AND ?
           ORDER BY scheduled_date, scheduled_time""",
        (user_id, start.isoformat(), end.isoformat()))


def missed_tasks(user_id, today: date):
    return db.query_all(
        """SELECT * FROM study_schedule WHERE user_id=? AND status='pending' AND scheduled_date < ?
           ORDER BY scheduled_date DESC, scheduled_time""", (user_id, today.isoformat()))


def auto_complete(user_id, kind, today_s):
    """Called after a real activity is logged. Returns how many tasks were completed."""
    rule = AUTO_COMPLETE.get(kind)
    if not rule:
        return 0
    task_type, needed = rule
    n = db.query_one(
        "SELECT COUNT(*) AS c FROM activities WHERE user_id=? AND kind=? AND local_date=?",
        (user_id, kind, today_s))["c"]
    if n < needed:
        return 0
    pending = db.query_all(
        """SELECT id FROM study_schedule WHERE user_id=? AND activity_type=? AND scheduled_date=?
           AND status='pending'""", (user_id, task_type, today_s))
    for t in pending:
        db.execute("UPDATE study_schedule SET status='done' WHERE id=? AND user_id=?", (t["id"], user_id))
    return len(pending)


# ---------------- targets ----------------
def update_planner_settings(user_id, weekly_goal_xp, preferred_time, daily_minutes):
    if not 50 <= int(weekly_goal_xp) <= 7000:
        return "Weekly goal must be between 50 and 7000 XP."
    if not _valid_time(preferred_time):
        return "Please choose a valid study time."
    if not 5 <= int(daily_minutes) <= 480:
        return "Daily study minutes must be between 5 and 480."
    db.execute("UPDATE profiles SET weekly_goal_xp=?, preferred_time=?, daily_minutes=? WHERE user_id=?",
               (int(weekly_goal_xp), preferred_time, int(daily_minutes), user_id))
    return None


def week_bounds(today: date):
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def week_summary(user_id, today: date):
    start, end = week_bounds(today)
    xp = db.query_one(
        "SELECT COALESCE(SUM(xp),0) AS x FROM activities WHERE user_id=? AND local_date BETWEEN ? AND ?",
        (user_id, start.isoformat(), end.isoformat()))["x"]
    tasks = tasks_between(user_id, start, end)
    return {"start": start, "end": end, "xp": xp, "planned": len(tasks),
            "done": sum(1 for t in tasks if t["status"] == "done")}


# ---------------- reminders ----------------
def reminders(user_id, now: datetime):
    """Pending tasks today that are due now (up to 2h late) or start within 30 minutes."""
    today_s = now.date().isoformat()
    out = []
    for t in db.query_all(
            "SELECT * FROM study_schedule WHERE user_id=? AND scheduled_date=? AND status='pending' "
            "ORDER BY scheduled_time", (user_id, today_s)):
        due = datetime.strptime(f"{today_s} {t['scheduled_time']}", "%Y-%m-%d %H:%M")
        minutes = (due - now.replace(tzinfo=None)).total_seconds() / 60
        if -120 <= minutes <= 30:
            t["state"] = "due" if minutes <= 0 else "soon"
            t["minutes"] = int(abs(minutes))
            out.append(t)
    return out


# ---------------- AI plan ----------------
def weak_areas(user_id):
    """Real weak spots only: repeated grammar categories and low quiz accuracy."""
    areas = []
    for r in db.query_all(
            """SELECT category, COUNT(*) AS c FROM grammar_mistakes WHERE user_id=?
               GROUP BY category HAVING c >= 2 ORDER BY c DESC LIMIT 3""", (user_id,)):
        areas.append(f"{r['category']} ({r['c']} mistakes in conversations)")
    q = db.query_one(
        "SELECT COALESCE(SUM(total),0) AS t, COALESCE(SUM(correct),0) AS c FROM quiz_results WHERE user_id=?",
        (user_id,))
    if q["t"] >= 10 and q["c"] / q["t"] < 0.7:
        areas.append(f"Vocabulary (quiz accuracy {round(100 * q['c'] / q['t'])}%)")
    return areas


def suggest_plan(user_id, level, minutes_per_day, days, start_date: date, preferred_time, areas, preferences):
    """Ask Gemini for a plan. Returns a validated list of task dicts. Raises ai.AIError."""
    data_note = ("Weak areas found in the learner's real history: " + "; ".join(areas)
                 if areas else "There is no performance history yet, so base the plan on level and time only.")
    prompt = f"""Create a {days}-day English study plan for a {level} learner in India.
Available time: {minutes_per_day} minutes per day. Preferred start time: {preferred_time}.
{data_note}
Learner preferences: {preferences or 'none'}.
Allowed activity_type values: {list(ACTIVITY_TYPES)}.
Prefer types the app can verify automatically: conversation, vocabulary_quiz, word_of_day, flashcards.
Return JSON: {{"tasks": [{{"day_offset": 0..{days - 1}, "time": "HH:MM" (24h), "title": short string,
"activity_type": allowed value, "duration_min": integer 5-60}}]}}.
Keep the total minutes of each day within the available time. 2-4 tasks per day."""
    data = ai.generate_json(prompt, "You are an experienced English study coach. Be realistic and concise.")
    raw = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise ai.AIError("The AI plan was in an unexpected format. Please try again.")
    plan = []
    for t in raw[:days * 5]:
        try:
            offset = int(t["day_offset"])
            d = start_date + timedelta(days=offset)
            vals, err = _validate(str(t["title"]), t.get("activity_type", "general"), d.isoformat(),
                                  str(t["time"]), int(t["duration_min"]))
        except (KeyError, ValueError, TypeError):
            continue
        if err or not 0 <= offset < days:
            continue
        plan.append({"title": vals[0], "activity_type": vals[1], "date": vals[2], "time": vals[3],
                     "duration_min": vals[4]})
    if not plan:
        raise ai.AIError("The AI did not return a usable plan. Please try again.")
    return sorted(plan, key=lambda x: (x["date"], x["time"]))
