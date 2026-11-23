"""Progress analytics. Every number here is computed from the learner's own saved records.

Rules this module follows:
- Nothing is invented. If there is not enough data, a value is None and the UI shows an empty state.
- Every query is parameterized and filtered by user_id.
- "Learning time" is real for quizzes and ESTIMATED for other activities (see config.py).
"""
import json
from datetime import date, timedelta

from config import (MIN_CHAT_MESSAGES_FOR_SCORE, MIN_MISTAKES_FOR_WEAK_AREA,
                    MIN_QUIZ_QUESTIONS_FOR_SCORE)
from core import database as db

KIND_LABELS = {
    "conversation_turn": "Conversation",
    "quiz_complete": "Vocabulary quiz",
    "word_of_day": "Word of the day",
    "flashcard_review": "Flashcards",
    "targeted_practice": "Targeted practice",
    "grammar_lesson": "Grammar lesson",
    "writing": "Writing",
    "pronunciation": "Pronunciation",
}


def _iso(d: date) -> str:
    return d.isoformat()


def _pct(part, whole):
    return round(100 * part / whole) if whole else None


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# ------------------------------------------------------------------ chat accuracy
def _chat_by_date(user_id, tz_offset_min, start: date, end: date):
    """{date_iso: [messages, messages_with_mistakes]} from saved conversation feedback.
    chat_history stores UTC timestamps, so shift them to the learner's local date."""
    rows = db.query_all(
        """SELECT date(created_at, ? ) AS d, correction FROM chat_history
           WHERE user_id=? AND role='assistant' AND correction != ''
             AND date(created_at, ?) BETWEEN ? AND ?""",
        (f"{int(tz_offset_min):+d} minutes", user_id, f"{int(tz_offset_min):+d} minutes",
         _iso(start), _iso(end)))
    out = {}
    for r in rows:
        try:
            has = bool(json.loads(r["correction"]).get("has_mistakes"))
        except (ValueError, AttributeError):
            continue
        cell = out.setdefault(r["d"], [0, 0])
        cell[0] += 1
        cell[1] += 1 if has else 0
    return out


# ------------------------------------------------------------------ daily series
def daily_series(user_id, tz_offset_min, start: date, end: date):
    """One dict per day (including empty days) so charts have no gaps."""
    act = {r["local_date"]: r for r in db.query_all(
        """SELECT local_date, SUM(xp) AS xp, SUM(duration_sec) AS sec, COUNT(*) AS n
           FROM activities WHERE user_id=? AND local_date BETWEEN ? AND ? GROUP BY local_date""",
        (user_id, _iso(start), _iso(end)))}
    quiz = {r["local_date"]: r for r in db.query_all(
        """SELECT local_date, SUM(total) AS t, SUM(correct) AS c FROM quiz_results
           WHERE user_id=? AND local_date BETWEEN ? AND ? GROUP BY local_date""",
        (user_id, _iso(start), _iso(end)))}
    gram = {r["local_date"]: r["c"] for r in db.query_all(
        """SELECT local_date, COUNT(*) AS c FROM grammar_mistakes
           WHERE user_id=? AND local_date BETWEEN ? AND ? GROUP BY local_date""",
        (user_id, _iso(start), _iso(end)))}
    chat = _chat_by_date(user_id, tz_offset_min, start, end)

    rows = []
    for d in _daterange(start, end):
        k = _iso(d)
        a, q, c = act.get(k), quiz.get(k), chat.get(k, [0, 0])
        rows.append({
            "date": d, "label": d.strftime("%a %d %b"),
            "xp": a["xp"] if a else 0,
            "minutes": round((a["sec"] or 0) / 60, 1) if a else 0,
            "activities": a["n"] if a else 0,
            "quiz_total": q["t"] if q else 0,
            "quiz_correct": q["c"] if q else 0,
            "chat_messages": c[0], "chat_with_mistakes": c[1],
            "mistakes": gram.get(k, 0),
        })
    return rows


# ------------------------------------------------------------------ period summary
def period_summary(user_id, tz_offset_min, start: date, end: date):
    rows = daily_series(user_id, tz_offset_min, start, end)
    msgs = sum(r["chat_messages"] for r in rows)
    clean = msgs - sum(r["chat_with_mistakes"] for r in rows)
    qt = sum(r["quiz_total"] for r in rows)
    qc = sum(r["quiz_correct"] for r in rows)
    ex = db.query_one(
        """SELECT COUNT(*) AS sets, COALESCE(SUM(total),0) AS t, COALESCE(SUM(correct),0) AS c
           FROM exercise_results WHERE user_id=? AND local_date BETWEEN ? AND ?""",
        (user_id, _iso(start), _iso(end)))
    return {
        "start": start, "end": end,
        "xp": sum(r["xp"] for r in rows),
        "minutes": round(sum(r["minutes"] for r in rows), 1),
        "active_days": sum(1 for r in rows if r["activities"] > 0),
        "days": len(rows),
        "activities": sum(r["activities"] for r in rows),
        "chat_messages": msgs,
        "grammar_accuracy": _pct(clean, msgs),         # % of messages with no mistakes
        "mistakes": sum(r["mistakes"] for r in rows),
        "quiz_questions": qt, "quiz_correct": qc, "quiz_accuracy": _pct(qc, qt),
        "exercise_sets": ex["sets"], "exercise_accuracy": _pct(ex["c"], ex["t"]),
    }


def lifetime_totals(user_id):
    a = db.query_one(
        """SELECT COALESCE(SUM(duration_sec),0) AS sec, COUNT(*) AS n,
                  COUNT(DISTINCT local_date) AS days, MIN(local_date) AS first
           FROM activities WHERE user_id=?""", (user_id,))
    q = db.query_one(
        """SELECT COUNT(*) AS quizzes, COALESCE(SUM(total),0) AS t, COALESCE(SUM(correct),0) AS c
           FROM quiz_results WHERE user_id=?""", (user_id,))
    words = db.query_one("SELECT COUNT(*) AS c FROM vocabulary WHERE user_id=? AND learned=1", (user_id,))["c"]
    chat = db.query_one(
        "SELECT COUNT(*) AS c FROM chat_history WHERE user_id=? AND role='user'", (user_id,))["c"]
    return {
        "minutes": round(a["sec"] / 60, 1), "activities": a["n"], "active_days": a["days"],
        "first_date": a["first"], "quizzes": q["quizzes"], "quiz_questions": q["t"],
        "quiz_accuracy": _pct(q["c"], q["t"]), "words_learned": words, "chat_messages": chat,
    }


def has_any_data(user_id) -> bool:
    return db.query_one("SELECT COUNT(*) AS c FROM activities WHERE user_id=?", (user_id,))["c"] > 0


# ------------------------------------------------------------------ breakdowns
def activity_breakdown(user_id, start: date, end: date):
    rows = db.query_all(
        """SELECT kind, COUNT(*) AS n, SUM(xp) AS xp, SUM(duration_sec) AS sec FROM activities
           WHERE user_id=? AND local_date BETWEEN ? AND ? GROUP BY kind ORDER BY sec DESC""",
        (user_id, _iso(start), _iso(end)))
    return [{"kind": KIND_LABELS.get(r["kind"], r["kind"]), "count": r["n"], "xp": r["xp"],
             "minutes": round(r["sec"] / 60, 1)} for r in rows]


def grammar_categories(user_id, start: date = None, end: date = None):
    sql = "SELECT category, COUNT(*) AS c FROM grammar_mistakes WHERE user_id=?"
    params = [user_id]
    if start and end:
        sql += " AND local_date BETWEEN ? AND ?"
        params += [_iso(start), _iso(end)]
    return db.query_all(sql + " GROUP BY category ORDER BY c DESC", tuple(params))


def recent_mistake_examples(user_id, category, limit=3):
    return db.query_all(
        """SELECT original, corrected FROM grammar_mistakes WHERE user_id=? AND category=?
           ORDER BY id DESC LIMIT ?""", (user_id, category, limit))


def weekly_grammar_trend(user_id, tz_offset_min, today: date, weeks=8):
    """Per ISO week: conversation messages, % without mistakes. Shows whether grammar improves."""
    monday = today - timedelta(days=today.weekday())
    out = []
    for i in range(weeks - 1, -1, -1):
        s = monday - timedelta(weeks=i)
        e = min(s + timedelta(days=6), today)
        p = period_summary(user_id, tz_offset_min, s, e)
        out.append({"week_start": s, "label": s.strftime("%d %b"),
                    "messages": p["chat_messages"], "accuracy": p["grammar_accuracy"],
                    "mistakes": p["mistakes"]})
    return out


def weekly_totals(user_id, tz_offset_min, today: date, weeks=8):
    monday = today - timedelta(days=today.weekday())
    out = []
    for i in range(weeks - 1, -1, -1):
        s = monday - timedelta(weeks=i)
        e = min(s + timedelta(days=6), today)
        p = period_summary(user_id, tz_offset_min, s, e)
        out.append({"week_start": s, "label": s.strftime("%d %b"), "xp": p["xp"],
                    "minutes": p["minutes"], "active_days": p["active_days"]})
    return out


# ------------------------------------------------------------------ skills
def skill_scores(user_id):
    """0-100 score per skill, only when there is enough real data. Others are listed as
    'not enough data' (with the reason) so the UI never fakes a number."""
    life = lifetime_totals(user_id)
    skills = []

    # Vocabulary = quiz accuracy
    if life["quiz_questions"] >= MIN_QUIZ_QUESTIONS_FOR_SCORE:
        skills.append({"skill": "Vocabulary", "score": life["quiz_accuracy"],
                       "basis": f"{life['quiz_questions']} quiz questions"})
    else:
        skills.append({"skill": "Vocabulary", "score": None,
                       "basis": f"Answer {MIN_QUIZ_QUESTIONS_FOR_SCORE}+ quiz questions"})

    # Grammar = share of conversation messages with no mistakes
    msgs = db.query_all(
        "SELECT correction FROM chat_history WHERE user_id=? AND role='assistant' AND correction != ''",
        (user_id,))
    total = clean = 0
    for r in msgs:
        try:
            has = bool(json.loads(r["correction"]).get("has_mistakes"))
        except (ValueError, AttributeError):
            continue
        total += 1
        clean += 0 if has else 1
    if total >= MIN_CHAT_MESSAGES_FOR_SCORE:
        skills.append({"skill": "Grammar", "score": _pct(clean, total),
                       "basis": f"{total} conversation messages"})
    else:
        skills.append({"skill": "Grammar", "score": None,
                       "basis": f"Send {MIN_CHAT_MESSAGES_FOR_SCORE}+ conversation messages"})

    # Targeted practice accuracy
    ex = db.query_one(
        "SELECT COALESCE(SUM(total),0) AS t, COALESCE(SUM(correct),0) AS c FROM exercise_results WHERE user_id=?",
        (user_id,))
    if ex["t"] >= MIN_QUIZ_QUESTIONS_FOR_SCORE:
        skills.append({"skill": "Targeted practice", "score": _pct(ex["c"], ex["t"]),
                       "basis": f"{ex['t']} practice questions"})
    else:
        skills.append({"skill": "Targeted practice", "score": None,
                       "basis": f"Answer {MIN_QUIZ_QUESTIONS_FOR_SCORE}+ practice questions (AI Coach tab)"})

    # Writing: filled by Phase 4 (table already exists)
    w = db.query_one("SELECT COUNT(*) AS n, AVG(score) AS avg FROM writing_assessments "
                     "WHERE user_id=? AND score IS NOT NULL", (user_id,))
    if w["n"] >= 1:
        skills.append({"skill": "Writing", "score": round(w["avg"]), "basis": f"{w['n']} assessed pieces"})
    else:
        skills.append({"skill": "Writing", "score": None, "basis": "Submit an assessed piece in Grammar & Writing"})

    pr = db.query_one("SELECT COUNT(*) AS n, AVG(score) AS avg FROM pronunciation_attempts WHERE user_id=?",
                      (user_id,))
    if pr["n"] >= 3:
        skills.append({"skill": "Pronunciation", "score": round(pr["avg"]),
                       "basis": f"{pr['n']} speech-matching attempts (speech-to-text match, not phonetics)"})
    else:
        skills.append({"skill": "Pronunciation", "score": None, "basis": "Do 3+ speaking attempts"})
    return skills


def strongest_weakest(skills):
    scored = [s for s in skills if s["score"] is not None]
    if len(scored) < 2:
        return None, None
    scored.sort(key=lambda s: s["score"])
    return scored[-1], scored[0]


def weak_grammar_categories(user_id):
    return [r for r in grammar_categories(user_id) if r["c"] >= MIN_MISTAKES_FOR_WEAK_AREA]


# ------------------------------------------------------------------ comparison + report
def _delta(cur, prev):
    if cur is None or prev is None:
        return None
    return cur - prev


def compare_periods(user_id, tz_offset_min, cur_start, cur_end, prev_start, prev_end):
    cur = period_summary(user_id, tz_offset_min, cur_start, cur_end)
    prev = period_summary(user_id, tz_offset_min, prev_start, prev_end)
    rows = []
    for key, label, unit in [("xp", "XP earned", ""), ("minutes", "Learning time", " min"),
                             ("active_days", "Active days", ""),
                             ("chat_messages", "Conversation messages", ""),
                             ("grammar_accuracy", "Messages without mistakes", "%"),
                             ("quiz_questions", "Quiz questions", ""),
                             ("quiz_accuracy", "Quiz accuracy", "%")]:
        rows.append({"metric": label, "unit": unit, "current": cur[key], "previous": prev[key],
                     "delta": _delta(cur[key], prev[key])})
    return cur, prev, rows


def this_vs_last_week(user_id, tz_offset_min, today: date):
    monday = today - timedelta(days=today.weekday())
    return compare_periods(user_id, tz_offset_min, monday, today,
                           monday - timedelta(days=7), monday - timedelta(days=1))


def this_vs_last_month(user_id, tz_offset_min, today: date):
    first = today.replace(day=1)
    last_prev = first - timedelta(days=1)
    return compare_periods(user_id, tz_offset_min, first, today, last_prev.replace(day=1), last_prev)


def weekly_report_markdown(name, today: date, cur, prev, rows, cats, skills):
    def fmt(v, unit):
        return "–" if v is None else f"{v}{unit}"

    def dfmt(d, unit):
        if d is None:
            return "–"
        return "0" if d == 0 else f"{d:+g}{unit}"

    lines = [f"# Weekly report – {name}",
             f"Week of {cur['start']:%d %b %Y} to {today:%d %b %Y}", "",
             "| Metric | This week | Last week | Change |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['metric']} | {fmt(r['current'], r['unit'])} | "
                     f"{fmt(r['previous'], r['unit'])} | {dfmt(r['delta'], r['unit'])} |")
    lines += ["", "## Most common grammar mistakes this week"]
    lines += [f"- {c['category']}: {c['c']}" for c in cats[:5]] or ["- No grammar mistakes recorded."]
    lines += ["", "## Skill scores (all time)"]
    for s in skills:
        lines.append(f"- {s['skill']}: " + (f"{s['score']}% ({s['basis']})" if s["score"] is not None
                                            else f"not enough data ({s['basis']})"))
    lines += ["", "_Learning time is measured for quizzes and estimated for other activities._"]
    return "\n".join(lines)


# ------------------------------------------------------------------ data summary for AI
def ai_data_summary(user_id, tz_offset_min, today: date) -> dict:
    """Compact, real-only facts that are sent to Gemini for recommendations."""
    monday = today - timedelta(days=today.weekday())
    this = period_summary(user_id, tz_offset_min, monday, today)
    last = period_summary(user_id, tz_offset_min, monday - timedelta(days=7), monday - timedelta(days=1))
    skills = [s for s in skill_scores(user_id) if s["score"] is not None]
    life = lifetime_totals(user_id)
    return {
        "lifetime": {k: life[k] for k in ("minutes", "activities", "active_days", "quizzes",
                                          "quiz_questions", "quiz_accuracy", "words_learned", "chat_messages")},
        "this_week": {k: this[k] for k in ("xp", "minutes", "active_days", "chat_messages",
                                           "grammar_accuracy", "quiz_questions", "quiz_accuracy")},
        "last_week": {k: last[k] for k in ("xp", "minutes", "active_days", "chat_messages",
                                           "grammar_accuracy", "quiz_questions", "quiz_accuracy")},
        "skill_scores": {s["skill"]: s["score"] for s in skills},
        "grammar_mistakes_by_category": {c["category"]: c["c"] for c in grammar_categories(user_id)},
        "difficult_or_missed_words": [w["word"] for w in db.query_all(
            "SELECT word FROM vocabulary WHERE user_id=? AND (difficult=1 OR times_wrong>0) "
            "ORDER BY times_wrong DESC LIMIT 10", (user_id,))],
    }
