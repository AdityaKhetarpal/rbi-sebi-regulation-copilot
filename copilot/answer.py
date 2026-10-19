"""Step 5 - Generation: write the answer from the retrieved chunks only, with [n] citations.

Three engines, tried in order, so the system never depends on a paid key:
  1. Claude (needs ANTHROPIC_API_KEY)   2. a free open-source model on a GPU   3. extractive: exact sentences, no AI
"""
import os
import re

import numpy as np
import pandas as pd

from . import config
from .chunking import split_sentences
from .retrieve import tokenize

SYSTEM = """You answer questions about Indian financial regulations using ONLY the numbered sources provided.

Rules:
1. Every factual sentence must end with its source number in square brackets, e.g. [2].
2. Quote numbers, limits and deadlines exactly as written in the sources.
3. If the sources do not contain the answer, say exactly: "I couldn't find this in the provided RBI/SEBI documents." Do not guess or use outside knowledge.
4. If the sources only partly answer, say what is covered and what is missing.
5. Keep it short: 2-5 sentences. Plain English.
6. This is information, not legal advice."""

STOP = {"the", "a", "an", "of", "in", "to", "is", "are", "what", "how", "for", "must", "be", "by", "on", "and",
        "or", "can", "does", "do", "which", "who", "when", "within", "under", "with", "as", "at", "it", "that"}


def build_context(found: pd.DataFrame) -> str:
    """Number each chunk and say where it is from - the 'A' (augmentation) in RAG."""
    return "\n\n".join(f"[{i}] {r.title}, page {r.page}\n{r.text}" for i, r in enumerate(found.itertuples(), start=1))


def citations(answer: str, found: pd.DataFrame) -> list[dict]:
    """Turn [1], [2] in the answer into {n, title, page, chunk_id}."""
    used = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 0 < int(n) <= len(found)})
    return [{"n": n, "title": found.iloc[n - 1]["title"], "page": int(found.iloc[n - 1]["page"]),
             "chunk_id": found.iloc[n - 1]["chunk_id"]} for n in used]


# ---------- engine 1: Claude ----------
class ClaudeEngine:
    name = f"Claude ({config.CLAUDE_MODEL})"

    def __init__(self, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.client = client

    def generate(self, question, context, found):
        r = self.client.messages.create(model=config.CLAUDE_MODEL, max_tokens=400, system=SYSTEM,
                                        messages=[{"role": "user", "content": f"Sources:\n\n{context}\n\nQuestion: {question}"}])
        return r.content[0].text


# ---------- engine 2: free local model ----------
class LocalEngine:
    name = "Free local model (Qwen2.5-1.5B)"

    def __init__(self, pipe=None):
        if pipe is None:
            import torch
            from transformers import pipeline
            if not torch.cuda.is_available():
                raise RuntimeError("no GPU")
            pipe = pipeline("text-generation", model=config.LOCAL_LLM, device_map="auto", torch_dtype=torch.float16)
        self.pipe = pipe

    def generate(self, question, context, found):
        out = self.pipe([{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"Sources:\n\n{context}\n\nQuestion: {question}"}],
                        max_new_tokens=300, do_sample=False)
        return out[0]["generated_text"][-1]["content"]


# ---------- engine 3: extractive (always works) ----------
class ExtractiveEngine:
    name = "Extractive (exact sentences, no AI)"

    def __init__(self, reranker=None, n: int = 2, threshold: float = config.RELEVANCE_THRESHOLD):
        self.reranker, self.n, self.threshold = reranker, n, threshold

    def generate(self, question, context, found):
        candidates = [(i, s) for i, r in enumerate(found.itertuples(), start=1) for s in split_sentences(r.text)]
        if not candidates:
            return config.REFUSAL
        if self.reranker is not None:                                   # best: the re-ranker judges each sentence
            scores = self.reranker.score(question, [s for _, s in candidates])
            floor = self.threshold
        else:                                                           # fallback: share of question words present
            q = set(tokenize(question)) - STOP
            scores = np.array([len(q & set(tokenize(s))) / max(len(q), 1) for _, s in candidates])
            floor = 0.5
        order = np.argsort(-np.asarray(scores))
        keep = [candidates[i] for i in order[: self.n] if scores[i] >= floor]
        if not keep:
            return config.REFUSAL
        return " ".join(f"{s} [{i}]" for i, s in keep)


def available_engines(reranker=None, use_claude: bool = True, use_local: bool = True) -> list:
    """Every engine that can run here, best first. Extractive is always last, so something always answers."""
    engines = []
    if use_claude and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            engines.append(ClaudeEngine())
        except Exception as e:  # noqa: BLE001
            print("Claude unavailable:", type(e).__name__)
    if use_local:
        try:
            engines.append(LocalEngine())
        except Exception:
            pass
    engines.append(ExtractiveEngine(reranker))
    return engines


def ask(question: str, retriever, engines: list, k: int = config.TOP_K, regulator: str | None = None) -> dict:
    found = retriever.retrieve(question, k=k, regulator=regulator)                       # R
    top = found["rerank"].iloc[0] if len(found) and "rerank" in found else np.nan
    sources = found[["chunk_id", "title", "page", "text"]].to_dict("records")

    # refuse early when even the best chunk is off-topic: no AI call, no made-up answer
    if found.empty or (pd.notna(top) and top < config.RELEVANCE_THRESHOLD):
        return {"question": question, "answer": config.REFUSAL, "engine": "retrieval threshold",
                "citations": [], "sources": sources, "refused": True, "top_score": None if pd.isna(top) else float(top)}

    context = build_context(found)                                                        # A
    for engine in engines:                                                                # G
        try:
            answer = engine.generate(question, context, found)
            return {"question": question, "answer": answer, "engine": engine.name,
                    "citations": citations(answer, found), "sources": sources,
                    "refused": answer.strip().startswith(config.REFUSAL[:25]),
                    "top_score": None if pd.isna(top) else float(top)}
        except Exception as e:  # noqa: BLE001 - any failure moves on to the next engine
            print(f"{engine.name} failed ({type(e).__name__}) - falling back")
    raise RuntimeError("no engine could answer")
