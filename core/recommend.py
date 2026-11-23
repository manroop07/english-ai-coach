"""Personal learning recommendations. Built ONLY from the learner's real saved data.

- Rule-based tips need no AI and always work.
- AI features (practice sets, weekly improvement plan) refuse to run when there is too little
  data, so Gemini is never asked to invent progress.
"""
import random
from datetime import date, timedelta

from config import MIN_QUIZ_QUESTIONS_FOR_SCORE
from core import ai, analytics
from core import database as db
from core import schedule

MIN_ACTIVITIES_FOR_AI_PLAN = 5
MIN_ACTIVE_DAYS_FOR_AI_PLAN = 2
LEVELS_UP = {"Beginner": "Intermediate", "Intermediate": "Advanced"}


# ------------------------------------------------------------------ rule-based
def rule_based(user_id, tz, today: date, level):
    """List of {icon, text, page} sorted by importance. Empty list = nothing to flag."""
    recs = []
    life = analytics.lifetime_totals(user_id)
    if life["activities"] == 0:
        return [{"icon": "🌱", "page": "💬  AI Conversation",
                 "text": "Start with a short AI conversation – your recommendations unlock as you practise."}]

    weak = analytics.weak_grammar_categories(user_id)
    if weak:
        top = weak[0]
        recs.append({"icon": "🧩", "page": None, "target": top["category"],
                     "text": f"“{top['category']}” is your most frequent mistake ({top['c']} times). "
                             "Do a targeted practice set below."})

    if life["quiz_questions"] >= MIN_QUIZ_QUESTIONS_FOR_SCORE and life["quiz_accuracy"] is not None \
            and life["quiz_accuracy"] < 70:
        n = len(db.query_all(
            "SELECT id FROM vocabulary WHERE user_id=? AND (difficult=1 OR times_wrong>0)", (user_id,)))
        recs.append({"icon": "🔁", "page": "📚  Vocabulary",
                     "text": f"Quiz accuracy is {life['quiz_accuracy']}%. Revise your {n} difficult/missed "
                             "word(s) in Flashcards."})

    last = db.query_one("SELECT MAX(local_date) AS d FROM activities WHERE user_id=?", (user_id,))["d"]
    if last:
        gap = (today - date.fromisoformat(last)).days
        if gap >= 2:
            recs.append({"icon": "⏰", "page": "💬  AI Conversation",
                         "text": f"You haven't practised for {gap} days. A 5-minute chat restarts your streak."})

    cur, prev, _ = analytics.this_vs_last_week(user_id, tz, today)
    if prev["minutes"] > 0 and today.weekday() >= 3 and cur["minutes"] < 0.5 * prev["minutes"]:
        recs.append({"icon": "📉", "page": "🗓️  My Schedule",
                     "text": "You're behind last week's study time. Schedule a short session in My Schedule."})

    if cur["grammar_accuracy"] is not None and prev["grammar_accuracy"] is not None \
            and cur["chat_messages"] >= 3 and prev["chat_messages"] >= 3 \
            and cur["grammar_accuracy"] > prev["grammar_accuracy"]:
        recs.append({"icon": "📈", "page": None,
                     "text": f"Your error-free messages rose from {prev['grammar_accuracy']}% to "
                             f"{cur['grammar_accuracy']}% this week. Keep going!"})
    return recs


def difficulty_suggestion(user_id, level):
    """A suggestion only – the learner decides whether to change level in My Profile."""
    life = analytics.lifetime_totals(user_id)
    skills = {s["skill"]: s["score"] for s in analytics.skill_scores(user_id)}
    scores = [v for k, v in skills.items() if k in ("Vocabulary", "Grammar") and v is not None]
    if len(scores) < 2 or life["quiz_questions"] < 10:
        return None
    avg = sum(scores) / len(scores)
    if avg >= 85 and level in LEVELS_UP:
        return (f"Your vocabulary and grammar average is {round(avg)}%. You may be ready for "
                f"**{LEVELS_UP[level]}** – change it in My Profile when you feel ready.")
    if avg < 50 and level != "Beginner":
        return (f"Your vocabulary and grammar average is {round(avg)}%. Practising at an easier level "
                "for a while can build confidence – you can change it in My Profile.")
    return None


# ------------------------------------------------------------------ targeted practice
def practice_topics(user_id):
    """Topics offered for practice: the learner's real weak grammar categories first."""
    topics = [c["category"] for c in analytics.weak_grammar_categories(user_id)]
    has_vocab = db.query_one(
        "SELECT COUNT(*) AS c FROM vocabulary WHERE user_id=? AND (difficult=1 OR times_wrong>0)",
        (user_id,))["c"]
    if has_vocab:
        topics.append("Vocabulary revision")
    return topics


def generate_exercises(user_id, topic, level, n=5):
    """Ask Gemini for n multiple-choice questions personalised to the learner's real mistakes.
    Returns a validated list. Raises ai.AIError."""
    if topic == "Vocabulary revision":
        words = db.query_all(
            "SELECT word, meaning FROM vocabulary WHERE user_id=? AND (difficult=1 OR times_wrong>0) "
            "ORDER BY times_wrong DESC LIMIT 8", (user_id,))
        if not words:
            raise ai.AIError("You have no difficult or missed words yet.")
        material = "Words the learner struggles with: " + "; ".join(f"{w['word']} ({w['meaning']})" for w in words)
        task = "Write fill-in-the-blank or best-meaning questions that test these words in context."
    else:
        ex = analytics.recent_mistake_examples(user_id, topic, 4)
        material = "Real mistakes this learner made:\n" + "\n".join(
            f"- said: {e['original']}  | corrected: {e['corrected']}" for e in ex) if ex else ""
        task = f"Write questions that practise the English grammar area “{topic}”, targeting the same kind of errors."
    prompt = f"""{task}
Learner level: {level}. {material}
Create exactly {n} multiple-choice questions. Each has exactly 4 options and exactly one correct option.
Return JSON: {{"questions": [{{"question": string, "options": [4 strings], "answer": string (identical to one option),
"explanation": string (simple English, max 25 words)}}]}}"""
    data = ai.generate_json(prompt, "You are a patient English teacher writing short, clear practice questions.")
    raw = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise ai.AIError("The AI practice set was in an unexpected format. Please try again.")
    out = []
    for q in raw:
        try:
            opts = [str(o).strip() for o in q["options"]]
            ans = str(q["answer"]).strip()
            if len(opts) != 4 or len(set(opts)) != 4 or ans not in opts or not str(q["question"]).strip():
                continue
            random.shuffle(opts)
            out.append({"question": str(q["question"]).strip(), "options": opts, "answer": ans,
                        "explanation": str(q.get("explanation", "")).strip()})
        except (KeyError, TypeError):
            continue
    if len(out) < 3:
        raise ai.AIError("The AI did not return enough valid questions. Please try again.")
    return out[:n]


def record_exercise_set(user_id, topic, total, correct, local_date):
    db.execute("INSERT INTO exercise_results (user_id, topic, total, correct, local_date) VALUES (?,?,?,?,?)",
               (user_id, topic, total, correct, local_date))


# ------------------------------------------------------------------ weekly improvement plan
def can_use_ai_plan(user_id):
    life = analytics.lifetime_totals(user_id)
    if life["activities"] < MIN_ACTIVITIES_FOR_AI_PLAN or life["active_days"] < MIN_ACTIVE_DAYS_FOR_AI_PLAN:
        return (f"Complete at least {MIN_ACTIVITIES_FOR_AI_PLAN} activities on {MIN_ACTIVE_DAYS_FOR_AI_PLAN}+ "
                f"different days first (you have {life['activities']} on {life['active_days']} day(s)). "
                "The plan is built from your real results, so it needs some to work with.")
    return None


def weekly_improvement_plan(user_id, tz, today: date, level, minutes_per_day, preferences):
    """Returns {"summary", "focus_areas": [...], "tasks": [...], "tip"}. Raises ai.AIError."""
    msg = can_use_ai_plan(user_id)
    if msg:
        raise ai.AIError(msg)
    facts = analytics.ai_data_summary(user_id, tz, today)
    prompt = f"""Here are the learner's REAL statistics (JSON). Use only these facts; never invent numbers.
{facts}
Learner level: {level}. Available time: {minutes_per_day} minutes per day. Preferences: {preferences or 'none'}.
Write a 7-day improvement plan that targets the weakest areas shown in the data.
Allowed activity_type values: {list(schedule.ACTIVITY_TYPES)}.
Prefer the types the app can verify automatically: conversation, vocabulary_quiz, word_of_day, flashcards, grammar.
Return JSON: {{"summary": string (2 sentences that reference the real numbers),
"focus_areas": [{{"area": string, "why": string (cite the data), "action": string}}] (max 3),
"tasks": [{{"day_offset": 0..6, "title": short string, "activity_type": allowed value, "duration_min": 5-60}}] (1-3 per day),
"tip": string}}"""
    data = ai.generate_json(prompt, "You are a data-driven English coach. Be specific, kind and realistic.")
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ai.AIError("The AI plan was in an unexpected format. Please try again.")
    tasks = []
    for t in data["tasks"][:21]:
        try:
            off = int(t["day_offset"])
            atype = t.get("activity_type", "general")
            if not 0 <= off <= 6 or atype not in schedule.ACTIVITY_TYPES:
                continue
            tasks.append({"day_offset": off, "title": str(t["title"]).strip()[:80],
                          "activity_type": atype, "duration_min": max(5, min(60, int(t["duration_min"])))})
        except (KeyError, ValueError, TypeError):
            continue
    if not tasks:
        raise ai.AIError("The AI did not return a usable plan. Please try again.")
    focus = [f for f in (data.get("focus_areas") or []) if isinstance(f, dict)][:3]
    return {"summary": str(data.get("summary", "")).strip(), "focus_areas": focus,
            "tasks": sorted(tasks, key=lambda x: x["day_offset"]), "tip": str(data.get("tip", "")).strip()}


def add_plan_to_schedule(user_id, plan_tasks, start: date, preferred_time):
    """Adds the AI plan's tasks to My Schedule. Returns (added, errors)."""
    added, errors = 0, []
    for t in plan_tasks:
        d = start + timedelta(days=t["day_offset"])
        err = schedule.add_task(user_id, t["title"], t["activity_type"], d.isoformat(),
                                preferred_time, t["duration_min"])
        if err:
            errors.append(err)
        else:
            added += 1
    return added, errors
