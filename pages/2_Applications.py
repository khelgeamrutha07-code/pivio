"""Application tracker: add, edit, delete, filter and launch practice interviews."""
from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from core import db, ui
from core.db import STATUSES, DatabaseError

ui.setup_page("Applications", "📌")
st.title("Applications")
st.caption("Log where you applied, which resume you sent and practise for that exact role.")

try:
    resumes = db.list_resumes()
    apps = db.list_applications()
except DatabaseError as exc:
    ui.show_error(str(exc))
    st.stop()

resume_options = {r["label"] + f" ({r['filename']})": r["id"] for r in resumes}
NONE = "— none —"


def app_form(prefix: str, a: dict | None = None) -> None:
    """Render an add/edit form; saves through db on submit."""
    a = a or {}
    labels = [NONE] + list(resume_options)
    current = next((k for k, v in resume_options.items() if v == a.get("resume_id")), NONE)
    with st.form(f"{prefix}_form", clear_on_submit=a == {}):
        c1, c2 = st.columns(2)
        company = c1.text_input("Company", value=a.get("company", ""), key=f"{prefix}_company")
        role = c2.text_input("Role", value=a.get("role", ""), key=f"{prefix}_role")
        c3, c4, c5 = st.columns(3)
        applied = c3.date_input("Applied on", key=f"{prefix}_applied",
                                value=datetime.fromisoformat(a["applied_on"]).date() if a.get("applied_on") else date.today())
        status = c4.selectbox("Status", STATUSES, index=STATUSES.index(a.get("status", "Applied")), key=f"{prefix}_status")
        resume_label = c5.selectbox("Resume used", labels, index=labels.index(current), key=f"{prefix}_resume")
        jd = st.text_area("Job description", value=a.get("job_description", ""), height=180, key=f"{prefix}_jd")
        notes = st.text_area("Notes", value=a.get("notes", "") or "", height=70, key=f"{prefix}_notes")
        submitted = st.form_submit_button("Save application", type="primary")
    if not submitted:
        return
    if not company.strip() or not role.strip():
        ui.show_error("Company and role are required.")
        return
    rid = resume_options.get(resume_label)
    saved = False
    try:
        if a:
            db.update_application(a["id"], company, role, jd, applied, status, notes, rid)
        else:
            db.add_application(company, role, jd, applied, status, notes, rid)
        saved = True
    except DatabaseError as exc:
        ui.show_error(str(exc))
    if saved:
        ui.flash("Application saved.")
        st.rerun()


# ---- status overview
counts = {s: sum(1 for a in apps if a["status"] == s) for s in STATUSES}
for col, s in zip(st.columns(len(STATUSES)), STATUSES, strict=True):
    col.metric(s, counts[s])

with st.expander("Add application", expanded=not apps):
    if not resumes:
        st.info("Tip: add a resume in the Resume Vault first so you can link it.")
    app_form("new")

st.subheader("Your applications")
chosen = st.multiselect("Filter by status", STATUSES, default=STATUSES, key="app_filter")
shown = [a for a in apps if a["status"] in chosen]
if not shown:
    st.info("No applications match.")

for a in shown:
    with st.container(border=True):
        st.markdown(ui.app_row(a), unsafe_allow_html=True)
        with st.expander("Details, practice and edit"):
            b1, b2 = st.columns(2)
            if b1.button("Practice interview", key=f"prac_{a['id']}", type="primary", icon=":material/mic:"):
                if not a.get("resume_id") or not (a.get("job_description") or "").strip():
                    ui.show_error("Link a resume and add a job description first (edit below).")
                else:
                    st.session_state["practice_app_id"] = a["id"]
                    st.session_state.pop("interview", None)
                    st.switch_page("pages/3_Interview.py")
            if b2.button("Delete", key=f"del_{a['id']}", icon=":material/delete:"):
                deleted = False
                try:
                    db.delete_application(a["id"])
                    deleted = True
                except DatabaseError as exc:
                    ui.show_error(str(exc))
                if deleted:
                    st.rerun()
            st.markdown("**Edit**")
            app_form(f"edit_{a['id']}", a)
