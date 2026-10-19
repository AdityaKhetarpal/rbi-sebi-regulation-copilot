"""
STEP 7 - TEST IT ON QUESTIONS WITH KNOWN ANSWERS
------------------------------------------------
What:  data/test_questions.json has 8 questions whose answers we know (e.g. KYC for high-risk customers
       -> "two years") and 3 off-topic questions it must refuse (e.g. "current repo rate").
       We ask every question and check:
         found  - was the right document, with the expected text, among the 5 pieces?
         right  - does the answer contain the expected words (or refuse, for off-topic ones)?
Out:   data/test_report.json and web/public/data/eval.json (shown on the website)

Run:   python pipeline/step7_test.py
       python pipeline/step7_test.py --min-score 90     (fails if any score is below 90% - used by the weekly job)
"""
import argparse
import datetime as dt
import json
import re

import settings
from step6_answer import ask


def loose(text):
    """Compare loosely: 'Rs.1,20,000/-' contains '1,20,000'."""
    return re.sub(r"[\s,/\-]", "", str(text).lower())


def check(question, result):
    expected = question.get("must_include", [])
    if question["kind"] == "refuse":
        return {"found": None, "right": result["method"] == "not in the documents" or result["answer"].startswith(settings.NOT_FOUND[:25])}
    found = any(question["expect_doc"].lower() in r.title.lower() and loose(expected[0]) in loose(r.text)
                for r in result["found"].itertuples())
    right = all(loose(e) in loose(result["answer"]) for e in expected)
    return {"found": found, "right": right}


def percent(values):
    values = [v for v in values if v is not None]
    return round(100 * sum(values) / len(values), 1) if values else None


def run_tests(questions, ask_fn=ask):
    rows = []
    for q in questions:
        result = ask_fn(q["question"])
        rows.append({"id": q["id"], "kind": q["kind"], "question": q["question"], "method": result["method"],
                     "answer": result["answer"], **check(q, result)})
    facts = [r for r in rows if r["kind"] == "fact"]
    refuse = [r for r in rows if r["kind"] == "refuse"]
    summary = {"questions": len(rows),
               "found_pct": percent([r["found"] for r in facts]),
               "right_pct": percent([r["right"] for r in facts]),
               "refused_pct": percent([r["right"] for r in refuse])}
    return {"summary": summary, "results": rows, "run_on": dt.date.today().isoformat()}


def save_report(report):
    for path in (settings.REPORT_FILE, settings.WEBSITE_DATA / "eval.json"):
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def quality_gate(report, min_score):
    """Stop the weekly job if any score drops - e.g. if RBI's page changes and a wrong PDF is downloaded."""
    lowest = min(v for k, v in report["summary"].items() if k.endswith("_pct") and v is not None)
    if lowest < min_score:
        raise SystemExit(f"QUALITY GATE FAILED: {lowest}% is below {min_score}% - not publishing")


def main(min_score=0):
    print("Step 7: testing")
    report = run_tests(json.loads(settings.QUESTIONS_FILE.read_text()))
    for r in report["results"]:
        print(f"  {'PASS' if r['right'] else 'FAIL'}  {r['question'][:60]:60} | {r['answer'][:60]}")
    print(report["summary"])
    save_report(report)
    quality_gate(report, min_score)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0)
    main(parser.parse_args().min_score)
