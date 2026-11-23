"""Speaking Practice: read-aloud matching and roleplay. Scores are speech-to-text matching only."""
import json
import time

import streamlit as st
import streamlit.components.v1 as components

from config import PRONUNCIATION_PASS, XP_RULES
from core import ai, conversation as conv, speaking
from core import gamification as gm
from core.ui import empty_state, esc, hero, section
from views.conversation_page import _show_feedback

ROLES = {"Interviewer": "Job interview", "Friend": "Roleplay: friend", "Teacher": "Roleplay: teacher",
         "Shopkeeper": "Roleplay: shopkeeper"}


def speak_button(text, key):
    """Browser text-to-speech (no server, no key). Works in Chrome, Edge and Safari."""
    components.html(
        f"""<button id="b" style="font:800 15px Nunito,sans-serif;border:none;border-radius:14px;padding:10px 18px;
        background:#E9E2FF;color:#6C4DF0;cursor:pointer">🔊 Listen</button>
        <script>document.getElementById('b').onclick=function(){{
          if(!('speechSynthesis' in window)){{this.textContent='Not supported in this browser';return;}}
          window.speechSynthesis.cancel();var u=new SpeechSynthesisUtterance({json.dumps(text)});
          u.lang='en-US';u.rate=0.85;window.speechSynthesis.speak(u);}};</script>""", height=56)


def _celebrate(info):
    msg = f"+{info['xp']} XP 🎉"
    if info["streak_increased"]:
        msg += f"  🔥 {info['streak']}-day streak!"
    if info.get("tasks_completed"):
        msg += f"  ✅ {info['tasks_completed']} planned task(s) completed"
    st.session_state["pending_toast"] = msg
    if info["leveled_up"]:
        st.session_state["pending_balloons"] = True


def _transcribe(audio):
    data = audio.getvalue()
    if len(data) < 3000:
        raise ai.AIError("That recording was too short. Press record, speak, then stop.")
    return ai.transcribe_audio(data, getattr(audio, "type", None) or "audio/wav")


def render(profile):
    uid, tz, level = profile["id"], profile["timezone_offset_min"], profile["level"]
    hero("Speaking Practice", "Listen, speak and see how well your words match")
    if not ai.is_configured():
        st.warning("Add your Gemini key to the `.env` file – it is used to turn your voice into text.")
    if not hasattr(st, "audio_input"):
        st.error("Your Streamlit is too old for voice recording. Run: pip install -U streamlit")
        return
    t1, t2, t3 = st.tabs(["🎤 Read aloud", "🎭 Roleplay", "📜 History"])
    with t1:
        _read_aloud(uid, tz, level)
    with t2:
        _roleplay(profile, uid, tz, level)
    with t3:
        _history(uid)


def _read_aloud(uid, tz, level):
    ss = st.session_state
    st.info("ℹ️ **How scoring works:** your voice is converted to text and compared word by word with the sentence. "
            "A high score means the words were recognised – it is **not** a phonetic pronunciation test, and the "
            "transcriber can be forgiving. Use it as a guide, and use 🔊 Listen to copy the sound.")
    c1, c2 = st.columns([2, 1])
    scenario = c1.selectbox("Real-life scenario", list(speaking.SCENARIOS), key="sp_scn")
    if c2.button("✨ New sentences", key="sp_gen", disabled=not ai.is_configured()):
        try:
            with st.spinner("Writing sentences…"):
                ss["sp_sentences"] = speaking.generate_sentences(level, scenario)
            ss.pop("sp_result", None)
        except ai.AIError as e:
            st.error(f"😕 {e}")
    options = list(ss.get("sp_sentences", []))
    custom = st.text_input("…or type your own sentence", key="sp_custom", max_chars=200)
    if custom.strip():
        target = custom.strip()
    elif options:
        target = st.radio("Pick a sentence", options, key="sp_pick")
    else:
        empty_state("🎤", "Press “New sentences” to get practice sentences, or type your own.")
        return

    st.markdown(f'<div class="flash"><div class="w" style="font-size:1.6rem">{esc(target)}</div></div>',
                unsafe_allow_html=True)
    speak_button(target, "sp_tts")
    audio = st.audio_input("Record your voice", key=f"sp_audio_{ss.get('sp_n', 0)}")
    if st.button("✅ Check my speech", key="sp_check", disabled=audio is None or not ai.is_configured()):
        try:
            with st.spinner("Listening…"):
                heard = _transcribe(audio)
        except ai.AIError as e:
            st.error(f"😕 {e}")
            return
        res = speaking.compare(target, heard)
        first_pass = res["score"] >= PRONUNCIATION_PASS and not speaking.already_passed(uid, target)
        speaking.save_attempt(uid, target, heard, res["score"], scenario, gm.local_today(tz).isoformat())
        xp = 0
        if first_pass:
            xp = XP_RULES["pronunciation_good"]
            _celebrate(gm.log_activity(uid, "pronunciation", xp, tz, detail=target[:60]))
        ss["sp_result"] = {"target": target, "heard": heard, "res": res, "xp": xp}
        ss["sp_n"] = ss.get("sp_n", 0) + 1  # resets the recorder
        st.rerun()

    r = ss.get("sp_result")
    if r and r["target"] == target:
        res = r["res"]
        words = " ".join(f'<span style="padding:2px 8px;border-radius:10px;background:{"#E5F8EC" if w["ok"] else "#FFE3DC"};'
                         f'font-weight:800">{"✅" if w["ok"] else "❌"} {esc(w["word"])}</span>' for w in res["words"])
        st.markdown(f'<div class="ec-card pop"><h3>Match score: {res["score"]}%</h3>'
                    f'<p><b>We heard:</b> {esc(r["heard"]) or "<i>nothing clear</i>"}</p><p>{words}</p>'
                    + (f'<p>Extra words heard: {esc(", ".join(res["extra"]))}</p>' if res["extra"] else "")
                    + f'<p>{"+%d XP earned" % r["xp"] if r["xp"] else "Reach " + str(PRONUNCIATION_PASS) + "% on a new sentence to earn XP."}</p></div>',
                    unsafe_allow_html=True)


def _roleplay(profile, uid, tz, level):
    ss = st.session_state
    ss.setdefault("rp_session", conv.new_session_id())
    ss.setdefault("rp_msgs", [])
    role = st.selectbox("Who do you want to talk to?", list(ROLES), key="rp_role")
    topic = ROLES[role]
    if ss.get("rp_topic") != topic:
        ss["rp_topic"], ss["rp_session"], ss["rp_msgs"] = topic, conv.new_session_id(), []
    if st.button("➕ Restart roleplay", type="secondary", key="rp_new"):
        ss["rp_session"], ss["rp_msgs"] = conv.new_session_id(), []
        st.rerun()

    msgs = ss["rp_msgs"]
    if not msgs:
        empty_state("🎭", f"Say hello to your {role.lower()} – type below or record your voice.")
    for m in msgs:
        user = m["role"] == "user"
        with st.chat_message("user" if user else "assistant", avatar=profile["avatar"] if user else "🎭"):
            st.write(m["content"])
    last = next((m for m in reversed(msgs) if m["role"] == "assistant"), None)
    if last:
        speak_button(last["content"], "rp_tts")
        if last.get("feedback"):
            _show_feedback(last["feedback"])

    with st.form("rp_form", clear_on_submit=True):
        typed = st.text_input("Type your reply", max_chars=400)
        sent = st.form_submit_button("Send")
    audio = st.audio_input("…or speak your reply", key=f"rp_audio_{ss.get('rp_n', 0)}")
    voice = st.button("📨 Send voice reply", key="rp_voice", disabled=audio is None or not ai.is_configured())

    text = None
    if sent and typed.strip():
        text = typed.strip()
    elif voice:
        try:
            with st.spinner("Listening…"):
                text = _transcribe(audio)
        except ai.AIError as e:
            st.error(f"😕 {e}")
            return
        if not text:
            st.error("I couldn't hear anything clear. Please try again.")
            return
        st.caption(f"We heard: “{text}”")
    if text:
        history = [{"role": m["role"], "content": m["content"]} for m in msgs]
        try:
            with st.spinner("Thinking…"):
                result = conv.send_message(uid, ss["rp_session"], topic, level, profile["preferences"], history, text)
        except ai.AIError as e:
            st.error(f"😕 {e}")
            return
        conv.save_turn(uid, ss["rp_session"], topic, text, result, gm.local_today(tz).isoformat())
        msgs.append({"role": "user", "content": text})
        msgs.append({"role": "assistant", "content": result["reply"], "feedback": {
            k: result[k] for k in ("has_mistakes", "corrected", "mistakes", "better_sentence", "encouragement")}})
        _celebrate(gm.log_activity(uid, "conversation_turn", XP_RULES["conversation_turn"], tz, detail=topic))
        ss["rp_n"] = ss.get("rp_n", 0) + 1
        st.rerun()


def _history(uid):
    s = speaking.stats(uid)
    if not s["attempts"]:
        empty_state("📜", "Your speaking attempts will be listed here.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Attempts", s["attempts"])
    c2.metric("Average match", f"{s['average']}%")
    c3.metric("Best", f"{s['best']}%")
    st.caption("Match = speech-to-text vs target sentence, not phonetic accuracy.")
    for r in speaking.history(uid):
        st.markdown(f'<div class="{"ec-good" if r["score"] >= PRONUNCIATION_PASS else "ec-fix"}">'
                    f'<b>{r["score"]}%</b> · {esc(r["created_at"][:16])} · {esc(r["scenario"])}<br>'
                    f'🎯 {esc(r["target"])}<br>👂 {esc(r["recognized"]) or "–"}</div>', unsafe_allow_html=True)
