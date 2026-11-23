"""Central settings. Everything configurable lives here."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "data" / "english_coach.db"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

LEVELS = ["Beginner", "Intermediate", "Advanced"]
AVATARS = ["🦊", "🐼", "🦉", "🐯", "🐸", "🦄", "🐙", "🐧", "🦁", "🐨"]
DEFAULT_DAILY_GOAL_XP = 50

# XP awarded per genuine activity
XP_RULES = {
    "conversation_turn": 5,   # one conversation message that gets AI feedback
    "quiz_correct": 4,        # per correct quiz answer
    "quiz_complete": 10,      # bonus for finishing a quiz
    "word_of_day": 5,
    "flashcard_review": 1,
    "targeted_correct": 3,    # per correct answer in an AI targeted-practice set
    "targeted_complete": 5,   # bonus for finishing a targeted-practice set
    "grammar_correct": 3,     # per correct answer in a grammar lesson quiz
    "grammar_complete": 5,
    "writing_piece": 15,      # a assessed piece of writing that meets the minimum length
    "pronunciation_good": 4,  # first time a sentence is matched at >= PRONUNCIATION_PASS %
}
PRONUNCIATION_PASS = 70
WRITING_MIN_WORDS = {"Journal entry": 20, "Paragraph": 40, "Email": 40, "Essay": 120}

# Learning-time tracking. Quizzes are timed for real (start -> submit). For other activities
# the app can only see *when you act*, so time is ESTIMATED: the gap since your previous action
# (counted only if it is at most ACTIVE_GAP_CAP_SEC), otherwise a small default per activity.
ACTIVE_GAP_CAP_SEC = 180
DEFAULT_ACTIVITY_SEC = {
    "conversation_turn": 45,
    "word_of_day": 30,
    "flashcard_review": 15,
    "quiz_complete": 60,
    "targeted_practice": 120,
    "grammar_lesson": 120,
    "writing": 180,
    "pronunciation": 40,
}

# Analytics thresholds: below these, the app says "not enough data" instead of guessing.
MIN_QUIZ_QUESTIONS_FOR_SCORE = 5
MIN_CHAT_MESSAGES_FOR_SCORE = 5
MIN_MISTAKES_FOR_WEAK_AREA = 2

CONVERSATION_TOPICS = {
    "Daily life": "everyday situations like routines, family, hobbies and weekend plans",
    "Job interview": "a job interview where you play the interviewer",
    "College": "college life: classes, assignments, professors, campus and friends",
    "Travel": "travel: airports, hotels, directions, sightseeing",
    "Shopping & restaurant": "shopping in stores and ordering in restaurants",
    "Friendly chat": "a relaxed friendly chat about anything the learner likes",
    "Roleplay: friend": "a roleplay where you act as the learner's friend meeting them for coffee; stay in character",
    "Roleplay: teacher": "a roleplay where you act as a school teacher talking with the learner about their studies; stay in character",
    "Roleplay: shopkeeper": "a roleplay where you act as a shopkeeper and the learner is a customer; stay in character",
}

LEARNER_LEVEL_STEP = 100  # XP per learner level
