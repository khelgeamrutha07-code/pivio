"""UI smoke tests: load every page with streamlit.testing.v1.AppTest and a fake backend (no Supabase/Gemini needed).

Run:  pytest tests/test_ui_smoke.py -q
The tests replace core.db / core.interview_engine / core.config functions with in-memory fakes, so nothing touches the network.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
from streamlit.testing.v1 import AppTest  # noqa: E402

from core import auth, config, db, interview_engine as engine  # noqa: E402

USER = {"id": "u1", "email": "alex.morgan@example.com"}
TIMEOUT = 30

EVAL = {"relevance": 8, "depth": 7, "structure": 8, "clarity": 9, "reason": "Solid.", "needs_followup": False, "followup_hint": ""}
REPORT = {
    "overall_score": 8.8, "per_skill_scores": {"SQL": 9.5, "Python": 6.2, "Statistics": 3.0},
    "strengths": ["Concrete metrics", "Clear structure"], "weaknesses": ["Vague on trade-offs"],
    "best_answer": "Q1: precise and quantified.", "weakest_answer": "Q2: no concrete example.",
    "improved_answer_for_weakest": "In my last role I reduced report time by 40% by ...",
    "tips": ["Use STAR", "Quantify results", "Name trade-offs", "Slow down slightly"],
    "criteria_averages": {"relevance": 8.0, "depth": 7.0, "structure": 8.0, "clarity": 9.0},
    "delivery": {"answers": 2, "avg_words": 42.0, "filler_total": 3, "fillers": {"like": 2, "basically": 1}, "avg_wpm": 138.0},
    "turn_scores": [8.0, 7.5],
}
TRANSCRIPT = [{"turn": 1, "question": "Tell me about SQL.", "answer": "I use SQL daily.", "is_followup": False, "topic": "SQL", "delivery": {}}]
RESUMES = [{"id": "r1", "label": "Data Analyst v1", "filename": "cv.pdf", "file_hash": "h", "file_path": None,
            "uploaded_at": "2026-01-01T10:00:00"}]
APPS = [
    {"id": "a1", "company": "Acme", "role": "Data Analyst", "status": "Interview", "applied_on": "2026-01-02", "resume_id": "r1",
     "resume_label": "Data Analyst v1", "job_description": "SQL and Python", "notes": ""},
    {"id": "a2", "company": "Beta <b>Corp</b>", "role": "Scientist", "status": "Offer", "applied_on": "2026-01-03", "resume_id": None,
     "resume_label": None, "job_description": "", "notes": None},
]
SESSIONS = [{"id": "s1", "application_id": "a1", "persona": "friendly", "overall_score": 7.5, "created_at": "2026-02-01T10:00:00",
             "transcript": TRANSCRIPT, "evaluations": [EVAL], "report": REPORT}]


@pytest.fixture
def backend(monkeypatch):
    """Fake data layer + engine. Returns the list of recorded (function_name, args) calls."""
    calls: list[tuple] = []

    def fake(name, value):
        def _f(*args, **kwargs):
            calls.append((name, args))
            return copy.deepcopy(value)
        monkeypatch.setattr(db, name, _f)

    for name, value in [
        ("list_resumes", RESUMES), ("list_applications", APPS), ("list_sessions", SESSIONS),
        ("get_resume", {"id": "r1", "label": "Data Analyst v1", "extracted_text": "Resume text"}),
        ("find_resume_by_hash", None), ("read_original", None), ("add_application", {}), ("update_application", None),
        ("delete_application", None), ("delete_resume", None), ("delete_session", None), ("save_session", {}),
        ("delete_all_user_data", None),
    ]:
        fake(name, value)

    def start(resume_text, job_description, persona, total):
        state = engine.InterviewState(resume_text, job_description, persona, total)
        state.current_question = "Tell me about yourself."
        return state

    def submit(state, answer, seconds=None):
        state.transcript.append({"turn": state.turns_taken + 1, "topic": "t", "question": state.current_question, "answer": answer,
                                 "is_followup": False, "delivery": {}})
        state.evaluations.append(dict(EVAL))
        state.finished = state.turns_taken >= state.turn_cap
        state.needs_question = not state.finished

    def next_q(state):
        state.current_question = f"Follow-up question {state.turns_taken + 1}?"
        state.needs_question = False
        return state.current_question

    monkeypatch.setattr(engine, "start_interview", start)
    monkeypatch.setattr(engine, "submit_answer", submit)
    monkeypatch.setattr(engine, "next_question", next_q)
    monkeypatch.setattr(engine, "build_report", lambda state: copy.deepcopy(REPORT))
    monkeypatch.setattr(config, "missing_settings", lambda: [])
    return calls


def load(page: str, logged_in: bool = True) -> AppTest:
    at = AppTest.from_file(str(ROOT / page), default_timeout=TIMEOUT)
    if logged_in:
        at.session_state["user"] = dict(USER)
    return at


def button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


PAGES = ["app.py", "pages/1_Resume_Vault.py", "pages/2_Applications.py", "pages/3_Interview.py", "pages/4_History.py",
         "pages/5_Settings.py"]


@pytest.mark.parametrize("page", PAGES)
def test_logged_out_shows_login_form(backend, page):
    at = load(page, logged_in=False).run()
    assert not at.exception
    assert at.text_input(key="li_email") is not None and at.text_input(key="li_pw") is not None
    assert [t.label for t in at.tabs] == ["Log in", "Sign up"]


def test_login_error_message_is_explicit(backend, monkeypatch):
    def bad(email, password):
        raise auth.AuthError("Wrong email or password, or this account does not exist yet. Try signing up first.")

    monkeypatch.setattr(auth, "sign_in", bad)
    at = load("app.py", logged_in=False).run()
    at.text_input(key="li_email").input("a@b.co")
    at.text_input(key="li_pw").input("secret1")
    button(at, "Log in").click().run()
    assert not at.exception
    assert any("Wrong email or password" in e.value for e in at.error)


@pytest.mark.parametrize("page", PAGES)
def test_logged_in_pages_render(backend, page):
    at = load(page).run()
    assert not at.exception
    assert not at.error


def test_dashboard_metrics(backend):
    at = load("app.py").run()
    assert [m.label for m in at.metric] == ["Resumes", "Applications", "Interviews practised", "Average score"]


def test_applications_add_application(backend):
    at = load("pages/2_Applications.py").run()
    at.text_input(key="new_company").input("Globex")
    at.text_input(key="new_role").input("Analyst")
    button(at, "Save application").click().run()
    assert not at.exception
    assert any(name == "add_application" for name, _ in backend)


def test_applications_validation_error(backend):
    at = load("pages/2_Applications.py").run()
    button(at, "Save application").click().run()
    assert any("Company and role are required" in e.value for e in at.error)


def test_interview_full_flow_to_report(backend):
    at = load("pages/3_Interview.py").run()
    assert not at.exception
    at.slider(key="iv_total").set_value(3)
    button(at, "Start interview").click().run()
    assert not at.exception
    assert at.session_state["interview"].turn_cap == 3
    for turn in range(3):
        at.text_area(key=f"answer_{turn}").input(f"My answer number {turn}")
        button(at, "Submit answer").click().run()
        assert not at.exception, f"turn {turn}"
    assert at.session_state["interview"].finished
    labels = [m.label for m in at.metric]
    assert "Filler words" in labels and "Speaking pace (wpm)" in labels
    assert sum(1 for name, _ in backend if name == "save_session") == 1


def test_interview_empty_answer_is_rejected(backend):
    at = load("pages/3_Interview.py").run()
    button(at, "Start interview").click().run()
    button(at, "Submit answer").click().run()
    assert any("Please type or record an answer" in e.value for e in at.error)


def test_interview_engine_crash_is_friendly(backend, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("internal secret")

    at = load("pages/3_Interview.py").run()
    button(at, "Start interview").click().run()
    monkeypatch.setattr(engine, "submit_answer", boom)
    at.text_area(key="answer_0").input("An answer")
    button(at, "Submit answer").click().run()
    assert not at.exception
    assert at.error and all("internal secret" not in e.value for e in at.error)


def test_history_renders_report(backend):
    at = load("pages/4_History.py").run()
    assert not at.exception
    assert any(m.label == "Filler words" for m in at.metric)


def test_settings_delete_requires_confirmation(backend):
    at = load("pages/5_Settings.py").run()
    assert button(at, "Delete my data").disabled
    at.text_input(key="st_confirm").input("DELETE").run()
    button(at, "Delete my data").click().run()
    assert not at.exception
    assert any(name == "delete_all_user_data" for name, _ in backend)
