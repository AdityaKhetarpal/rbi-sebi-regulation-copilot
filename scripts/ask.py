"""Ask a question from the command line.

    python scripts/ask.py "How often must KYC be updated for high-risk customers?"
    python scripts/ask.py --agent "Compare the KYC update rules for high and low risk customers"   (needs ANTHROPIC_API_KEY)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from copilot.agent import run_agent  # noqa: E402
from copilot.answer import ask, available_engines  # noqa: E402
from copilot.index import Embedder, Reranker, load_documents, load_index  # noqa: E402
from copilot.retrieve import Retriever  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--agent", action="store_true", help="multi-step agent (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--regulator", choices=["RBI", "SEBI"])
    a = ap.parse_args()

    chunks, vectors = load_index()
    reranker = Reranker()
    retriever = Retriever(chunks, vectors, Embedder(), reranker)

    if a.agent:
        out = run_agent(a.question, retriever, load_documents())
        for t in out["trace"]:
            if t["type"] == "tool":
                print(f"  step {t['step']}: {t['tool']}({t['input']})")
    else:
        out = ask(a.question, retriever, available_engines(reranker), regulator=a.regulator)
        print(f"[{out['engine']}]")
    print("\n" + out["answer"])
    for c in out["citations"]:
        print(f"  - {c['title']}, p.{c['page']}")


if __name__ == "__main__":
    main()
