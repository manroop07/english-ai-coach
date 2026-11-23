"""AI conversation partner with grammar feedback after each learner message."""
import uuid

from config import CONVERSATION_TOPICS
from core import ai
from core import database as db

LEVEL_STYLE = {
    "Beginner": "Use very short, simple sentences and common words. Speak slowly and clearly.",
    "Intermediate": "Use natural everyday English with some new vocabulary. Medium-length sentences.",
    "Advanced": "Use rich vocabulary, idioms and complex sentences. Challenge the learner gently.",
}

GRAMMAR_CATEGORIES = ["Tenses", "Prepositions", "Articles", "Subject-verb agreement",
                      "Word choice", "Sentence structure", "Spelling", "Other"]


def new_session_id():
    return uuid.uuid4().hex[:12]


def _system_prompt(topic, level, preferences):
    return f"""You are a warm, encouraging English teacher having a spoken-style conversation.
Topic: {CONVERSATION_TOPICS[topic]}.
Learner level: {level}. {LEVEL_STYLE[level]}
Learner preferences: {preferences or 'none'}.
Rules:
- Reply naturally in 1-3 sentences and ALWAYS end with a question so the conversation continues.
- Never be harsh. Praise effort and encourage the learner to speak confidently.
- Check ONLY the learner's latest message for English mistakes.
Return JSON with exactly these keys:
  "reply": string, your conversational reply,
  "has_mistakes": boolean,
  "corrected": string, the corrected version of the learner's message (same as original if no mistakes),
  "mistakes": list of objects {{"category": one of {GRAMMAR_CATEGORIES}, "original": string, "explanation": string (simple English, max 20 words)}},
  "better_sentence": string, a more natural way to say it (empty if the message was already natural),
  "encouragement": string, one short motivating sentence."""


def send_message(user_id, session_id, topic, level, preferences, history, user_text):
    """history: list of {"role": "user"/"assistant", "content": str}. Raises ai.AIError."""
    transcript = "\n".join(
        f"{'Learner' if m['role'] == 'user' else 'Teacher'}: {m['content']}" for m in history[-12:]
    )
    prompt = f"Conversation so far:\n{transcript or '(none yet)'}\n\nLearner's latest message: {user_text}"
    data = ai.generate_json(prompt, _system_prompt(topic, level, preferences))
    if not isinstance(data, dict) or "reply" not in data:
        raise ai.AIError("The AI answer was in an unexpected format. Please try again.")
    mistakes = [m for m in (data.get("mistakes") or []) if isinstance(m, dict)]
    result = {
        "reply": str(data.get("reply", "")).strip(),
        "has_mistakes": bool(data.get("has_mistakes")) and bool(mistakes),
        "corrected": str(data.get("corrected", "")).strip(),
        "mistakes": mistakes,
        "better_sentence": str(data.get("better_sentence", "")).strip(),
        "encouragement": str(data.get("encouragement", "")).strip(),
    }
    return result


def save_turn(user_id, session_id, topic, user_text, result, local_date):
    import json

    db.execute(
        "INSERT INTO chat_history (user_id, session_id, topic, role, content) VALUES (?,?,?,?,?)",
        (user_id, session_id, topic, "user", user_text))
    db.execute(
        "INSERT INTO chat_history (user_id, session_id, topic, role, content, correction) VALUES (?,?,?,?,?,?)",
        (user_id, session_id, topic, "assistant", result["reply"],
         json.dumps({k: result[k] for k in ("has_mistakes", "corrected", "mistakes",
                                            "better_sentence", "encouragement")})))
    for m in result["mistakes"]:
        cat = m.get("category") if m.get("category") in GRAMMAR_CATEGORIES else "Other"
        db.execute(
            "INSERT INTO grammar_mistakes (user_id, category, original, corrected, local_date) VALUES (?,?,?,?,?)",
            (user_id, cat, str(m.get("original", ""))[:200], result["corrected"][:300], local_date))


def list_sessions(user_id):
    return db.query_all(
        """SELECT session_id, topic, MIN(created_at) AS started, COUNT(*) AS messages
           FROM chat_history WHERE user_id=? GROUP BY session_id ORDER BY MIN(id) DESC LIMIT 30""",
        (user_id,))


def load_session(user_id, session_id):
    import json

    rows = db.query_all(
        "SELECT role, content, correction FROM chat_history WHERE user_id=? AND session_id=? ORDER BY id",
        (user_id, session_id))
    msgs = []
    for r in rows:
        m = {"role": r["role"], "content": r["content"]}
        if r["correction"]:
            try:
                m["feedback"] = json.loads(r["correction"])
            except ValueError:
                pass
        msgs.append(m)
    return msgs
