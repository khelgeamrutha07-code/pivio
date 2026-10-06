"""Resume vault: upload, list, view and delete labelled resume versions."""
from __future__ import annotations

import streamlit as st

from core import db, ui
from core.db import DatabaseError
from core.pdf_utils import PdfError, extract_text, file_hash

ui.setup_page("Resume Vault", "📄")
st.title("Resume Vault")
st.caption("Store labelled resume versions so you always know which one went where.")

S = st.session_state
if S.pop("rv_reset", False):  # after a save: fresh uploader + empty label (set BEFORE the widgets are created)
    S["rv_uploader_n"] = S.get("rv_uploader_n", 0) + 1
    S["rv_label"] = ""

with st.container(border=True):
    st.subheader("Upload a resume")
    file = st.file_uploader("PDF resume", type=["pdf"], key=f"resume_file_{S.get('rv_uploader_n', 0)}")
    label = st.text_input("Version label", placeholder="Data Analyst v2", key="rv_label")
    store_original = st.checkbox("Also store the original PDF file in my private storage", value=False, key="rv_store")
    if file is not None:
        data = file.getvalue()
        digest = file_hash(data)
        try:
            existing = db.find_resume_by_hash(digest)
        except DatabaseError as exc:
            ui.show_error(str(exc))
            st.stop()
        if existing:
            st.warning(f"This exact file is already in your vault as **{existing['label']}** ({existing['filename']}).")
            if st.button("Reuse the existing resume", key="rv_reuse"):
                st.success(f"Great. Use **{existing['label']}** when logging applications; nothing new was saved.")
        elif st.button("Save resume", type="primary", key="rv_save", icon=":material/upload_file:"):
            if not label.strip():
                ui.show_error("Please enter a version label.")
            else:
                saved = False
                try:
                    with st.spinner("Reading your PDF..."):
                        text = extract_text(data)
                    with st.spinner("Saving..."):
                        path = db.upload_original(data, digest) if store_original else None
                        db.add_resume(label.strip(), file.name, digest, text, path)
                    saved = True
                except (PdfError, DatabaseError) as exc:
                    ui.show_error(str(exc))
                if saved:
                    ui.flash(f"Saved “{label.strip()}” ({len(text):,} characters extracted).")
                    S["rv_reset"] = True
                    st.rerun()

st.subheader("Your resumes")
try:
    resumes = db.list_resumes()
except DatabaseError as exc:
    ui.show_error(str(exc))
    st.stop()
if not resumes:
    st.info("No resumes yet. Upload your first one above.")
for r in resumes:
    with st.expander(f"{r['label']} — {r['filename']} · {r['uploaded_at'][:10]}"):
        full = db.get_resume(r["id"]) or {}
        st.text_area("Extracted text", full.get("extracted_text", ""), height=250, disabled=True, key=f"txt_{r['id']}")
        c1, c2 = st.columns([1, 1])
        if r.get("file_path"):
                        pdf_bytes = db.read_original(r["file_path"])
        if pdf_bytes:
            c1.download_button("Download original", pdf_bytes, file_name=r["filename"], mime="application/pdf",
                                key=f"dl_{r['id']}", icon=":material/download:")
        if c2.button("Delete", key=f"del_{r['id']}", icon=":material/delete:"):
            deleted = False
            try:
                db.delete_resume(r["id"])
                deleted = True
            except DatabaseError as exc:
                ui.show_error(str(exc))
            if deleted:
                st.rerun()
