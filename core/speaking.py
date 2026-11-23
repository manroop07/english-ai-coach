"""Speaking practice helpers.

IMPORTANT: scores here compare what speech-to-text HEARD with the target sentence, word by word.
They are NOT a phonetic pronunciation assessment – the transcriber may also quietly 'fix' small
errors. The UI says this plainly.
"""
import difflib
import re

from config import PRONUNCIATION_PASS
from core import ai
from core import database as db

SCENARIOS = {
    "Everyday life": "daily routines, family, hobbies",
    "Job interview": "answering common interview questions",
    "Travel": "airports, hotels, asking for directions",
    "Shopping & restaurant": "buying things and ordering food",
    "Classroom & college": "talking to teachers and classmates",
}


def _tokens(text):
    return re.findall(r"[a-z0-9']+", (text or "").lower().replace("’", "'"))


def compare(target, recognized):
    """Word-level match. Returns {"score", "words": [{"word","ok"}], "extra": [...]}."""
    t, r = _tokens(target), _tokens(recognized)
    if not t:
        return {"score": 0, "words": [], "extra": []}
    sm = difflib.SequenceMatcher(None, t, r, autojunk=False)
    ok = [False] * len(t)
    extra = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                ok[i] = True
        elif tag in ("insert", "replace"):
            extra += r[j1:j2]
    original_words = target.split()
    words = [{"word": original_words[i] if len(original_words) == len(t) else t[i], "ok": ok[i]}
             for i in range(len(t))]
    return {"score": round(100 * sum(ok) / len(t)), "words": words, "extra": extra}


def generate_sentences(level, scenario, n=5):
    prompt = f"""Write {n} English sentences for a {level} learner to read aloud. Scenario: {scenario} ({SCENARIOS.get(scenario, '')}).
Beginner: 5-8 words. Intermediate: 8-12 words. Advanced: 12-18 words. Natural, useful in real life.
Return JSON: {{"sentences": [{n} strings]}}"""
    d = ai.generate_json(prompt, "You write clear speaking-practice sentences.")
    s = d.get("sentences") if isinstance(d, dict) else None
    out = [str(x).strip() for x in (s or []) if isinstance(x, (str,)) and 2 <= len(str(x).split()) <= 30]
    if not out:
        raise ai.AIError("The AI did not return usable sentences. Please try again.")
    return out[:n]


def already_passed(user_id, target):
    return db.query_one("SELECT 1 AS x FROM pronunciation_attempts WHERE user_id=? AND target=? AND score>=?",
                        (user_id, target, PRONUNCIATION_PASS)) is not None


def save_attempt(user_id, target, recognized, score, scenario, local_date):
    db.execute("INSERT INTO pronunciation_attempts (user_id, target, recognized, score, scenario, local_date) "
               "VALUES (?,?,?,?,?,?)", (user_id, target[:300], recognized[:300], score, scenario[:60], local_date))


def history(user_id, limit=30):
    return db.query_all("SELECT target, recognized, score, scenario, created_at FROM pronunciation_attempts "
                        "WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))


def stats(user_id):
    r = db.query_one("SELECT COUNT(*) AS n, AVG(score) AS avg, MAX(score) AS best FROM pronunciation_attempts "
                     "WHERE user_id=?", (user_id,))
    return {"attempts": r["n"], "average": round(r["avg"]) if r["avg"] is not None else None, "best": r["best"]}
