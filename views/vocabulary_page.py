import random
import time

import streamlit as st

from config import XP_RULES
from core import gamification as gm
from core import vocab
from core.ui import empty_state, esc, hero, section


def _celebrate(info, extra=""):
    msg = f"+{info['xp']} XP 🎉{extra}"
    if info["streak_increased"]:
        msg += f"  🔥 {info['streak']}-day streak!"
    if info.get("tasks_completed"):
        msg += f"  ✅ {info['tasks_completed']} planned task(s) completed"
    st.session_state["pending_toast"] = msg
    if info["leveled_up"]:
        st.session_state["pending_balloons"] = True


def render(profile):
    uid, tz, level = profile["id"], profile["timezone_offset_min"], profile["level"]
    hero("Vocabulary", f"Build your word power · {level} level")

    tab_wod, tab_quiz, tab_cards, tab_dict = st.tabs(
        ["🌟 Word of the day", "📝 Quiz", "🃏 Flashcards & revision", "📖 My dictionary"])

    with tab_wod:
        _word_of_day(uid, tz, level)
    with tab_quiz:
        _quiz(uid, tz, level)
    with tab_cards:
        _flashcards(uid, tz)
    with tab_dict:
        _dictionary(uid)


def _word_card(w):
    st.markdown(
        f"""<div class="ec-card pop">
        <div style="font-size:2.2rem;font-weight:900;color:#7C5CFC">{esc(w['word'])}</div>
        <div style="font-size:1.1rem;margin:.3rem 0"><b>Meaning:</b> {esc(w['meaning'])}</div>
        <div style="font-size:1.1rem"><b>Hindi:</b> {esc(w['hindi'])}</div>
        <div class="ec-tip">💬 {esc(w['example'])}</div>
        <div><span class="ec-pill" style="background:#E0F7EC">Synonyms: {esc(w['synonyms'])}</span>
        <span class="ec-pill" style="background:#FFE3DC">Antonyms: {esc(w['antonyms'])}</span></div>
        </div>""", unsafe_allow_html=True)


def _word_of_day(uid, tz, level):
    today = gm.local_today(tz)
    w = vocab.word_of_the_day(uid, level, today)
    _word_card(w)
    if vocab.word_of_day_claimed(uid, today.isoformat()):
        st.success("✅ You've already collected today's word. Come back tomorrow for a new one!")
    elif st.button("I've learned it! (+%d XP)" % XP_RULES["word_of_day"], key="claim_wod"):
        vocab.mark_learned(uid, w["word"])
        info = gm.log_activity(uid, "word_of_day", XP_RULES["word_of_day"], tz, detail=w["word"])
        _celebrate(info)
        st.rerun()


def _quiz(uid, tz, level):
    ss = st.session_state
    summary = vocab.quiz_summary(uid)
    c1, c2, c3 = st.columns(3)
    c1.metric("Quizzes taken", summary["quizzes"])
    c2.metric("Questions answered", summary["total"])
    c3.metric("Accuracy", f"{summary['accuracy']}%" if summary["accuracy"] is not None else "–")

    result = ss.get("quiz_result")
    if result:
        pct = round(100 * result["correct"] / result["total"])
        st.markdown(f'<div class="ec-card pop" style="text-align:center"><div style="font-size:2.5rem">'
                    f'{"🏆" if pct >= 80 else "💪"}</div><h2>{result["correct"]} / {result["total"]} correct ({pct}%)</h2>'
                    f'<p>+{result["xp"]} XP earned</p></div>', unsafe_allow_html=True)
        for r in result["review"]:
            cls = "ec-good" if r["ok"] else "ec-fix"
            icon = "✅" if r["ok"] else "❌"
            extra = "" if r["ok"] else f"<br>Your answer: {esc(r['chosen'])}"
            st.markdown(f'<div class="{cls}">{icon} <b>{esc(r["word"])}</b> – {esc(r["answer"])}{extra}</div>',
                        unsafe_allow_html=True)
        if st.button("Take another quiz", key="quiz_again"):
            ss.pop("quiz_result", None)
            st.rerun()
        return

    quiz = ss.get("quiz")
    if not quiz:
        n = st.radio("Quiz length", [5, 10], horizontal=True, format_func=lambda x: f"{x} words")
        if st.button("Start quiz", key="start_quiz"):
            ss["quiz"] = {"n": n, "questions": vocab.build_quiz(uid, level, n), "started": time.time()}
            st.rerun()
        return

    with st.form("quiz_form"):
        st.caption("Choose the correct meaning for each word.")
        answers = []
        for i, q in enumerate(quiz["questions"]):
            answers.append(st.radio(f"**{i + 1}. {q['word']}**", q["options"], index=None, key=f"q_{i}"))
        submitted = st.form_submit_button("Submit quiz")
    if st.button("Cancel quiz", type="secondary", key="cancel_quiz"):
        ss.pop("quiz", None)
        st.rerun()

    if submitted:
        if any(a is None for a in answers):
            st.error("Please answer every question before submitting.")
            return
        graded = [(q["word"], a == q["answer"]) for q, a in zip(quiz["questions"], answers)]
        correct = vocab.record_quiz(uid, f"{len(graded)}-word", graded, gm.local_today(tz).isoformat())
        xp = correct * XP_RULES["quiz_correct"] + XP_RULES["quiz_complete"]
        secs = int(time.time() - quiz.get("started", time.time()))  # real, measured quiz time
        info = gm.log_activity(uid, "quiz_complete", xp, tz, duration_sec=max(secs, 5),
                               detail=f"{correct}/{len(graded)}")
        _celebrate(info)
        ss["quiz_result"] = {
            "correct": correct, "total": len(graded), "xp": xp,
            "review": [{"word": q["word"], "answer": q["answer"], "chosen": a, "ok": a == q["answer"]}
                       for q, a in zip(quiz["questions"], answers)],
        }
        ss.pop("quiz", None)
        for i in range(len(graded)):
            ss.pop(f"q_{i}", None)
        st.rerun()


def _flashcards(uid, tz):
    ss = st.session_state
    deck_name = st.radio("Deck", ["All my words", "Revision (difficult or missed)"], horizontal=True)
    words = vocab.my_words(uid, only_revision=deck_name.startswith("Revision"))
    if not words:
        empty_state("🃏", "No words here yet. Claim a word of the day or take a quiz to fill your deck!"
                    if deck_name == "All my words" else
                    "Nothing to revise yet. Words you miss in quizzes or mark as difficult will appear here.")
        return
    ss.setdefault("card_i", 0)
    ss.setdefault("card_show", False)
    ss["card_i"] %= len(words)
    w = words[ss["card_i"]]
    st.caption(f"Card {ss['card_i'] + 1} of {len(words)}")
    if ss["card_show"]:
        st.markdown(f'<div class="flash pop"><div class="w">{esc(w["word"])}</div>'
                    f'<p><b>{esc(w["meaning"])}</b></p><p>{esc(w["hindi"])}</p>'
                    f'<p><i>{esc(w["example"])}</i></p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="flash"><div class="w">{esc(w["word"])}</div>'
                    f'<p>Do you remember the meaning?</p></div>', unsafe_allow_html=True)

    a, b, c, d = st.columns(4)
    if a.button("👀 Show answer", key="fc_show", type="secondary", use_container_width=True):
        ss["card_show"] = True
        st.rerun()
    if b.button("✅ I know it", key="fc_know", use_container_width=True):
        vocab.toggle_difficult(uid, w["id"], False)
        if vocab.mark_learned(uid, w["word"]):
            info = gm.log_activity(uid, "flashcard_review", XP_RULES["flashcard_review"], tz, detail=w["word"])
            _celebrate(info)
        ss["card_i"] += 1
        ss["card_show"] = False
        st.rerun()
    if c.button("🔁 Still learning", key="fc_learn", type="secondary", use_container_width=True):
        vocab.toggle_difficult(uid, w["id"], True)
        ss["card_i"] += 1
        ss["card_show"] = False
        st.rerun()
    if d.button("🔀 Shuffle", key="fc_shuf", type="secondary", use_container_width=True):
        ss["card_i"] = random.randrange(len(words))
        ss["card_show"] = False
        st.rerun()


def _dictionary(uid):
    section("My personal dictionary")
    only_hard = st.toggle("Show only difficult words", key="dict_hard")
    words = vocab.my_words(uid, only_difficult=only_hard)
    if not words:
        empty_state("📖", "Your dictionary is empty. Words appear here as you learn them." if not only_hard
                    else "You haven't marked any words as difficult.")
    for w in words:
        with st.expander(f"{'⭐ ' if w['difficult'] else ''}{w['word']} — {w['meaning']}"):
            if w["hindi"]:
                st.write(f"**Hindi:** {w['hindi']}")
            if w["example"]:
                st.write(f"**Example:** {w['example']}")
            if w["synonyms"]:
                st.write(f"**Synonyms:** {w['synonyms']}  \n**Antonyms:** {w['antonyms']}")
            st.caption(f"Correct: {w['times_correct']} · Missed: {w['times_wrong']} · "
                       f"{'Learned ✅' if w['learned'] else 'Not learned yet'}")
            label = "Remove from difficult" if w["difficult"] else "⭐ Mark as difficult"
            if st.button(label, key=f"dif_{w['id']}", type="secondary"):
                vocab.toggle_difficult(uid, w["id"], not w["difficult"])
                st.rerun()

    section("Add your own word")
    with st.form("add_word", clear_on_submit=True):
        c1, c2 = st.columns(2)
        word = c1.text_input("Word")
        hindi = c2.text_input("Hindi meaning (optional)")
        meaning = st.text_input("Meaning in simple English")
        example = st.text_input("Example sentence (optional)")
        if st.form_submit_button("Save word"):
            err = vocab.add_custom_word(uid, word, meaning, hindi, example)
            if err:
                st.error(err)
            else:
                st.success(f"Saved “{word.strip().lower()}” to your dictionary.")
