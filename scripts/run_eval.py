"""Score the full Python pipeline (hybrid search + re-ranker + best available engine) on data/eval/questions.json.

    python scripts/run_eval.py
Writes data/eval/report.json and web/public/data/eval.json (shown on the website's Evaluation page).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from copilot import config  # noqa: E402
from copilot.answer import ask, available_engines  # noqa: E402
from copilot.evaluate import load_questions, run_eval  # noqa: E402
from copilot.index import Embedder, Reranker, load_index  # noqa: E402
from copilot.retrieve import Retriever  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-accuracy", type=float, default=0, help="fail (exit 1) if any score falls below this %%")
    args = ap.parse_args()

    chunks, vectors = load_index()
    reranker = Reranker()
    retriever = Retriever(chunks, vectors, Embedder(), reranker)
    engines = available_engines(reranker, use_local=False)
    print("Engines:", [e.name for e in engines])

    report = run_eval(load_questions(), lambda q: ask(q, retriever, engines))
    report["run_on"] = dt.date.today().isoformat()
    report["pipeline"] = "hybrid search (bge-small + BM25, RRF) + cross-encoder re-ranker + " + engines[0].name

    for r in report["results"]:
        mark = "PASS" if r["answer_correct"] else "FAIL"
        print(f"{mark}  {r['id']:22} retrieval={r['retrieval_hit']}  {r['answer'][:90]}")
    print(json.dumps(report["summary"], indent=1))

    for path in (config.ROOT / "data" / "eval" / "report.json", config.SITE_DATA / "eval.json"):
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # quality gate: a rebuild that scores worse than this is not published
    s = report["summary"]
    worst = min(v for k, v in s.items() if k.endswith("_pct") and v is not None)
    if worst < args.min_accuracy:
        raise SystemExit(f"QUALITY GATE FAILED: lowest score {worst}% is below {args.min_accuracy}% - not publishing this index")


if __name__ == "__main__":
    main()
