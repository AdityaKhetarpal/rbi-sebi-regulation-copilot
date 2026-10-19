"""
STEP 5 - FIND THE BEST PIECES FOR A QUESTION ("RETRIEVAL")
----------------------------------------------------------
Three ways to search, combined:
  1. Meaning search  - compare the question's 384 numbers with every chunk's numbers (from step 4).
                       Good at different wording. Weak at exact terms like "Rs.10,000" or "small PPI".
  2. Keyword search  - classic search-engine scoring (BM25): chunks containing the question's words,
                       especially rare words, score high. Good at exact terms.
  3. Re-ranker       - a second model reads the question and each candidate chunk TOGETHER and scores
                       how well the chunk answers it. Slow, so it only checks the top 20 from 1 + 2.

Out:   search("question") -> table of the 5 best chunks with title, page, text and a score

Run:   python pipeline/step5_search.py
"""
import re
from functools import lru_cache

import numpy as np
import pandas as pd

import settings
from step4_embed import embed_question


def words(text):
    return re.findall(r"[a-z0-9]+", str(text).lower())        # "Small PPIs (Rs.10,000)" -> small, ppis, rs, 10, 000


@lru_cache(maxsize=1)
def load():
    """Load the chunks, their numbers and the keyword index once."""
    from rank_bm25 import BM25Okapi
    chunks = pd.read_csv(settings.CHUNKS_FILE)
    vectors = np.load(settings.VECTORS_FILE)
    keyword_index = BM25Okapi([words(t) for t in chunks["text"]])
    return chunks, vectors, keyword_index


@lru_cache(maxsize=1)
def get_reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(settings.RERANKER_MODEL)


def rerank_scores(question, texts):
    """How well each text answers the question. Roughly: above 0 = relevant, far below 0 = unrelated."""
    if len(texts) == 0:
        return np.array([])
    return np.asarray(get_reranker().predict([(question, t) for t in texts]), dtype=float)


def meaning_search(question, k=20):
    chunks, vectors, _ = load()
    scores = vectors @ embed_question(question)         # similarity with every chunk at once
    best = np.argsort(-scores)[:k]                      # positions of the k highest
    return chunks.iloc[best].assign(score=scores[best])


def keyword_search(question, k=20):
    chunks, _, keyword_index = load()
    scores = keyword_index.get_scores(words(question))
    best = np.argsort(-scores)[:k]
    return chunks.iloc[best].assign(score=scores[best])


def combine(*rankings, k=60):
    """Reciprocal Rank Fusion: being near the top of ANY list helps; near the top of BOTH helps most.
    Ranks are used (not scores) because the two searches score on different scales."""
    points = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking["chunk_id"], start=1):
            points[chunk_id] = points.get(chunk_id, 0) + 1 / (k + rank)
    return sorted(points, key=points.get, reverse=True)


def search(question, top_k=settings.TOP_K):
    """The full search: meaning + keyword -> combine -> re-rank -> best `top_k`."""
    chunks, _, _ = load()
    candidate_ids = combine(meaning_search(question), keyword_search(question))[:20]
    candidates = chunks.set_index("chunk_id").loc[candidate_ids].reset_index()
    candidates["score"] = rerank_scores(question, candidates["text"].tolist())
    return candidates.sort_values("score", ascending=False).head(top_k).reset_index(drop=True)


if __name__ == "__main__":
    print("Step 5: searching")
    for q in ["How often must KYC be updated for high risk customers?",
              "What is the maximum amount that can be loaded in a small PPI?"]:
        print(f"\nQ: {q}")
        for name, results in [("meaning only", meaning_search(q, 3)), ("keyword only", keyword_search(q, 3)),
                              ("FINAL (combined + re-ranked)", search(q, 3))]:
            print(f"  {name}:")
            for r in results.itertuples():
                print(f"    {r.title}, p.{r.page} | {r.text[:90]}...")
