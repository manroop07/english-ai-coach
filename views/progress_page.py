"""My Progress: analytics, Plotly charts, weekly report and AI coach. Real data only."""
import time
from datetime import timedelta

import streamlit as st

from config import XP_RULES
from core import ai, analytics, recommend, schedule
from core import database as db
from core import gamification as gm
from core.ui import empty_state, esc, hero, section, stat_card
from views import charts


def _plot(fig, empty_icon, empty_text):
    if fig is None:
        empty_state(empty_icon, empty_text)
    else:
        st.plotly_chart(fig, config={"displayModeBar": False})


def _celebrate(info):
    msg = f"+{info['xp']} XP 🎉"
    if info["streak_increased"]:
        msg += f"  🔥 {info['streak']}-day streak!"
    if info.get("tasks_completed"):
        msg += f"  ✅ {info['tasks_completed']} planned task(s) completed"
    st.session_state["pending_toast"] = msg
    if info["leveled_up"]:
        st.session_state["pending_balloons"] = True


def _delta_pill(delta, unit):
    if delta is None:
        return '<span class="ec-pill" style="background:#EEE">–</span>'
    if delta == 0:
        return '<span class="ec-pill" style="background:#EEE">no change</span>'
    up = delta > 0
    bg, arrow = ("#E5F8EC", "▲") if up else ("#FFE3DC", "▼")
    return f'<span class="ec-pill" style="background:{bg}">{arrow} {abs(delta):g}{unit}</span>'


def _comparison_table(rows, cur_label, prev_label):
    head = (f'<tr><th align="left">Metric</th><th>{esc(cur_label)}</th><th>{esc(prev_label)}</th>'
            '<th>Change</th></tr>')
    body = ""
    for r in rows:
        f = lambda v: "–" if v is None else f"{v:g}{r['unit']}"
        body += (f'<tr><td><b>{esc(r["metric"])}</b></td><td align="center">{f(r["current"])}</td>'
                 f'<td align="center">{f(r["previous"])}</td>'
                 f'<td align="center">{_delta_pill(r["delta"], r["unit"])}</td></tr>')
    st.markdown(f'<div class="ec-card"><table style="width:100%;border-collapse:separate;border-spacing:0 .4rem">'
                f'{head}{body}</table></div>', unsafe_allow_html=True)


def render(profile):
    uid, tz = profile["id"], profile["timezone_offset_min"]
    hero("My Progress", "See how your English is really improving")

    if not analytics.has_any_data(uid):
        empty_state("📈", "No learning activity yet. Have a conversation, take a quiz or claim your word of the "
                          "day – your charts and reports appear here from real results.")
        return

    today = gm.local_today(tz)
    t_over, t_chart, t_skill, t_gram, t_report, t_ai = st.tabs(
        ["📊 Overview", "📅 Weekly & monthly", "🎯 Skills", "🧩 Grammar & quizzes",
         "📝 Weekly report", "🤖 AI coach"])
    with t_over:
        _overview(uid, tz, today)
    with t_chart:
        _weekly_monthly(uid, tz, today)
    with t_skill:
        _skills(uid)
    with t_gram:
        _grammar_quiz(uid, tz, today)
    with t_report:
        _report(profile, uid, tz, today)
    with t_ai:
        _ai_coach(profile, uid, tz, today)


# ------------------------------------------------------------------ tabs
def _overview(uid, tz, today):
    life = analytics.lifetime_totals(uid)
    hours, mins = divmod(int(life["minutes"]), 60)
    c = st.columns(5)
    with c[0]:
        stat_card("⏱️", f"{hours}h {mins}m" if hours else f"{mins}m", "Learning time (est.)", "#E9E2FF")
    with c[1]:
        stat_card("📅", life["active_days"], "Days practised", "#FFE3DC")
    with c[2]:
        stat_card("📖", life["words_learned"], "Words learned", "#E0F7EC")
    with c[3]:
        stat_card("💬", life["chat_messages"], "Messages sent", "#DDF0FF")
    with c[4]:
        stat_card("🎯", f"{life['quiz_accuracy']}%" if life["quiz_accuracy"] is not None else "–",
                  "Quiz accuracy", "#FFF3C4")
    st.caption("Learning time is **measured** for quizzes and **estimated** for other activities "
               "(time between your actions, up to 3 minutes each).")

    section("🔥 Activity calendar (last 15 weeks)")
    start = today - timedelta(days=104)
    series = analytics.daily_series(uid, tz, start, today)
    _plot(charts.heatmap(series), "🗓️", "Your activity calendar will fill in as you practise.")

    left, right = st.columns([1.2, 1])
    with left:
        section("📊 This week vs last week")
        cur, prev, rows = analytics.this_vs_last_week(uid, tz, today)
        _comparison_table(rows, "This week", "Last week")
    with right:
        section("⏳ Where your time goes (30 days)")
        _plot(charts.breakdown_donut(analytics.activity_breakdown(uid, today - timedelta(days=29), today)),
              "⏳", "No time recorded in the last 30 days.")


def _weekly_monthly(uid, tz, today):
    section("📅 Last 7 days")
    week = analytics.daily_series(uid, tz, today - timedelta(days=6), today)
    _plot(charts.xp_and_time(week), "📉", "No activity in the last 7 days.")

    section("🗓️ Last 30 days")
    month = analytics.daily_series(uid, tz, today - timedelta(days=29), today)
    _plot(charts.xp_and_time(month), "📉", "No activity in the last 30 days.")

    section("📚 Historical comparison – last 8 weeks")
    _plot(charts.weekly_totals_chart(analytics.weekly_totals(uid, tz, today, 8)), "📚",
          "Weekly totals will appear after your first week of practice.")

    section("🆚 This month vs last month")
    cur, prev, rows = analytics.this_vs_last_month(uid, tz, today)
    if prev["activities"] == 0:
        st.info("Last month has no activity yet, so there is nothing to compare with. "
                "Here is this month so far:")
        st.write(f"**{cur['xp']} XP** · **{cur['minutes']} min** · **{cur['active_days']} active days**")
    else:
        _comparison_table(rows, today.strftime("%B (so far)"), (today.replace(day=1) - timedelta(days=1)).strftime("%B"))


def _skills(uid):
    skills = analytics.skill_scores(uid)
    strongest, weakest = analytics.strongest_weakest(skills)
    section("🎯 Skill-wise performance")
    _plot(charts.skills_chart(skills), "🎯", "Practise a little more – skill scores need a minimum amount of data.")
    if strongest:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="ec-good">💪 <b>Strongest:</b> {esc(strongest["skill"])} – {strongest["score"]}%'
                        f'<br><small>{esc(strongest["basis"])}</small></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="ec-fix">🌱 <b>Needs most practice:</b> {esc(weakest["skill"])} – {weakest["score"]}%'
                        f'<br><small>{esc(weakest["basis"])}</small></div>', unsafe_allow_html=True)
    else:
        st.info("Strongest and weakest skills show once at least two skills have enough data.")
    section("How each score is calculated")
    for s in skills:
        val = f"**{s['score']}%**" if s["score"] is not None else "_not enough data_"
        st.markdown(f"- **{s['skill']}**: {val} – {s['basis']}")
    st.caption("Grammar = share of your conversation messages with no mistakes. "
               "Vocabulary = quiz accuracy. Pronunciation will compare speech-to-text with the target "
               "sentence – it is not a phonetic assessment.")


def _grammar_quiz(uid, tz, today):
    section("🧩 Grammar mistakes by category (all time)")
    cats = analytics.grammar_categories(uid)
    _plot(charts.categories_chart(cats), "✅", "No grammar mistakes recorded yet. Chat with the AI teacher to build this.")

    section("📈 Grammar improvement")
    trend = analytics.weekly_grammar_trend(uid, tz, today, 8)
    fig = charts.grammar_trend_chart(trend)
    _plot(fig, "📈", "Chat in at least two different weeks to see whether your grammar is improving.")
    if fig is not None:
        pts = [w for w in trend if w["accuracy"] is not None]
        change = pts[-1]["accuracy"] - pts[0]["accuracy"]
        st.caption(f"Share of messages without mistakes changed by {change:+d} points "
                   f"between the week of {pts[0]['label']} and the week of {pts[-1]['label']}.")

    section("📝 Quiz performance (last 30 days)")
    series = analytics.daily_series(uid, tz, today - timedelta(days=29), today)
    _plot(charts.quiz_trend_chart(series), "📝", "No quizzes in the last 30 days.")

    section("🎤 Pronunciation matching (speech-to-text)")
    rows = db.query_all("SELECT local_date, AVG(score) AS s, COUNT(*) AS n FROM pronunciation_attempts "
                        "WHERE user_id=? GROUP BY local_date ORDER BY local_date", (uid,))
    _plot(charts.score_line([r["local_date"] for r in rows], [round(r["s"]) for r in rows],
                            [r["n"] for r in rows], "Match score (%)", "attempts"),
          "🎤", "No speaking attempts yet. Try Speaking Practice.")
    section("✍️ Writing scores")
    rows = db.query_all("SELECT date(created_at) AS d, AVG(score) AS s, COUNT(*) AS n FROM writing_assessments "
                        "WHERE user_id=? AND score IS NOT NULL GROUP BY date(created_at) ORDER BY d", (uid,))
    _plot(charts.score_line([r["d"] for r in rows], [round(r["s"]) for r in rows],
                            [r["n"] for r in rows], "Writing score", "pieces"),
          "✍️", "No assessed writing yet. Try Grammar & Writing.")


def _report(profile, uid, tz, today):
    section("📝 Weekly performance report")
    cur, prev, rows = analytics.this_vs_last_week(uid, tz, today)
    st.caption(f"Week of {cur['start']:%d %b} to {today:%d %b %Y} (compared with the previous full week)")
    if cur["activities"] == 0:
        st.info("You haven't practised yet this week, so there is nothing to report. "
                "Last week's numbers are shown for reference.")
    _comparison_table(rows, "This week", "Last week")

    cats = analytics.grammar_categories(uid, cur["start"], today)
    if cats:
        st.markdown("**Most common mistakes this week**")
        for c in cats[:4]:
            st.markdown(f'<div class="ec-fix">🧩 {esc(c["category"])} – {c["c"]} time(s)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ec-good">✅ No grammar mistakes recorded this week.</div>', unsafe_allow_html=True)

    md = analytics.weekly_report_markdown(profile["name"], today, cur, prev, rows, cats, analytics.skill_scores(uid))
    st.download_button("⬇️ Download report (.md)", md, file_name=f"english_coach_report_{today.isoformat()}.md",
                       mime="text/markdown")

    ss = st.session_state
    if st.button("🤖 Ask AI to comment on this report", type="secondary", key="ai_comment",
                 disabled=not ai.is_configured() or cur["activities"] + prev["activities"] == 0):
        try:
            with st.spinner("Your coach is reading your report…"):
                facts = analytics.ai_data_summary(uid, tz, today)
                ss["ai_comment"] = ai.generate_text(
                    f"Real learner statistics (JSON): {facts}\nWrite a short, kind progress comment (max 90 words) "
                    "for this English learner. Mention 1 strength and 1 thing to improve. Use ONLY these facts.",
                    "You are a warm English coach. Never invent numbers.")
        except ai.AIError as e:
            st.error(f"😕 {e}")
    if ss.get("ai_comment"):
        st.markdown(f'<div class="ec-tip">🤖 {esc(ss["ai_comment"])}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ AI coach
def _ai_coach(profile, uid, tz, today):
    ss = st.session_state
    level = profile["level"]

    section("💡 Recommended for you")
    recs = recommend.rule_based(uid, tz, today, level)
    if not recs:
        st.markdown('<div class="ec-good">✅ Nothing urgent – your recent practice looks balanced. '
                    'Keep your streak going!</div>', unsafe_allow_html=True)
    for i, r in enumerate(recs):
        st.markdown(f'<div class="ec-tip">{r["icon"]} {esc(r["text"])}</div>', unsafe_allow_html=True)
        if r["page"] and st.button(f"Go to {r['page'].split('  ')[1]}", key=f"ai_rec_{i}", type="secondary"):
            ss["goto"] = r["page"]
            st.rerun()
    hint = recommend.difficulty_suggestion(uid, level)
    if hint:
        st.info(hint)

    _targeted_practice(profile, uid, tz, level)
    _improvement_plan(profile, uid, tz, today, level)


def _targeted_practice(profile, uid, tz, level):
    ss = st.session_state
    section("🎯 Targeted practice (AI-made from your real mistakes)")
    if not ai.is_configured():
        st.warning("Add your Gemini key to use AI practice (see Settings).")
        return

    res = ss.get("tp_result")
    if res:
        pct = round(100 * res["correct"] / res["total"])
        st.markdown(f'<div class="ec-card pop" style="text-align:center"><div style="font-size:2.3rem">'
                    f'{"🏆" if pct >= 80 else "💪"}</div><h3>{esc(res["topic"])}: {res["correct"]}/{res["total"]} ({pct}%)</h3>'
                    f'<p>+{res["xp"]} XP earned</p></div>', unsafe_allow_html=True)
        for r in res["review"]:
            cls, icon = ("ec-good", "✅") if r["ok"] else ("ec-fix", "❌")
            extra = "" if r["ok"] else f"<br>Your answer: {esc(r['chosen'])} · Correct: <b>{esc(r['answer'])}</b>"
            st.markdown(f'<div class="{cls}">{icon} {esc(r["question"])}{extra}'
                        f'<br><small>💡 {esc(r["explanation"])}</small></div>', unsafe_allow_html=True)
        if st.button("Practise again", key="tp_again"):
            ss.pop("tp_result", None)
            st.rerun()
        return

    tp = ss.get("tp_set")
    if not tp:
        topics = recommend.practice_topics(uid)
        if not topics:
            empty_state("🎯", f"No weak areas found yet. Targeted practice unlocks when you repeat the same grammar "
                              f"mistake {analytics.MIN_MISTAKES_FOR_WEAK_AREA}+ times, or have difficult/missed words.")
            return
        topic = st.selectbox("Practise", topics, key="tp_topic_pick")
        if st.button("✨ Make my practice set", key="tp_make"):
            try:
                with st.spinner("Writing questions just for you…"):
                    qs = recommend.generate_exercises(uid, topic, level)
                ss["tp_set"] = {"topic": topic, "questions": qs, "started": time.time()}
                st.rerun()
            except ai.AIError as e:
                st.error(f"😕 {e}")
        return

    with st.form("tp_form"):
        st.caption(f"Topic: {tp['topic']}")
        answers = [st.radio(f"**{i + 1}. {q['question']}**", q["options"], index=None, key=f"tp_q_{i}")
                   for i, q in enumerate(tp["questions"])]
        submitted = st.form_submit_button("Check answers")
    if st.button("Cancel", type="secondary", key="tp_cancel"):
        ss.pop("tp_set", None)
        st.rerun()
    if submitted:
        if any(a is None for a in answers):
            st.error("Please answer every question.")
            return
        qs = tp["questions"]
        correct = sum(1 for q, a in zip(qs, answers) if a == q["answer"])
        xp = correct * XP_RULES["targeted_correct"] + XP_RULES["targeted_complete"]
        recommend.record_exercise_set(uid, tp["topic"], len(qs), correct, gm.local_today(tz).isoformat())
        info = gm.log_activity(uid, "targeted_practice", xp, tz,
                               duration_sec=max(int(time.time() - tp["started"]), 5),
                               detail=f"{tp['topic']} {correct}/{len(qs)}")
        _celebrate(info)
        ss["tp_result"] = {"topic": tp["topic"], "correct": correct, "total": len(qs), "xp": xp,
                           "review": [{"question": q["question"], "answer": q["answer"], "chosen": a,
                                       "ok": a == q["answer"], "explanation": q["explanation"]}
                                      for q, a in zip(qs, answers)]}
        ss.pop("tp_set", None)
        for i in range(len(qs)):
            ss.pop(f"tp_q_{i}", None)
        st.rerun()


def _improvement_plan(profile, uid, tz, today, level):
    ss = st.session_state
    section("🗺️ Weekly improvement plan")
    blocked = recommend.can_use_ai_plan(uid)
    if blocked:
        st.info(blocked)
        return
    if not ai.is_configured():
        st.warning("Add your Gemini key to generate an AI plan (see Settings).")
        return
    if st.button("🧠 Build my improvement plan", key="plan_make"):
        try:
            with st.spinner("Analysing your results…"):
                ss["improve_plan"] = recommend.weekly_improvement_plan(
                    uid, tz, today, level, profile["daily_minutes"], profile["preferences"])
        except ai.AIError as e:
            st.error(f"😕 {e}")
    plan = ss.get("improve_plan")
    if not plan:
        return
    st.markdown(f'<div class="ec-card">{esc(plan["summary"])}</div>', unsafe_allow_html=True)
    for f in plan["focus_areas"]:
        st.markdown(f'<div class="ec-fix">🎯 <b>{esc(f.get("area", ""))}</b><br>{esc(f.get("why", ""))}'
                    f'<br>👉 {esc(f.get("action", ""))}</div>', unsafe_allow_html=True)
    start = today + timedelta(days=1)
    for t in plan["tasks"]:
        d = start + timedelta(days=t["day_offset"])
        st.markdown(f'<div class="ec-tip">📅 <b>{d:%a %d %b}</b> · {esc(t["title"])} '
                    f'({esc(schedule.ACTIVITY_TYPES[t["activity_type"]])}, {t["duration_min"]} min)</div>',
                    unsafe_allow_html=True)
    if plan["tip"]:
        st.caption(f"💡 {plan['tip']}")
    if st.button("➕ Add this plan to My Schedule (from tomorrow)", key="plan_add"):
        added, errors = recommend.add_plan_to_schedule(uid, plan["tasks"], start, profile["preferred_time"])
        if added:
            st.success(f"Added {added} activities to My Schedule.")
        for e in errors[:3]:
            st.error(e)
        ss.pop("improve_plan", None)
