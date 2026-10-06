"""History: past interview sessions and progress chart per application."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core import db, ui
from core.db import DatabaseError

ui.setup_page("History", "📈")
st.title("Interview History")
st.caption("Your past mock interviews and how your scores are trending.")

try:
    apps = {a["id"]: a for a in db.list_applications()}
    sessions = db.list_sessions()
except DatabaseError as exc:
    ui.show_error(str(exc))
    st.stop()

if not sessions:
    st.info("No interviews yet. Practice from the Applications page and your progress will appear here.")
    st.stop()

rows = []
for s in sessions:
    a = apps.get(s["application_id"], {})
    rows.append({"Application": f"{a.get('company', '?')} — {a.get('role', '?')}", "Date": s["created_at"][:19].replace("T", " "),
                 "Score": s["overall_score"], "Persona": s["persona"]})
df = pd.DataFrame(rows)
df["Date"] = pd.to_datetime(df["Date"])

with st.container(border=True):
    ui.card_head("Overall score across sessions", "Each line is one application; scores are out of 10")
    fig = px.line(df, x="Date", y="Score", color="Application", markers=True, range_y=[0, 10])
    fig.update_traces(line_width=2.5)
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    ui.plotly(fig, key="hist_progress")

st.subheader("Past sessions")
for s in reversed(sessions):
    a = apps.get(s["application_id"], {})
    title = f"{a.get('company', '?')} — {s['created_at'][:16].replace('T', ' ')} · {s['persona']} · {s['overall_score']}/10"
    with st.expander(title):
        ui.render_report(s["report"], s["transcript"], s["evaluations"], key_prefix=f"h_{s['id']}")
        if st.button("Delete session", key=f"ds_{s['id']}", icon=":material/delete:"):
            deleted = False
            try:
                db.delete_session(s["id"])
                deleted = True
            except DatabaseError as exc:
                ui.show_error(str(exc))
            if deleted:
                st.rerun()
