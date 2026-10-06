"""Pivio entry point: dashboard behind the auth gate. Other screens live in pages/."""
from __future__ import annotations

import streamlit as st

from core import db, ui
from core.db import DatabaseError

ui.setup_page("Dashboard", "🧭")

st.title("Dashboard")
st.caption(ui.TAGLINE)

try:
    resumes, apps, sessions = db.list_resumes(), db.list_applications(), db.list_sessions()
except DatabaseError as exc:
    ui.show_error(str(exc))
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Resumes", len(resumes))
c2.metric("Applications", len(apps))
c3.metric("Interviews practised", len(sessions))
scores = [s["overall_score"] for s in sessions if s.get("overall_score") is not None]
c4.metric("Average score", f"{sum(scores) / len(scores):.1f}" if scores else "n/a")

st.subheader("Get started")
STEPS = [
    ("1", "Add a resume", "Upload a PDF and label the version.", "pages/1_Resume_Vault.py", "Open Resume Vault", ":material/description:"),
    ("2", "Log an application", "Link the resume you sent and paste the job description.", "pages/2_Applications.py",
     "Open Applications", ":material/work:"),
    ("3", "Practice", "Start a mock interview built from that resume and job.", "pages/3_Interview.py", "Open Interview", ":material/mic:"),
]
for col, (num, title, body, page, label, icon) in zip(st.columns(3, gap="large"), STEPS, strict=True):
    with col, st.container(border=True):
        st.markdown(
            f'<span class="pv-step-n">{num}</span><p class="pv-step-title">{title}</p><p class="pv-step-body">{body}</p>',
            unsafe_allow_html=True,
        )
        st.page_link(page, label=label, icon=icon)

if apps:
    st.subheader("Recent applications")
    with st.container(border=True):
        st.markdown("".join(ui.app_row(a) for a in apps[:5]), unsafe_allow_html=True)
