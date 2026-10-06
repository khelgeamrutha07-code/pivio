"""Settings: privacy notice and delete-my-data."""
from __future__ import annotations

import streamlit as st

from core import db, ui
from core.db import DatabaseError

ui.setup_page("Settings", "⚙️")
st.title("Settings & Privacy")

S = st.session_state
if S.pop("st_reset", False):  # clear the confirmation box after a deletion (before the widget is created)
    S["st_confirm"] = ""

with st.container(border=True):
    ui.card_head("What Pivio stores", "Everything is private to your account")
    st.markdown(
        """
- **Account:** your email and password (handled by Firebase Authentication; passwords are never visible to Pivio).
- **Resumes:** the extracted text, file name, a SHA-256 hash and your label. The original PDF is stored **only** if you tick the box on upload.
- **Applications:** company, role, job description, dates, status, notes and which resume you used.
- **Interviews:** transcripts, hidden evaluations, your report and delivery stats (filler words, pace). Audio recordings are **not** stored; they are transcribed in memory and discarded.
- **AI processing:** your resume text, job description and answers are sent to Google Gemini to generate questions and feedback.
- Only you can read your rows (row-level security).
"""
    )

with st.container(border=True):
    ui.marker("danger")
    ui.card_head("Danger zone", "Delete my data")
    st.warning("This permanently deletes all your resumes, applications, interview sessions and stored files. It cannot be undone.")
    confirm = st.text_input("Type DELETE to confirm", key="st_confirm")
    if st.button("Delete my data", type="primary", disabled=confirm != "DELETE", key="st_delete", icon=":material/delete_forever:"):
        deleted = False
        try:
            with st.spinner("Deleting..."):
                db.delete_all_user_data()
            deleted = True
        except DatabaseError as exc:
            ui.show_error(str(exc))
        if deleted:
            for k in ("interview", "report", "saved", "practice_app_id", "interview_app_id", "voice_seconds"):
                S.pop(k, None)
            ui.flash("All your data has been deleted.")
            S["st_reset"] = True
            st.rerun()
    st.caption("To remove your login itself, delete the user in the Firebase console (Authentication → Users).")
