import json

from copilot import config
from copilot.evaluate import norm, run_eval, score_one


def test_norm_matches_indian_number_formats():
    assert norm("1,20,000") in norm("shall not exceed Rs.1,20,000/-;")


def test_score_fact_and_refusal():
    q = {"id": "x", "kind": "fact", "question": "?", "expect_doc": "PPI", "must_include": ["10,000"]}
    good = {"engine": "e", "answer": "Rs.10,000 a month [1]", "refused": False, "citations": [],
            "sources": [{"title": "PPI Master Direction", "text": "not exceed Rs.10,000"}]}
    assert score_one(q, good)["answer_correct"] and score_one(q, good)["retrieval_hit"]
    r = {"id": "r", "kind": "refuse", "question": "?"}
    assert score_one(r, {**good, "refused": True})["answer_correct"]
    assert not score_one(r, good)["answer_correct"]


def test_run_eval_summary():
    qs = [{"id": "r", "kind": "refuse", "question": "?"}]
    rep = run_eval(qs, lambda q: {"engine": "e", "answer": config.REFUSAL, "refused": True, "citations": [], "sources": []})
    assert rep["summary"]["refusal_accuracy_pct"] == 100.0


def test_question_file_is_valid():
    qs = json.loads(config.EVAL_FILE.read_text())
    assert len({q["id"] for q in qs}) == len(qs)
    for q in qs:
        assert q["kind"] in {"fact", "refuse"}
        if q["kind"] == "fact":
            assert q["expect_doc"] and q["must_include"]
