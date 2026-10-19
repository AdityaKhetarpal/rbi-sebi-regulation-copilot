"""Step 7 - Evaluation: questions with known answers, scored automatically.

For each question we check three things:
  retrieval  - did the top 5 chunks include the right document with the expected text?
  answer     - does the answer contain the expected number or phrase?
  refusal    - did it refuse the questions our documents cannot answer, and answer the rest?
"""
import json
import re
import time

from . import config


def norm(text: str) -> str:
    """Compare loosely: 'Rs.1,20,000/-' and '1,20,000' should match."""
    return re.sub(r"[\s,/\-]", "", str(text).lower())


def load_questions(path=config.EVAL_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_one(q: dict, result: dict) -> dict:
    must = [norm(m) for m in q.get("must_include", [])]
    is_refuse = q["kind"] == "refuse"
    retrieval_hit = None
    if not is_refuse:
        retrieval_hit = any(
            q["expect_doc"].lower() in s["title"].lower() and all(m in norm(s["text"]) for m in must[:1])
            for s in result["sources"]
        )
    answer_ok = result["refused"] if is_refuse else (not result["refused"] and all(m in norm(result["answer"]) for m in must))
    return {"id": q["id"], "kind": q["kind"], "question": q["question"], "engine": result["engine"],
            "retrieval_hit": retrieval_hit, "answer_correct": bool(answer_ok), "refused": bool(result["refused"]),
            "answer": result["answer"], "citations": result["citations"]}


def run_eval(questions: list[dict], ask_fn) -> dict:
    rows = []
    for q in questions:
        t0 = time.time()
        row = score_one(q, ask_fn(q["question"]))
        row["seconds"] = round(time.time() - t0, 2)
        rows.append(row)
    facts = [r for r in rows if r["kind"] == "fact"]
    refuse = [r for r in rows if r["kind"] == "refuse"]
    pct = lambda xs: round(100 * sum(xs) / len(xs), 1) if xs else None  # noqa: E731
    summary = {
        "questions": len(rows),
        "retrieval_hit_rate_pct": pct([r["retrieval_hit"] for r in facts]),
        "answer_accuracy_pct": pct([r["answer_correct"] for r in facts]),
        "refusal_accuracy_pct": pct([r["answer_correct"] for r in refuse]),
        "overall_pct": pct([r["answer_correct"] for r in rows]),
    }
    return {"summary": summary, "results": rows}
