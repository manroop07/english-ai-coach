"""Grammar lessons and AI writing assessment."""
import json

from config import WRITING_MIN_WORDS
from core import ai
from core import database as db
from core.conversation import GRAMMAR_CATEGORIES

GRAMMAR_TOPICS = {
    "Tenses": "Tenses",
    "Prepositions": "Prepositions",
    "Articles": "Articles",
    "Sentence formation": "Sentence structure",
    "Active and passive voice": "Sentence structure",
    "Direct and indirect speech": "Sentence structure",
    "Common grammatical mistakes": "Other",
}
WRITING_KINDS = {
    "Journal entry": "a personal daily journal entry about the learner's day",
    "Paragraph": "a single well-organised paragraph",
    "Email": "an email with subject, greeting, body and closing",
    "Essay": "an essay with introduction, body and conclusion",
}
MAX_CHARS = 4000


def count_words(text: str) -> int:
    return len(text.split())


def generate_lesson(topic, level):
    """Returns {"explanation", "rules": [..], "examples": [{"wrong","right"}], "tip"}. Raises ai.AIError."""
    prompt = f"""Teach the English grammar topic “{topic}” to a {level} learner (Hindi-speaking, India).
Use simple English. Return JSON: {{"explanation": string (max 70 words),
"rules": [3-5 short strings], "examples": [{{"wrong": string, "right": string}}] (3-4 items; common mistakes),
"tip": string (one memory trick)}}"""
    d = ai.generate_json(prompt, "You are a clear, friendly English grammar teacher.")
    if not isinstance(d, dict) or not d.get("explanation") or not isinstance(d.get("rules"), list):
        raise ai.AIError("The AI lesson was in an unexpected format. Please try again.")
    ex = [e for e in (d.get("examples") or []) if isinstance(e, dict) and e.get("right")]
    return {"explanation": str(d["explanation"]), "rules": [str(r) for r in d["rules"]][:5],
            "examples": ex[:4], "tip": str(d.get("tip", ""))}


def validate_writing(kind, text):
    text = (text or "").strip()
    if kind not in WRITING_KINDS:
        return "Choose what you are writing."
    if len(text) > MAX_CHARS:
        return f"Please keep it under {MAX_CHARS} characters."
    need = WRITING_MIN_WORDS[kind]
    if count_words(text) < need:
        return f"A {kind.lower()} needs at least {need} words (you have {count_words(text)})."
    return None


def assess_writing(user_id, kind, text, level, prompt_topic, local_date):
    """AI assessment. Saves to writing_assessments and feeds grammar_mistakes. Raises ai.AIError."""
    err = validate_writing(kind, text)
    if err:
        raise ai.AIError(err)
    prompt = f"""Assess this learner's {kind} ({WRITING_KINDS[kind]}). Level: {level}. Topic: {prompt_topic or 'free'}.
Be kind and specific. Return JSON: {{"score": integer 0-100 (grammar, vocabulary, organisation, clarity),
"summary": string (2 sentences), "strengths": [max 3 strings],
"corrected": string (the full text with errors fixed, keeping the learner's ideas),
"issues": [{{"category": one of {GRAMMAR_CATEGORIES}, "original": string, "explanation": string (max 20 words)}}] (max 8),
"sentence_improvements": [{{"original": string, "better": string}}] (max 3),
"vocabulary_suggestions": [{{"word": string, "better_word": string, "why": string}}] (max 4)}}
Learner's text:
\"\"\"{text}\"\"\""""
    d = ai.generate_json(prompt, "You are an encouraging English writing tutor.")
    if not isinstance(d, dict):
        raise ai.AIError("The AI feedback was in an unexpected format. Please try again.")
    try:
        score = max(0, min(100, int(d["score"])))
    except (KeyError, ValueError, TypeError):
        raise ai.AIError("The AI did not give a score. Please try again.")
    issues = []
    for i in d.get("issues") or []:
        if isinstance(i, dict) and i.get("original"):
            cat = i.get("category") if i.get("category") in GRAMMAR_CATEGORIES else "Other"
            issues.append({"category": cat, "original": str(i["original"])[:200],
                           "explanation": str(i.get("explanation", ""))[:200]})
    fb = {"score": score, "summary": str(d.get("summary", "")), "strengths": [str(x) for x in (d.get("strengths") or [])][:3],
          "corrected": str(d.get("corrected", "")), "issues": issues[:8],
          "sentence_improvements": [x for x in (d.get("sentence_improvements") or []) if isinstance(x, dict)][:3],
          "vocabulary_suggestions": [x for x in (d.get("vocabulary_suggestions") or []) if isinstance(x, dict)][:4]}
    db.execute("INSERT INTO writing_assessments (user_id, kind, text, feedback, score) VALUES (?,?,?,?,?)",
               (user_id, kind, text, json.dumps(fb), score))
    for i in fb["issues"]:
        db.execute("INSERT INTO grammar_mistakes (user_id, category, original, corrected, local_date) VALUES (?,?,?,?,?)",
                   (user_id, i["category"], i["original"], fb["corrected"][:300], local_date))
    return fb


def history(user_id, limit=20):
    rows = db.query_all("SELECT id, kind, text, feedback, score, created_at FROM writing_assessments "
                        "WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    for r in rows:
        try:
            r["feedback"] = json.loads(r["feedback"])
        except ValueError:
            r["feedback"] = {}
    return rows
