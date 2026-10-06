"""Orchestrates the four LLM roles: planner, interviewer, evaluator, reporter."""
from __future__ import annotations

import time

import json
from dataclasses import dataclass, field

from core import config, llm, prompts, rag, voice
from core.llm import LLMError
from core.schemas import Evaluation, Plan, Report

MAX_FOLLOWUPS_PER_TOPIC = 2
HISTORY_TURNS = 8


@dataclass
class InterviewState:
    """Everything needed to run one interview; lives in st.session_state."""

    resume_text: str
    job_description: str
    persona: str
    total_questions: int
    plan: Plan | None = None
    topic_idx: int = 0
    followups_on_topic: int = 0
    transcript: list[dict] = field(default_factory=list)
    evaluations: list[dict] = field(default_factory=list)
    current_question: str = ""
    current_is_followup: bool = False
    finished: bool = False
    needs_question: bool = False

    @property
    def turns_taken(self) -> int:
        return len(self.transcript)

    @property
    def turn_cap(self) -> int:
        """Hard cap on turns, regardless of follow-ups."""
        return min(self.total_questions, config.MAX_QUESTIONS_HARD_CAP)

    @property
    def topic(self):
        return self.plan.topics[self.topic_idx % len(self.plan.topics)]


RAG_WAIT_SECONDS = 6  # the reference material is a nice-to-have: never make the user wait longer than this for it


def _retrieve_with_timeout(query: str, k: int) -> list[str]:
    """Look up reference chunks, but give up after RAG_WAIT_SECONDS (the embedding model may still be loading)."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(rag.retrieve, query, k).result(timeout=RAG_WAIT_SECONDS)
    except FutureTimeout:
        print(f"[TIMING] reference lookup not ready after {RAG_WAIT_SECONDS}s, continuing without it", flush=True)
        return []
    finally:
        pool.shutdown(wait=False)


def plan_interview(resume_text: str, job_description: str) -> Plan:
    """Planner: run once per session using RAG context from the job description's skills."""
    t0 = time.time()
    context = rag.format_context(_retrieve_with_timeout(rag.skills_query(job_description), 2))
    print(f"[TIMING] reference lookup took {time.time() - t0:.1f}s", flush=True)
    t1 = time.time()
    plan = llm.generate_json(
        Plan, prompts.PLANNER_SYSTEM, prompts.planner_prompt(resume_text, job_description, context), temperature=0.3
    )
    print(f"[TIMING] planning the interview took {time.time() - t1:.1f}s", flush=True)
    return plan


def start_interview(resume_text: str, job_description: str, persona: str, total_questions: int) -> InterviewState:
    """Create the state, run the planner and set the opening question."""
    if persona not in prompts.PERSONAS:
        raise ValueError(f"Unknown persona: {persona}")
    total = max(3, min(int(total_questions), config.MAX_QUESTIONS_HARD_CAP))
    state = InterviewState(resume_text, job_description, persona, total)
    state.plan = plan_interview(resume_text, job_description)
    state.current_question = state.plan.opening_question.strip()
    return state


def _history_text(state: InterviewState) -> str:
    lines: list[str] = []
    for t in state.transcript[-HISTORY_TURNS:]:
        lines.append(f"Interviewer: {t['question']}")
        lines.append(f"Candidate: {t['answer']}")
    return "\n".join(lines)


def next_question(state: InterviewState) -> str:
    """Interviewer: ask a follow-up if the evaluator said so, otherwise move to the next topic."""
    last = Evaluation.model_validate(state.evaluations[-1]) if state.evaluations else None
    follow = bool(last and last.needs_followup and state.followups_on_topic < MAX_FOLLOWUPS_PER_TOPIC)
    if follow:
        state.followups_on_topic += 1
    else:
        state.topic_idx += 1 if state.turns_taken else 0
        state.followups_on_topic = 0
    topic = state.topic
    persona = prompts.PERSONAS[state.persona]
    prompt = prompts.interviewer_prompt(
        resume=state.resume_text, job_description=state.job_description, topic=topic.name, topic_why=topic.why,
        mode="followup" if follow else "new", hint=last.followup_hint if last else "",
        history=_history_text(state), number=state.turns_taken + 1, total=state.turn_cap,
    )
    t0 = time.time()
    text = llm.generate_text(persona["system"], prompt, temperature=persona["temperature"])
    print(f"[TIMING] writing the next question took {time.time() - t0:.1f}s", flush=True)
    question = text.strip().strip('"').strip()
    state.current_question, state.current_is_followup = question, follow
    state.needs_question = False
    return question


def evaluate_answer(question: str, answer: str) -> Evaluation:
    """Evaluator: low-temperature scoring with RAG reference. Falls back to a neutral score on failure."""
    context = rag.format_context(_retrieve_with_timeout(question, 3))
    try:
        return llm.generate_json(
            Evaluation, prompts.EVALUATOR_SYSTEM, prompts.evaluator_prompt(question, answer, context), temperature=0.1
        )
    except LLMError:
        return Evaluation(relevance=5, depth=5, structure=5, clarity=5, reason="Automatic evaluation was unavailable for this answer.")


def submit_answer(state: InterviewState, answer: str, seconds: float | None = None) -> None:
    """Record an answer, evaluate it, and mark the interview finished when the turn cap is reached."""
    answer = answer.strip()
    if not answer:
        raise ValueError("Please provide an answer first.")
    t0 = time.time()
    evaluation = evaluate_answer(state.current_question, answer)
    print(f"[TIMING] evaluating the answer took {time.time() - t0:.1f}s", flush=True)
    state.transcript.append({
        "turn": state.turns_taken + 1,
        "topic": state.topic.name,
        "question": state.current_question,
        "answer": answer,
        "is_followup": state.current_is_followup,
        "delivery": voice.delivery_stats(answer, seconds),
    })
    state.evaluations.append(evaluation.model_dump())
    if state.turns_taken >= state.turn_cap:
        state.finished = True
    state.needs_question = not state.finished


def criteria_averages(evaluations: list[dict]) -> dict[str, float]:
    """Average each criterion across all evaluations."""
    keys = ["relevance", "depth", "structure", "clarity"]
    if not evaluations:
        return {k: 0.0 for k in keys}
    return {k: round(sum(e[k] for e in evaluations) / len(evaluations), 2) for k in keys}


def build_report(state: InterviewState) -> dict:
    """Reporter: returns the report as a dict including delivery stats and criterion averages."""
    transcript = "\n".join(
        f"Q{t['turn']} [{t['topic']}]: {t['question']}\nA{t['turn']}: {t['answer']}" for t in state.transcript
    )
    evals = "\n".join(f"Q{i + 1}: {json.dumps(e)}" for i, e in enumerate(state.evaluations))
    report: Report = llm.generate_json(
        Report, prompts.REPORTER_SYSTEM,
        prompts.reporter_prompt(transcript, evals, prompts.PERSONAS[state.persona]["label"]), temperature=0.3,
    )
    data = report.model_dump()
    data["criteria_averages"] = criteria_averages(state.evaluations)
    data["delivery"] = voice.aggregate_delivery([t["delivery"] for t in state.transcript])
    data["turn_scores"] = [round(Evaluation.model_validate(e).average, 2) for e in state.evaluations]
    return data