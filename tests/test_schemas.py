import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pytest
from pydantic import ValidationError

from core.llm import extract_json
from core.schemas import Evaluation, Plan, Report


def test_valid_plan():
    plan = Plan.model_validate({
        "topics": [{"name": "SQL", "why": "Required", "difficulty": "Medium"}],
        "skill_gaps": ["Spark"], "opening_question": "Tell me about a SQL project.",
    })
    assert plan.topics[0].difficulty == "medium"


def test_plan_requires_topics():
    with pytest.raises(ValidationError):
        Plan.model_validate({"topics": [], "skill_gaps": [], "opening_question": "Hello there"})


def test_evaluation_bounds():
    ok = Evaluation(relevance=8, depth=6, structure=7, clarity=9, reason="Good.")
    assert ok.average == 7.5 and ok.needs_followup is False
    with pytest.raises(ValidationError):
        Evaluation(relevance=11, depth=6, structure=7, clarity=9)
    with pytest.raises(ValidationError):
        Evaluation(relevance=0, depth=6, structure=7, clarity=9)


def test_report_clamps_skill_scores():
    r = Report(overall_score=7.2, per_skill_scores={"SQL": 12, "Python": -3})
    assert r.per_skill_scores == {"SQL": 10.0, "Python": 0.0}
    with pytest.raises(ValidationError):
        Report(overall_score=11)


def test_extract_json_handles_fences_and_prose():
    payload = {"a": 1}
    assert extract_json("```json\n" + json.dumps(payload) + "\n```") == payload
    assert extract_json("Sure! Here you go: " + json.dumps(payload) + " Hope that helps.") == payload
    with pytest.raises(json.JSONDecodeError):
        extract_json("no json here")
