"""
STEP 6 - ANSWER THE QUESTION, ONLY FROM THE PIECES FOUND
--------------------------------------------------------
This is RAG (Retrieval-Augmented Generation):
  Retrieve  - step 5 finds the 5 best pieces
  Augment   - we number them [1]..[5] and put them in the prompt with strict rules
  Generate  - the answer is written ONLY from those pieces, citing [1], [2]...

Two ways to write the answer, so it always works:
  - Claude (an AI model), if an ANTHROPIC_API_KEY is set
  - Quote mode (no AI, no key): pick the best sentences from the pieces, word for word

And one safety check BEFORE writing anything:
  if even the best piece scores below MIN_SCORE, the documents don't cover the question
  -> answer "I couldn't find this..." instead of guessing.

Run:   python pipeline/step6_answer.py
"""
import os
import re

import settings
from step5_search import rerank_scores, search

RULES = f"""You answer questions about Indian financial regulations using ONLY the numbered sources provided.
1. End every factual sentence with its source number in square brackets, e.g. [2].
2. Quote numbers, limits and deadlines exactly as written.
3. If the sources do not contain the answer, say exactly: "{settings.NOT_FOUND}"
4. Keep it to 2-5 plain-English sentences. This is information, not legal advice."""


def numbered_sources(found):
    """'[1] KYC Master Direction, page 41\n<text>' ... - what the AI receives."""
    return "\n\n".join(f"[{i}] {r.title}, page {r.page}\n{r.text}" for i, r in enumerate(found.itertuples(), start=1))


def sentences(text):
    parts = re.split(r"(?<=[.;:])\s+", text)
    return [p.strip() for p in parts if 8 <= len(p.split()) <= 80]       # skip fragments and walls of text


def quote_answer(question, found, how_many=2):
    """No AI: the sentences that best answer the question, word for word, each with its source number."""
    options = [(i, s) for i, r in enumerate(found.itertuples(), start=1) for s in sentences(r.text)]
    if not options:
        return settings.NOT_FOUND
    scores = rerank_scores(question, [s for _, s in options])
    best = sorted(zip(scores, options), key=lambda x: x[0], reverse=True)[:how_many]
    keep = [f"{s} [{i}]" for score, (i, s) in best if score >= settings.MIN_SCORE]
    return " ".join(keep) if keep else settings.NOT_FOUND


def claude_answer(question, found):
    import anthropic
    client = anthropic.Anthropic()                                   # reads ANTHROPIC_API_KEY
    reply = client.messages.create(
        model=settings.CLAUDE_MODEL, max_tokens=400, system=RULES,
        messages=[{"role": "user", "content": f"Sources:\n\n{numbered_sources(found)}\n\nQuestion: {question}"}])
    return reply.content[0].text


def citations(answer, found):
    """[1] in the answer -> 'KYC Master Direction, p.41'"""
    numbers = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(found)})
    return [f"[{n}] {found.iloc[n - 1]['title']}, p.{found.iloc[n - 1]['page']}" for n in numbers]


def ask(question):
    found = search(question)                                         # R: step 5
    if found.empty or found["score"].iloc[0] < settings.MIN_SCORE:  # safety check: nothing relevant
        return {"answer": settings.NOT_FOUND, "method": "not in the documents", "citations": [], "found": found}

    method = "quote (no AI)"
    answer = None
    if os.environ.get("ANTHROPIC_API_KEY"):                          # A + G with Claude, if possible
        try:
            answer, method = claude_answer(question, found), "Claude"
        except Exception as error:                                   # no credit, no internet... -> quote mode
            print("  Claude unavailable:", type(error).__name__)
    if answer is None:
        answer = quote_answer(question, found)
    return {"answer": answer, "method": method, "citations": citations(answer, found), "found": found}


if __name__ == "__main__":
    print("Step 6: answering")
    for q in ["How often must KYC be updated for high risk customers?",
              "What is the maximum amount that can be loaded in a small PPI in a month?",
              "What is the current repo rate?"]:                    # not in our documents: should refuse
        out = ask(q)
        print(f"\nQ: {q}\nA ({out['method']}): {out['answer']}")
        for c in out["citations"]:
            print("   ", c)
