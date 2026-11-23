"""Shared look & feel: global CSS and small HTML component helpers."""
import html

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
:root{
  --purple:#7C5CFC; --lavender:#E9E2FF; --blue:#8EC5FF; --coral:#FF7A6B;
  --peach:#FFD3B6; --yellow:#FFD84D; --ink:#2B2540; --muted:#7A7394; --card:#FFFFFF;
}
html, body, [class*="css"], .stApp { font-family:'Nunito', sans-serif !important; color:var(--ink); }
.stApp{
  background: radial-gradient(1200px 500px at 10% -10%, #E9E2FF 0%, transparent 60%),
              radial-gradient(900px 500px at 100% 0%, #FFE6D6 0%, transparent 55%),
              #F7F4FF;
}
#MainMenu, footer, header[data-testid="stHeader"]{ background:transparent; }
.block-container{ padding-top:2rem; max-width:1150px; }
h1,h2,h3{ font-weight:900 !important; letter-spacing:-0.5px; }

/* Sidebar */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg,#6C4DF0 0%, #8A6CFF 60%, #A98BFF 100%);
}
section[data-testid="stSidebar"] *{ color:#fff !important; }
section[data-testid="stSidebar"] .stRadio label{
  background:rgba(255,255,255,.10); border-radius:14px; padding:.55rem .8rem;
  margin-bottom:.35rem; transition:all .2s ease; width:100%;
}
section[data-testid="stSidebar"] .stRadio label:hover{ background:rgba(255,255,255,.22); transform:translateX(4px); }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"]{ gap:0; }
section[data-testid="stSidebar"] .stRadio label > div:first-child{ display:none; }
section[data-testid="stSidebar"] .stRadio label:has(input:checked){ background:#fff; }
section[data-testid="stSidebar"] .stRadio label:has(input:checked) *{ color:var(--purple) !important; font-weight:800; }
section[data-testid="stSidebar"] .stButton button{
  background:rgba(255,255,255,.18); border:none; color:#fff !important; border-radius:14px; width:100%;
}
section[data-testid="stSidebar"] .stButton button:hover{ background:rgba(255,255,255,.3); }

/* Buttons */
.stButton > button, .stFormSubmitButton > button{
  border-radius:16px; font-weight:800; padding:.55rem 1.2rem; border:none;
  background:linear-gradient(135deg,#7C5CFC,#9B7BFF); color:#fff;
  box-shadow:0 6px 0 #5A3FD1; transition:transform .12s ease, box-shadow .12s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover{ transform:translateY(-2px); box-shadow:0 8px 0 #5A3FD1; color:#fff; }
.stButton > button:active, .stFormSubmitButton > button:active{ transform:translateY(4px); box-shadow:0 2px 0 #5A3FD1; }
.stButton > button[kind="secondary"]{ background:#fff; color:var(--purple); box-shadow:0 6px 0 #D8CCFF; }
.stButton > button[kind="secondary"]:hover{ box-shadow:0 8px 0 #D8CCFF; color:var(--purple); }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input{
  border-radius:14px !important; border:2px solid #E3DAFF !important; background:#fff !important;
}
.stTextInput input:focus, .stTextArea textarea:focus{ border-color:var(--purple) !important; box-shadow:0 0 0 3px rgba(124,92,252,.15) !important; }
div[data-testid="stChatMessage"]{ background:#fff; border-radius:20px; padding:.9rem 1rem; box-shadow:0 4px 18px rgba(124,92,252,.08); }
.stTabs [data-baseweb="tab"]{ border-radius:12px 12px 0 0; font-weight:800; }
.stProgress > div > div > div > div{ background:linear-gradient(90deg,#7C5CFC,#FF7A6B); border-radius:10px; }

/* Cards */
.ec-card{
  background:var(--card); border-radius:24px; padding:1.2rem 1.3rem; margin-bottom:1rem;
  box-shadow:0 8px 28px rgba(124,92,252,.10); border:1px solid rgba(124,92,252,.08);
  transition:transform .2s ease, box-shadow .2s ease;
}
.ec-card:hover{ transform:translateY(-3px); box-shadow:0 14px 34px rgba(124,92,252,.16); }
.ec-hero{
  background:linear-gradient(120deg,#7C5CFC 0%, #A98BFF 55%, #FF9A8B 100%); color:#fff;
  border-radius:28px; padding:1.6rem 1.8rem; margin-bottom:1.2rem;
  box-shadow:0 14px 34px rgba(124,92,252,.28); position:relative; overflow:hidden;
}
.ec-hero:after{ content:""; position:absolute; right:-40px; top:-40px; width:200px; height:200px;
  background:rgba(255,255,255,.16); border-radius:50%; }
.ec-hero h1{ color:#fff; margin:0; font-size:2rem; }
.ec-hero p{ margin:.3rem 0 0; opacity:.95; font-weight:600; }
.ec-stat{ display:flex; align-items:center; gap:.9rem; }
.ec-stat .ico{ width:52px; height:52px; border-radius:16px; display:grid; place-items:center; font-size:1.7rem; }
.ec-stat .val{ font-size:1.7rem; font-weight:900; line-height:1; }
.ec-stat .lbl{ color:var(--muted); font-weight:700; font-size:.85rem; }
.ec-pill{ display:inline-block; padding:.25rem .75rem; border-radius:999px; font-weight:800; font-size:.8rem; }
.ec-section{ font-size:1.25rem; font-weight:900; margin:1.2rem 0 .6rem; }
.ec-empty{ text-align:center; color:var(--muted); padding:1.4rem; font-weight:700; }
.ec-fix{ background:#FFF4F2; border-left:5px solid var(--coral); border-radius:12px; padding:.6rem .9rem; margin:.4rem 0; }
.ec-good{ background:#EFFBF3; border-left:5px solid #34C27A; border-radius:12px; padding:.6rem .9rem; margin:.4rem 0; }
.ec-tip{ background:#FFF9DC; border-left:5px solid var(--yellow); border-radius:12px; padding:.6rem .9rem; margin:.4rem 0; }
.ec-bar{ display:flex; align-items:flex-end; gap:.5rem; height:120px; }
.ec-bar div.col{ flex:1; text-align:center; font-size:.75rem; font-weight:800; color:var(--muted); }
.ec-bar div.fill{ border-radius:10px 10px 4px 4px; background:linear-gradient(180deg,#9B7BFF,#7C5CFC); min-height:6px; margin-bottom:4px; transition:height .6s ease; }
.ec-bar div.fill.today{ background:linear-gradient(180deg,#FFB199,#FF7A6B); }
.flame{ display:inline-block; animation:flicker 1.2s ease-in-out infinite; transform-origin:50% 90%; }
@keyframes flicker{ 0%,100%{ transform:scale(1) rotate(-2deg);} 50%{ transform:scale(1.15) rotate(3deg);} }
.pop{ animation:pop .5s cubic-bezier(.2,1.4,.4,1); }
@keyframes pop{ from{ transform:scale(.7); opacity:0;} to{ transform:scale(1); opacity:1;} }
.ring{ --p:0; width:112px; height:112px; border-radius:50%;
  background:conic-gradient(var(--purple) calc(var(--p)*1%), #EDE7FF 0); display:grid; place-items:center; }
.ring > div{ width:84px; height:84px; border-radius:50%; background:#fff; display:grid; place-items:center;
  font-weight:900; font-size:1.3rem; color:var(--purple); }
.flash{ background:linear-gradient(135deg,#FFF 0%,#F2ECFF 100%); border:2px dashed #CDBDFF; border-radius:26px;
  text-align:center; padding:2.2rem 1rem; }
.flash .w{ font-size:2.3rem; font-weight:900; color:var(--purple); }
@media (max-width:768px){
  .block-container{ padding:1rem .8rem; }
  .ec-hero h1{ font-size:1.5rem; } .ec-hero{ padding:1.2rem; }
  .ec-stat .val{ font-size:1.3rem; }
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text) -> str:
    return html.escape(str(text))


def hero(title, subtitle=""):
    st.markdown(
        f'<div class="ec-hero pop"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def stat_card(icon, value, label, bg="#EFE9FF", extra_class=""):
    st.markdown(
        f"""<div class="ec-card"><div class="ec-stat">
        <div class="ico {extra_class}" style="background:{bg}"><span class="{extra_class}">{icon}</span></div>
        <div><div class="val">{esc(value)}</div><div class="lbl">{esc(label)}</div></div>
        </div></div>""",
        unsafe_allow_html=True,
    )


def ring(percent, caption=""):
    p = max(0, min(100, int(percent)))
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:1rem"><div class="ring" style="--p:{p}">'
        f"<div>{p}%</div></div><div style='font-weight:800'>{esc(caption)}</div></div>",
        unsafe_allow_html=True,
    )


def empty_state(icon, text):
    st.markdown(f'<div class="ec-card ec-empty"><div style="font-size:2.2rem">{icon}</div>{esc(text)}</div>',
                unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="ec-section">{esc(title)}</div>', unsafe_allow_html=True)


def week_bars(week):
    mx = max([d["xp"] for d in week] + [1])
    cols = ""
    for i, d in enumerate(week):
        h = int(100 * d["xp"] / mx)
        today = " today" if i == len(week) - 1 else ""
        cols += (f'<div class="col"><div style="font-size:.7rem">{d["xp"]}</div>'
                 f'<div class="fill{today}" style="height:{h}px"></div>{esc(d["label"])}</div>')
    st.markdown(f'<div class="ec-card"><div class="ec-bar">{cols}</div></div>', unsafe_allow_html=True)
