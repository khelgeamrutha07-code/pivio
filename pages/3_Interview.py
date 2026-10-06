"""Mock interview: setup, adaptive Q&A (text or voice), feedback report."""
from __future__ import annotations

import streamlit as st

from core import db, interview_engine as engine, media, prompts, ui, voice
from core.db import DatabaseError
from core.llm import LLMError

ui.setup_page("Interview", "🎤")
st.title("Mock Interview")

try:
    apps = [a for a in db.list_applications() if a.get("resume_id")]
except DatabaseError as exc:
    ui.show_error(str(exc))
    st.stop()

S = st.session_state
state: engine.InterviewState | None = S.get("interview")

# Display-only descriptions of the personas (the prompts themselves live in core/prompts.py).
PERSONA_BLURBS = {
    "friendly": "Warm and encouraging",
    "stress-test": "Challenges your claims",
    "rapid fire": "Short questions, fast pace",
}

# ------------------------------------------------------------------ setup
if state is None or not state.finished:
    with st.sidebar:
        st.markdown("**Your camera**")
        media.camera_panel()

if state is None:
    if not apps:
        st.info("Add an application with a linked resume and job description first.")
        st.page_link("pages/2_Applications.py", label="Go to Applications", icon=":material/work:")
        st.stop()
    ids = [a["id"] for a in apps]
    default = ids.index(S["practice_app_id"]) if S.get("practice_app_id") in ids else 0
    with st.container(border=True):
        st.subheader("Set up your interview")
        app = apps[st.selectbox("Application", range(len(apps)), index=default, key="iv_app",
                                format_func=lambda i: f"{apps[i]['company']} — {apps[i]['role']} (resume: {apps[i]['resume_label']})")]
        persona = st.radio("Interviewer persona", list(prompts.PERSONAS), key="iv_persona", horizontal=True,
                           format_func=lambda p: f"**{prompts.PERSONAS[p]['label']}** — {PERSONA_BLURBS.get(p, '')}")
        total = st.slider("Number of questions", 3, 10, 5, key="iv_total")
        start = st.button("Start interview", type="primary", key="iv_start", icon=":material/play_arrow:")
    if start:
        new_state = None
        try:
            resume = db.get_resume(app["resume_id"])
            if not resume or not (app.get("job_description") or "").strip():
                raise DatabaseError("This application needs a resume and a job description.")
            with st.spinner("Studying your resume and the job description..."):
                new_state = engine.start_interview(resume["extracted_text"], app["job_description"], persona, total)
        except (LLMError, DatabaseError) as exc:
            ui.show_error(str(exc))
        except Exception as exc:  # noqa: BLE001 - e.g. embedding model download or vector-store failure
            ui.show_unexpected("prepare the interview", exc)
        if new_state is not None:
            S.update(interview=new_state, interview_app_id=app["id"], voice_seconds={}, report=None, saved=False)
            st.rerun()
    st.stop()

# ----------------------------------------------------------- in progress
persona_label = prompts.PERSONAS[state.persona]["label"]
st.markdown(
    f'{ui.chip(persona_label)} {ui.chip(f"Question {min(state.turns_taken + 1, state.turn_cap)} of {state.turn_cap}")}',
    unsafe_allow_html=True,
)
st.progress(min(state.turns_taken / state.turn_cap, 1.0))

for t in state.transcript:
    with st.chat_message("assistant"):
        st.write(t["question"])
    with st.chat_message("user"):
        st.write(t["answer"])

if state.needs_question and not state.finished:
    st.warning("Your answer was saved, but the next question could not be generated.")
    if st.button("Retry next question", type="primary", key="iv_retry_q", icon=":material/replay:"):
        done = False
        try:
            with st.spinner("Preparing the next question..."):
                engine.next_question(state)
            done = True
        except LLMError as exc:
            ui.show_error(str(exc))
        except Exception as exc:  # noqa: BLE001
            ui.show_unexpected("prepare the next question", exc)
        if done:
            st.rerun()
    st.stop()

if not state.finished:
    turn = state.turns_taken
    with st.chat_message("assistant"):
        st.write(state.current_question)
    media.speak(state.current_question)
    akey = f"answer_{turn}"
    with st.container(border=True):
        with st.expander("Answer by voice (optional)", expanded=True):
            audio = st.audio_input("Record your answer", key=f"audio_{turn}")
            if audio is not None and st.button("Transcribe", key=f"tr_{turn}"):
                try:
                    with st.spinner("Transcribing (the first run downloads the speech model)..."):
                        text, secs = voice.transcribe(audio.getvalue())
                    S[akey] = text
                    S["voice_seconds"][turn] = secs
                    st.success("Transcribed. Edit the text below if needed, then submit.")
                except voice.TranscriptionError as exc:
                    ui.show_error(str(exc))
        answer = st.text_area("Your answer (type, or edit the voice transcript)", key=akey, height=160)
        submit = st.button("Submit answer", type="primary", key=f"submit_{turn}", icon=":material/send:")
    if submit:
        if not answer.strip():
            ui.show_error("Please type or record an answer first.")
        else:
            ok = False
            try:
                with st.spinner("Thinking about your answer..."):
                    engine.submit_answer(state, answer, S["voice_seconds"].get(turn))
                ok = True
            except Exception as exc:  # noqa: BLE001
                ui.show_unexpected("evaluate your answer", exc)
            if ok:
                if not state.finished:
                    try:
                        with st.spinner("Preparing the next question..."):
                            engine.next_question(state)
                    except LLMError as exc:
                        ui.show_error(str(exc))
                        st.stop()
                    except Exception as exc:  # noqa: BLE001
                        ui.show_unexpected("prepare the next question", exc)
                        st.stop()
                st.rerun()
    if st.button("End interview early", key="end_" + str(turn)) and state.transcript:
        state.finished = True
        st.rerun()
    st.stop()

# ----------------------------------------------------------------- report
st.success("Interview complete!")
if not S.get("report"):
    try:
        with st.spinner("Writing your feedback report..."):
            S["report"] = engine.build_report(state)
    except LLMError as exc:
        ui.show_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        ui.show_unexpected("write your feedback report", exc)
    if not S.get("report"):
        if st.button("Retry report", key="iv_retry_report", icon=":material/replay:"):
            st.rerun()
        st.stop()
if not S.get("saved"):
    try:
        db.save_session(S["interview_app_id"], state.persona, state.transcript, state.evaluations, S["report"])
        S["saved"] = True
        st.caption("Session saved to your History.")
    except DatabaseError as exc:
        ui.show_error(str(exc) + " (The report below is still available.)")
ui.render_report(S["report"], state.transcript, state.evaluations, key_prefix="live", expand_details=True)
if st.button("Start a new interview", key="iv_new", icon=":material/replay:"):
    for k in ("interview", "report", "saved", "voice_seconds"):
        S.pop(k, None)
    st.rerun()