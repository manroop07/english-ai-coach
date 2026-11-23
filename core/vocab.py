"""Vocabulary logic: word of the day, quizzes, flashcards, personal dictionary."""
import random
from datetime import date

from core import database as db
from core.vocab_bank import BANK


def _ensure_word(user_id, w):
    """Make sure a bank word exists in the user's personal dictionary."""
    db.execute(
        """INSERT OR IGNORE INTO vocabulary
           (user_id, word, meaning, hindi, example, synonyms, antonyms)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, w["word"], w["meaning"], w["hindi"], w["example"], w["synonyms"], w["antonyms"]),
    )


def words_for_level(level):
    same = [w for w in BANK if w["level"] == level]
    return same if len(same) >= 4 else BANK


def word_of_the_day(user_id, level, today: date):
    pool = words_for_level(level)
    w = pool[(today.toordinal() + user_id) % len(pool)]
    _ensure_word(user_id, w)
    return w


def word_of_day_claimed(user_id, today_s):
    return db.query_one(
        "SELECT id FROM activities WHERE user_id=? AND kind='word_of_day' AND local_date=?",
        (user_id, today_s),
    ) is not None


def build_quiz(user_id, level, n):
    """Multiple-choice 'what does this word mean?' questions from the user's level.
    Words the learner has not mastered yet come first."""
    pool = words_for_level(level)
    for w in pool:
        _ensure_word(user_id, w)
    learned = {
        r["word"] for r in db.query_all(
            "SELECT word FROM vocabulary WHERE user_id=? AND learned=1", (user_id,))
    }
    fresh = [w for w in pool if w["word"] not in learned]
    seen = [w for w in pool if w["word"] in learned]
    random.shuffle(fresh)
    random.shuffle(seen)
    chosen = (fresh + seen)[:n]

    questions = []
    for w in chosen:
        wrong = [x["meaning"] for x in BANK if x["word"] != w["word"] and x["meaning"] != w["meaning"]]
        options = random.sample(wrong, 3) + [w["meaning"]]
        random.shuffle(options)
        questions.append({"word": w["word"], "answer": w["meaning"], "options": options,
                          "hindi": w["hindi"], "example": w["example"]})
    return questions


def record_quiz(user_id, quiz_type, answers, local_date):
    """answers: list of (word, was_correct). Returns number correct."""
    correct = 0
    for word, ok in answers:
        if ok:
            correct += 1
            db.execute(
                "UPDATE vocabulary SET times_correct = times_correct + 1, learned = 1 "
                "WHERE user_id=? AND word=?", (user_id, word))
        else:
            db.execute(
                "UPDATE vocabulary SET times_wrong = times_wrong + 1 WHERE user_id=? AND word=?",
                (user_id, word))
    db.execute(
        "INSERT INTO quiz_results (user_id, quiz_type, total, correct, local_date) VALUES (?,?,?,?,?)",
        (user_id, quiz_type, len(answers), correct, local_date))
    return correct


def quiz_summary(user_id):
    r = db.query_one(
        "SELECT COUNT(*) AS quizzes, COALESCE(SUM(total),0) AS total, COALESCE(SUM(correct),0) AS correct "
        "FROM quiz_results WHERE user_id=?", (user_id,))
    r["accuracy"] = round(100 * r["correct"] / r["total"]) if r["total"] else None
    return r


def my_words(user_id, only_difficult=False, only_revision=False):
    sql = "SELECT * FROM vocabulary WHERE user_id=?"
    if only_difficult:
        sql += " AND difficult=1"
    if only_revision:
        sql += " AND (difficult=1 OR times_wrong > 0)"
    return db.query_all(sql + " ORDER BY word", (user_id,))


def toggle_difficult(user_id, word_id, value):
    db.execute("UPDATE vocabulary SET difficult=? WHERE id=? AND user_id=?",
               (1 if value else 0, word_id, user_id))


def mark_learned(user_id, word):
    """Returns True only the first time (so XP can't be farmed)."""
    row = db.query_one("SELECT learned FROM vocabulary WHERE user_id=? AND word=?", (user_id, word))
    if not row or row["learned"]:
        return False
    db.execute("UPDATE vocabulary SET learned=1 WHERE user_id=? AND word=?", (user_id, word))
    return True


def add_custom_word(user_id, word, meaning, hindi="", example=""):
    word = word.strip().lower()
    if not word or not meaning.strip():
        return "Please enter both a word and its meaning."
    db.execute(
        "INSERT OR IGNORE INTO vocabulary (user_id, word, meaning, hindi, example) VALUES (?,?,?,?,?)",
        (user_id, word, meaning.strip(), hindi.strip(), example.strip()))
    return None
