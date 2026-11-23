"""In-app reminder banner (refreshes every minute) + optional browser notifications."""
import json

import streamlit as st
import streamlit.components.v1 as components

from core import gamification as gm
from core import schedule
from core.ui import esc


def _browser_notifications(due_tasks):
    payload = json.dumps([{"id": t["id"], "title": t["title"], "time": t["scheduled_time"]} for t in due_tasks])
    payload = payload.replace("</", "<\\/")
    components.html(
        f"""
<div style="font-family:Nunito,sans-serif;font-size:13px;color:#7A7394">
  <span id="msg"></span>
  <button id="btn" style="display:none;border:none;border-radius:10px;padding:6px 12px;
    background:#7C5CFC;color:#fff;font-weight:700;cursor:pointer">Allow notifications</button>
</div>
<script>
const tasks = {payload};
const msg = document.getElementById('msg'), btn = document.getElementById('btn');
function fire() {{
  let seen = [];
  try {{ seen = JSON.parse(sessionStorage.getItem('ec_seen') || '[]'); }} catch (e) {{}}
  tasks.forEach(t => {{
    if (seen.includes(t.id)) return;
    new Notification('English Coach ⏰', {{ body: t.title + ' (' + t.time + ')' }});
    seen.push(t.id);
  }});
  try {{ sessionStorage.setItem('ec_seen', JSON.stringify(seen)); }} catch (e) {{}}
}}
if (!('Notification' in window)) {{
  msg.textContent = 'Browser notifications are not supported here – in-app reminders still work.';
}} else if (Notification.permission === 'granted') {{
  msg.textContent = '🔔 Browser notifications are on (while this tab stays open).'; fire();
}} else if (Notification.permission === 'denied') {{
  msg.textContent = 'Notifications are blocked in your browser settings.';
}} else {{
  btn.style.display = 'inline-block';
  btn.onclick = () => Notification.requestPermission().then(p => {{
    if (p === 'granted') {{ btn.style.display = 'none'; msg.textContent = '🔔 Notifications enabled.'; fire(); }}
  }});
}}
</script>""",
        height=44,
    )


@st.fragment(run_every="60s")
def render(profile):
    tz = profile["timezone_offset_min"]
    due = schedule.reminders(profile["id"], gm.local_now(tz))
    for t in due:
        if t["state"] == "due":
            text = f"⏰ <b>{esc(t['title'])}</b> was due at {esc(t['scheduled_time'])}. Ready to start?"
            bg = "#FFF4F2"
        else:
            text = f"🔔 <b>{esc(t['title'])}</b> starts in {t['minutes']} min ({esc(t['scheduled_time'])})."
            bg = "#FFF9DC"
        st.markdown(f'<div class="ec-card" style="background:{bg};padding:.7rem 1rem;margin-bottom:.5rem">{text}</div>',
                    unsafe_allow_html=True)
    if due and st.session_state.get("browser_notif"):
        _browser_notifications(due)
