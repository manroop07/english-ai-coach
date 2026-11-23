import streamlit as st

from config import CONVERSATION_TOPICS, XP_RULES
from core import ai, conversation as conv
from core import gamification as gm
from core.ui import empty_state, esc, hero


def _show_feedback(fb):
    if fb.get("has_mistakes"):
        st.markdown(f'<div class="ec-fix">✏️ <b>Better:</b> {esc(fb.get("corrected", ""))}</div>', unsafe_allow_html=True)
        for m in fb.get("mistakes", []):
            st.markdown(
                f'<div class="ec-fix">❌ <i>{esc(m.get("original", ""))}</i><br>'
                f'💡 <b>{esc(m.get("category", ""))}:</b> {esc(m.get("explanation", ""))}</div>',
                unsafe_allow_html=True)
    else:
        st.markdown('<div class="ec-good">✅ No mistakes – your English was correct!</div>', unsafe_allow_html=True)
    if fb.get("better_sentence"):
        st.markdown(f'<div class="ec-tip">✨ <b>More natural:</b> {esc(fb["better_sentence"])}</div>', unsafe_allow_html=True)
    if fb.get("encouragement"):
        st.caption(fb["encouragement"])


def render(profile):
    uid, tz = profile["id"], profile["timezone_offset_min"]
    hero("AI Conversation", "Chat with your friendly English teacher and get instant feedback")

    if not ai.is_configured():
        st.warning("Gemini is not set up yet. Add your key to the `.env` file (see `.env.example`) and restart the app.")

    ss = st.session_state
    ss.setdefault("chat_session", conv.new_session_id())
    ss.setdefault("chat_topic", "Daily life")
    ss.setdefault("chat_msgs", [])
    topics = list(CONVERSATION_TOPICS)

    main, side = st.columns([3, 1.2])
    with side:
        st.markdown("**Topic**")
        topic = st.selectbox("Topic", topics, index=topics.index(ss["chat_topic"]),
                             label_visibility="collapsed")
        if topic != ss["chat_topic"]:
            ss["chat_topic"] = topic
            ss["chat_session"] = conv.new_session_id()
            ss["chat_msgs"] = []
        if st.button("➕ New conversation", type="secondary", use_container_width=True):
            ss["chat_session"] = conv.new_session_id()
            ss["chat_msgs"] = []
            st.rerun()

        st.markdown("**Past conversations**")
        sessions = conv.list_sessions(uid)
        if not sessions:
            st.caption("Your saved chats will show up here.")
        for s in sessions[:8]:
            if st.button(f"{s['topic']} · {s['started'][:10]}", key=f"sess_{s['session_id']}",
                         type="secondary", use_container_width=True):
                ss["chat_session"] = s["session_id"]
                ss["chat_topic"] = s["topic"]
                ss["chat_msgs"] = conv.load_session(uid, s["session_id"])
                st.rerun()

    with main:
        msgs = ss["chat_msgs"]
        if not msgs:
            empty_state("💬", f"Say hello to start a “{ss['chat_topic']}” conversation. "
                              "Don't worry about mistakes – that's how we learn!")
        for m in msgs:
            is_user = m["role"] == "user"
            with st.chat_message("user" if is_user else "assistant", avatar=profile["avatar"] if is_user else "🦉"):
                st.write(m["content"])

        last = next((m for m in reversed(msgs) if m["role"] == "assistant" and m.get("feedback")), None)
        if last:
            st.markdown("**📝 Feedback on your last message**")
            _show_feedback(last["feedback"])

        text = st.chat_input("Type your message in English…", disabled=not ai.is_configured())
        if text:
            text = text.strip()[:600]
            if len(text) < 2:
                st.error("Please write a little more.")
            else:
                _handle(profile, uid, tz, text)


def _handle(profile, uid, tz, text):
    ss = st.session_state
    history = [{"role": m["role"], "content": m["content"]} for m in ss["chat_msgs"]]
    try:
        with st.spinner("Your teacher is thinking…"):
            result = conv.send_message(uid, ss["chat_session"], ss["chat_topic"], profile["level"],
                                       profile["preferences"], history, text)
    except ai.AIError as e:
        st.error(f"😕 {e}")
        return
    conv.save_turn(uid, ss["chat_session"], ss["chat_topic"], text, result, gm.local_today(tz).isoformat())
    ss["chat_msgs"].append({"role": "user", "content": text})
    ss["chat_msgs"].append({"role": "assistant", "content": result["reply"], "feedback": {
        k: result[k] for k in ("has_mistakes", "corrected", "mistakes", "better_sentence", "encouragement")}})
    info = gm.log_activity(uid, "conversation_turn", XP_RULES["conversation_turn"], tz, detail=ss["chat_topic"])
    ss["pending_toast"] = f"+{info['xp']} XP 🎉" + (f"  🔥 {info['streak']}-day streak!" if info["streak_increased"] else "")
    if info["tasks_completed"]:
        ss["pending_toast"] += f"  ✅ {info['tasks_completed']} planned task(s) completed"
    if info["leveled_up"]:
        ss["pending_balloons"] = True
    st.rerun()
