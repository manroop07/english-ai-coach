"""Grammar & Writing: AI grammar lessons with practice, and AI writing assessment."""
import time

import streamlit as st

from config import WRITING_MIN_WORDS, XP_RULES
from core import ai, grammar, recommend
from core import database as db
from core import gamification as gm
from core.ui import empty_state, esc, hero, ring, section


def _celebrate(info):
    msg = f"+{info['xp']} XP 🎉"
    if info["streak_increased"]:
        msg += f"  🔥 {info['streak']}-day streak!"
    if info.get("tasks_completed"):
        msg += f"  ✅ {info['tasks_completed']} planned task(s) completed"
    st.session_state["pending_toast"] = msg
    if info["leveled_up"]:
        st.session_state["pending_balloons"] = True


def render(profile):
    uid, tz, level = profile["id"], profile["timezone_offset_min"], profile["level"]
    hero("Grammar & Writing", f"Learn the rules, then use them · {level} level")
    if not ai.is_configured():
        st.warning("Add your Gemini key to the `.env` file to use lessons and writing feedback.")
    t1, t2, t3 = st.tabs(["📖 Grammar lessons", "✍️ Write & get feedback", "🗂️ My writing"])
    with t1:
        _lessons(uid, tz, level)
    with t2:
        _write(uid, tz, level)
    with t3:
        _history(uid)


# ------------------------------------------------------------------ lessons
def _lessons(uid, tz, level):
    ss = st.session_state
    topic = st.selectbox("Choose a topic", list(grammar.GRAMMAR_TOPICS), key="gl_topic")
    key = f"lesson::{topic}::{level}"
    if st.button("📖 Teach me this topic", key="gl_teach", disabled=not ai.is_configured()):
        try:
            with st.spinner("Preparing your lesson…"):
                ss[key] = grammar.generate_lesson(topic, level)
            ss.pop("gl_set", None)
            ss.pop("gl_result", None)
        except ai.AIError as e:
            st.error(f"😕 {e}")
    lesson = ss.get(key)
    if not lesson:
        empty_state("📖", "Pick a topic and press “Teach me” – the AI writes a short lesson for your level.")
        return

    st.markdown(f'<div class="ec-card pop"><h3>{esc(topic)}</h3><p>{esc(lesson["explanation"])}</p></div>',
                unsafe_allow_html=True)
    for r in lesson["rules"]:
        st.markdown(f'<div class="ec-tip">📌 {esc(r)}</div>', unsafe_allow_html=True)
    for e in lesson["examples"]:
        st.markdown(f'<div class="ec-fix">❌ {esc(e.get("wrong", ""))}</div>'
                    f'<div class="ec-good">✅ {esc(e.get("right", ""))}</div>', unsafe_allow_html=True)
    if lesson["tip"]:
        st.caption(f"💡 {lesson['tip']}")

    section("🧪 Practice quiz")
    _lesson_quiz(uid, tz, level, topic)


def _lesson_quiz(uid, tz, level, topic):
    ss = st.session_state
    res = ss.get("gl_result")
    if res and res["topic"] == topic:
        st.markdown(f'<div class="ec-card pop" style="text-align:center"><h3>{res["correct"]}/{res["total"]} correct</h3>'
                    f'<p>+{res["xp"]} XP</p></div>', unsafe_allow_html=True)
        for r in res["review"]:
            cls, icon = ("ec-good", "✅") if r["ok"] else ("ec-fix", "❌")
            extra = "" if r["ok"] else f"<br>Correct: <b>{esc(r['answer'])}</b>"
            st.markdown(f'<div class="{cls}">{icon} {esc(r["question"])}{extra}<br><small>💡 {esc(r["explanation"])}</small></div>',
                        unsafe_allow_html=True)
        if st.button("Try a new quiz", key="gl_again"):
            ss.pop("gl_result", None)
            st.rerun()
        return
    tp = ss.get("gl_set")
    if not tp or tp["topic"] != topic:
        if st.button("✨ Make a 5-question quiz", key="gl_make", disabled=not ai.is_configured()):
            try:
                with st.spinner("Writing questions…"):
                    qs = recommend.generate_exercises(uid, topic, level)
                ss["gl_set"] = {"topic": topic, "questions": qs, "started": time.time()}
                st.rerun()
            except ai.AIError as e:
                st.error(f"😕 {e}")
        return
    with st.form("gl_form"):
        answers = [st.radio(f"**{i + 1}. {q['question']}**", q["options"], index=None, key=f"gl_q_{i}")
                   for i, q in enumerate(tp["questions"])]
        submitted = st.form_submit_button("Check answers")
    if submitted:
        if any(a is None for a in answers):
            st.error("Please answer every question.")
            return
        qs = tp["questions"]
        correct = sum(1 for q, a in zip(qs, answers) if a == q["answer"])
        xp = correct * XP_RULES["grammar_correct"] + XP_RULES["grammar_complete"]
        recommend.record_exercise_set(uid, topic, len(qs), correct, gm.local_today(tz).isoformat())
        info = gm.log_activity(uid, "grammar_lesson", xp, tz,
                               duration_sec=max(int(time.time() - tp["started"]), 5), detail=f"{topic} {correct}/{len(qs)}")
        _celebrate(info)
        ss["gl_result"] = {"topic": topic, "correct": correct, "total": len(qs), "xp": xp,
                           "review": [{"question": q["question"], "answer": q["answer"], "ok": a == q["answer"],
                                       "explanation": q["explanation"]} for q, a in zip(qs, answers)]}
        ss.pop("gl_set", None)
        for i in range(len(qs)):
            ss.pop(f"gl_q_{i}", None)
        st.rerun()


# ------------------------------------------------------------------ writing
def _write(uid, tz, level):
    ss = st.session_state
    c1, c2 = st.columns([1, 2])
    kind = c1.selectbox("What are you writing?", list(grammar.WRITING_KINDS), key="wr_kind")
    topic = c2.text_input("Topic (optional)", key="wr_topic", max_chars=120,
                          placeholder="e.g. My weekend, Asking for leave, Why reading matters")
    need = WRITING_MIN_WORDS[kind]
    text = st.text_area(f"Your {kind.lower()} (at least {need} words)", height=220, key="wr_text",
                        max_chars=grammar.MAX_CHARS)
    n = grammar.count_words(text)
    st.caption(f"{n} words" + ("" if n >= need else f" · {need - n} more needed"))

    if st.button("🔍 Get feedback", key="wr_go", disabled=not ai.is_configured()):
        err = grammar.validate_writing(kind, text)
        if err:
            st.error(err)
        else:
            repeat = db.query_one("SELECT 1 AS x FROM writing_assessments WHERE user_id=? AND text=?",
                                  (uid, text.strip())) is not None
            try:
                with st.spinner("Your tutor is reading carefully…"):
                    fb = grammar.assess_writing(uid, kind, text.strip(), level, topic, gm.local_today(tz).isoformat())
            except ai.AIError as e:
                st.error(f"😕 {e}")
                return
            if repeat:
                ss["wr_note"] = "You already submitted this exact text, so no XP this time."
            else:
                _celebrate(gm.log_activity(uid, "writing", XP_RULES["writing_piece"], tz, detail=kind))
                ss["wr_note"] = f"+{XP_RULES['writing_piece']} XP earned"
            ss["wr_fb"] = fb
    fb = ss.get("wr_fb")
    if fb:
        _show_feedback(fb)
        st.caption(ss.get("wr_note", ""))


def _show_feedback(fb):
    section("📋 Your feedback")
    ring(fb["score"], "Writing score")
    if fb["summary"]:
        st.markdown(f'<div class="ec-card">{esc(fb["summary"])}</div>', unsafe_allow_html=True)
    for s in fb["strengths"]:
        st.markdown(f'<div class="ec-good">💪 {esc(s)}</div>', unsafe_allow_html=True)
    if fb["corrected"]:
        st.markdown("**✏️ Corrected version**")
        st.markdown(f'<div class="ec-tip">{esc(fb["corrected"])}</div>', unsafe_allow_html=True)
    if fb["issues"]:
        st.markdown("**🧩 Mistakes explained**")
        for i in fb["issues"]:
            st.markdown(f'<div class="ec-fix">❌ <i>{esc(i["original"])}</i><br>💡 <b>{esc(i["category"])}:</b> '
                        f'{esc(i["explanation"])}</div>', unsafe_allow_html=True)
    if fb["sentence_improvements"]:
        st.markdown("**✨ Sentence improvements**")
        for s in fb["sentence_improvements"]:
            st.markdown(f'<div class="ec-tip">{esc(s.get("original", ""))}<br>➜ <b>{esc(s.get("better", ""))}</b></div>',
                        unsafe_allow_html=True)
    if fb["vocabulary_suggestions"]:
        st.markdown("**📚 Vocabulary upgrades**")
        for v in fb["vocabulary_suggestions"]:
            st.markdown(f'<div class="ec-good"><b>{esc(v.get("word", ""))}</b> ➜ <b>{esc(v.get("better_word", ""))}</b>'
                        f' – {esc(v.get("why", ""))}</div>', unsafe_allow_html=True)


def _history(uid):
    rows = grammar.history(uid)
    if not rows:
        empty_state("🗂️", "Your assessed writing will be saved here.")
        return
    for r in rows:
        with st.expander(f"{r['created_at'][:10]} · {r['kind']} · score {r['score']}"):
            st.write(r["text"])
            if r["feedback"]:
                _show_feedback(r["feedback"])
