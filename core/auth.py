"""Registration, login and profile updates. Passwords are salted + hashed with PBKDF2."""
import hashlib
import hmac
import re
import secrets

from config import AVATARS, DEFAULT_DAILY_GOAL_XP, LEVELS
from core import database as db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ITERATIONS = 200_000


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    ).hex()


def register(name: str, email: str, password: str, level: str):
    """Returns (user_id, error). Exactly one of them is None."""
    name, email = name.strip(), email.strip().lower()
    if len(name) < 2:
        return None, "Please enter your name (at least 2 characters)."
    if not EMAIL_RE.match(email):
        return None, "Please enter a valid email address."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    if level not in LEVELS:
        return None, "Please choose a valid level."
    if db.query_one("SELECT id FROM users WHERE email = ?", (email,)):
        return None, "An account with this email already exists. Try logging in."

    salt = secrets.token_hex(16)
    user_id = db.execute(
        "INSERT INTO users (email, password_hash, salt) VALUES (?, ?, ?)",
        (email, _hash(password, salt), salt),
    )
    avatar = AVATARS[user_id % len(AVATARS)]
    db.execute(
        "INSERT INTO profiles (user_id, name, avatar, level, daily_goal_xp) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, avatar, level, DEFAULT_DAILY_GOAL_XP),
    )
    db.execute("INSERT INTO progress (user_id) VALUES (?)", (user_id,))
    db.execute("INSERT INTO streaks (user_id) VALUES (?)", (user_id,))
    return user_id, None


def login(email: str, password: str):
    """Returns (user_id, error)."""
    email = email.strip().lower()
    row = db.query_one("SELECT id, password_hash, salt FROM users WHERE email = ?", (email,))
    # Same message for unknown email and wrong password (no account enumeration).
    if not row or not hmac.compare_digest(row["password_hash"], _hash(password, row["salt"])):
        return None, "Incorrect email or password."
    return row["id"], None


def get_profile(user_id: int):
    return db.query_one(
        """SELECT u.id, u.email, p.name, p.avatar, p.level, p.daily_goal_xp,
                  p.preferences, p.timezone_offset_min,
                  p.weekly_goal_xp, p.preferred_time, p.daily_minutes
           FROM users u JOIN profiles p ON p.user_id = u.id WHERE u.id = ?""",
        (user_id,),
    )


def update_profile(user_id, name, avatar, level, daily_goal_xp, preferences, tz_offset_min):
    name = name.strip()
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if level not in LEVELS:
        return "Invalid level."
    if not 10 <= int(daily_goal_xp) <= 1000:
        return "Daily goal must be between 10 and 1000 XP."
    db.execute(
        """UPDATE profiles SET name=?, avatar=?, level=?, daily_goal_xp=?,
           preferences=?, timezone_offset_min=? WHERE user_id=?""",
        (name, avatar, level, int(daily_goal_xp), preferences.strip()[:500],
         int(tz_offset_min), user_id),
    )
    return None


def change_password(user_id, old_password, new_password):
    row = db.query_one("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
    if not row or not hmac.compare_digest(row["password_hash"], _hash(old_password, row["salt"])):
        return "Current password is incorrect."
    if len(new_password) < 8:
        return "New password must be at least 8 characters."
    salt = secrets.token_hex(16)
    db.execute(
        "UPDATE users SET password_hash=?, salt=? WHERE id=?",
        (_hash(new_password, salt), salt, user_id),
    )
    return None
