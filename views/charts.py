"""Plotly chart builders. Each function takes real data and returns a figure (or None if empty)."""
import plotly.graph_objects as go

PURPLE, CORAL, BLUE, YELLOW, MINT, LAV = "#7C5CFC", "#FF7A6B", "#8EC5FF", "#FFD84D", "#34C27A", "#E9E2FF"
INK, MUTED = "#2B2540", "#7A7394"
PALETTE = [PURPLE, CORAL, BLUE, YELLOW, MINT, "#B89BFF"]


def _style(fig, height=320, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito, sans-serif", color=INK, size=13),
        showlegend=legend, legend=dict(orientation="h", y=1.12, x=0),
        hoverlabel=dict(font_family="Nunito, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#EDE7FF", zeroline=False)
    return fig


def xp_and_time(series, title=""):
    """Bars = XP, line = minutes. Used for the weekly (7 day) and monthly (30 day) views."""
    if not series or not any(r["xp"] or r["minutes"] for r in series):
        return None
    x = [r["date"] for r in series]
    fig = go.Figure()
    fig.add_bar(x=x, y=[r["xp"] for r in series], name="XP", marker_color=PURPLE,
                hovertemplate="%{x|%a %d %b}<br>%{y} XP<extra></extra>")
    fig.add_scatter(x=x, y=[r["minutes"] for r in series], name="Minutes (est.)", mode="lines+markers",
                    line=dict(color=CORAL, width=3), yaxis="y2",
                    hovertemplate="%{x|%a %d %b}<br>%{y} min<extra></extra>")
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="min"),
                      yaxis=dict(title="XP"), title=dict(text=title, font=dict(size=15)))
    return _style(fig)


def weekly_totals_chart(weeks):
    if not weeks or not any(w["xp"] for w in weeks):
        return None
    fig = go.Figure()
    fig.add_bar(x=[w["label"] for w in weeks], y=[w["xp"] for w in weeks], name="XP",
                marker_color=[PURPLE] * (len(weeks) - 1) + [CORAL],
                hovertemplate="Week of %{x}<br>%{y} XP<extra></extra>")
    fig.update_layout(yaxis_title="XP per week")
    return _style(fig, legend=False)


def heatmap(series):
    """GitHub-style calendar: columns = weeks, rows = Mon..Sun, colour = XP that day."""
    if not series or not any(r["xp"] for r in series):
        return None
    first = series[0]["date"]
    offset = first.weekday()
    ncols = (len(series) + offset + 6) // 7
    z = [[None] * ncols for _ in range(7)]
    text = [[""] * ncols for _ in range(7)]
    for i, r in enumerate(series):
        col, row = (i + offset) // 7, (i + offset) % 7
        z[row][col] = r["xp"]
        text[row][col] = f"{r['label']}<br>{r['xp']} XP · {r['minutes']} min"
    xlabels = [f"wk {c + 1}" for c in range(ncols)]
    fig = go.Figure(go.Heatmap(
        z=z, x=xlabels, y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], text=text,
        hovertemplate="%{text}<extra></extra>", xgap=3, ygap=3, showscale=False,
        colorscale=[[0, "#F1ECFF"], [0.0001, "#CDBDFF"], [1, PURPLE]], zmin=0))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showticklabels=False)
    return _style(fig, height=230, legend=False)


def breakdown_donut(items):
    items = [i for i in items if i["minutes"] > 0]
    if not items:
        return None
    fig = go.Figure(go.Pie(labels=[i["kind"] for i in items], values=[i["minutes"] for i in items],
                           hole=.6, marker=dict(colors=PALETTE), textinfo="label+percent",
                           hovertemplate="%{label}<br>%{value} min<extra></extra>"))
    return _style(fig, height=300, legend=False)


def skills_chart(skills):
    scored = [s for s in skills if s["score"] is not None]
    if not scored:
        return None
    scored.sort(key=lambda s: s["score"])
    fig = go.Figure(go.Bar(
        x=[s["score"] for s in scored], y=[s["skill"] for s in scored], orientation="h",
        marker_color=[CORAL if s["score"] < 60 else (YELLOW if s["score"] < 80 else MINT) for s in scored],
        text=[f"{s['score']}%" for s in scored], textposition="outside",
        customdata=[s["basis"] for s in scored], hovertemplate="%{y}: %{x}%<br>%{customdata}<extra></extra>"))
    fig.update_xaxes(range=[0, 110], title="Score (%)")
    return _style(fig, height=80 + 60 * len(scored), legend=False)


def categories_chart(cats):
    if not cats:
        return None
    cats = sorted(cats, key=lambda c: c["c"])
    fig = go.Figure(go.Bar(x=[c["c"] for c in cats], y=[c["category"] for c in cats], orientation="h",
                           marker_color=CORAL, text=[c["c"] for c in cats],
                           textposition="outside"))
    fig.update_xaxes(title="Mistakes recorded")
    return _style(fig, height=80 + 45 * len(cats), legend=False)


def grammar_trend_chart(weeks):
    pts = [w for w in weeks if w["accuracy"] is not None]
    if len(pts) < 2:
        return None
    fig = go.Figure(go.Scatter(
        x=[w["label"] for w in pts], y=[w["accuracy"] for w in pts], mode="lines+markers",
        line=dict(color=PURPLE, width=3), marker=dict(size=[8 + min(w["messages"], 20) for w in pts]),
        customdata=[w["messages"] for w in pts],
        hovertemplate="Week of %{x}<br>%{y}% without mistakes<br>%{customdata} messages<extra></extra>"))
    fig.update_yaxes(range=[0, 105], title="% messages without mistakes")
    return _style(fig, legend=False)


def quiz_trend_chart(series):
    pts = [r for r in series if r["quiz_total"] > 0]
    if not pts:
        return None
    fig = go.Figure(go.Scatter(
        x=[r["date"] for r in pts], y=[round(100 * r["quiz_correct"] / r["quiz_total"]) for r in pts],
        mode="lines+markers", line=dict(color=CORAL, width=3),
        marker=dict(size=[8 + min(r["quiz_total"], 20) for r in pts]), customdata=[r["quiz_total"] for r in pts],
        hovertemplate="%{x|%d %b}<br>%{y}% correct<br>%{customdata} questions<extra></extra>"))
    fig.update_yaxes(range=[0, 105], title="Quiz accuracy (%)")
    return _style(fig, legend=False)


def score_line(dates, scores, counts, ytitle, unit):
    if not dates:
        return None
    fig = go.Figure(go.Scatter(
        x=dates, y=scores, mode="lines+markers", line=dict(color=PURPLE, width=3),
        marker=dict(size=[8 + min(c, 10) * 2 for c in counts]), customdata=counts,
        hovertemplate="%{x}<br>%{y}<br>%{customdata} " + unit + "<extra></extra>"))
    fig.update_yaxes(range=[0, 105], title=ytitle)
    return _style(fig, legend=False)
