"""Gemini wrapper. The API key is read from the environment (.env) on the server only."""
import json
import re

import streamlit as st

from config import GEMINI_API_KEY, GEMINI_MODEL


class AIError(Exception):
    """Raised with a friendly message that is safe to show to the user."""


def _api_key() -> str:
    # A key pasted in Settings lives only in this browser session's server memory.
    return st.session_state.get("session_api_key") or GEMINI_API_KEY


def is_configured() -> bool:
    return bool(_api_key())


def _client():
    key = _api_key()
    if not key:
        raise AIError(
            "No Gemini API key found. Add GEMINI_API_KEY to your .env file "
            "(see .env.example) and restart the app."
        )
    try:
        from google import genai
    except ImportError:
        raise AIError("The 'google-genai' package is missing. Run: pip install -r requirements.txt")
    return genai.Client(api_key=key)


def _call(contents, system_instruction, json_mode, temperature):
    from google.genai import types

    client = _client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
    except Exception as e:  # network, quota, bad key ...
        msg = str(e).lower()
        if "api key" in msg or "permission" in msg or "401" in msg or "403" in msg:
            raise AIError("Gemini rejected the API key. Please check it in your .env file.")
        if "429" in msg or "quota" in msg or "resource_exhausted" in msg:
            raise AIError("Gemini rate limit reached. Please wait a minute and try again.")
        if "timeout" in msg or "connect" in msg or "network" in msg:
            raise AIError("Could not reach Gemini. Please check your internet connection.")
        raise AIError("The AI service had a problem. Please try again in a moment.")
    text = (resp.text or "").strip()
    if not text:
        raise AIError("The AI returned an empty answer. Please try again.")
    return text


def generate_text(prompt, system_instruction="", temperature=0.7) -> str:
    return _call(prompt, system_instruction, False, temperature)


def generate_json(prompt, system_instruction="", temperature=0.4):
    text = _call(prompt, system_instruction, True, temperature)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise AIError("The AI answer could not be read. Please try again.")


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Speech-to-text with Gemini. Returns exactly what was heard (may be empty). Raises AIError."""
    from google.genai import types

    part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    instruction = ("Transcribe this audio exactly as spoken, word for word, in English. "
                   "Do NOT fix grammar, do NOT complete unclear words, do not add punctuation commentary. "
                   "If you hear nothing intelligible, answer with exactly: [unclear]. Return only the transcript.")
    text = _call([part, instruction], "You are a literal speech transcriber.", False, 0.0)
    return "" if text.strip().lower() in ("[unclear]", "unclear") else text.strip()
