"""Step 4 - Retrieval: meaning search + keyword search, merged with RRF, then re-ranked."""
import re

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from . import config

COLUMNS = ["chunk_id", "regulator", "title", "file", "page", "text"]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())          # "Small PPIs (Rs.10,000)" -> ["small", "ppis", "rs", "10", "000"]


def rrf_merge(rankings: list[list[str]], k: int = config.RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion: rank 1 earns 1/(k+1), rank 2 earns 1/(k+2) ... summed over every list."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return scores


class Retriever:
    def __init__(self, chunks: pd.DataFrame, vectors: np.ndarray, embedder=None, reranker=None):
        self.chunks = chunks.reset_index(drop=True)
        self.vectors = vectors
        self.embedder = embedder            # None -> keyword search only
        self.reranker = reranker            # None -> keep the RRF order
        self.bm25 = BM25Okapi([tokenize(t) for t in self.chunks["text"]])
        self.by_id = self.chunks.set_index("chunk_id")

    def _rows(self, positions, scores, name):
        found = self.chunks.iloc[list(positions)][COLUMNS].copy()
        found.insert(0, name, np.round(np.asarray(scores, dtype=float), 4))
        return found.reset_index(drop=True)

    def _filter(self, regulator):
        if not regulator:
            return np.ones(len(self.chunks), dtype=bool)
        return (self.chunks["regulator"].str.upper() == regulator.upper()).to_numpy()

    def semantic(self, question: str, k: int = config.TOP_K, regulator: str | None = None) -> pd.DataFrame:
        q = self.embedder.encode([question], is_query=True)[0]       # question -> 384 numbers
        scores = np.where(self._filter(regulator), self.vectors @ q, -np.inf)
        best = np.argsort(-scores)[:k]
        best = [i for i in best if np.isfinite(scores[i])]
        return self._rows(best, scores[best], "score")

    def keyword(self, question: str, k: int = config.TOP_K, regulator: str | None = None) -> pd.DataFrame:
        scores = np.where(self._filter(regulator), self.bm25.get_scores(tokenize(question)), -np.inf)
        best = [i for i in np.argsort(-scores)[:k] if np.isfinite(scores[i])]
        return self._rows(best, scores[best], "score")

    def hybrid(self, question: str, k: int = config.TOP_K, pool: int = config.POOL, regulator: str | None = None) -> pd.DataFrame:
        lists = [self.keyword(question, pool, regulator)["chunk_id"].tolist()]
        if self.embedder is not None:
            lists.insert(0, self.semantic(question, pool, regulator)["chunk_id"].tolist())
        rrf = rrf_merge(lists)
        best = sorted(rrf, key=rrf.get, reverse=True)[:k]
        found = self.by_id.loc[best].reset_index()[COLUMNS]
        found.insert(0, "rrf", [round(rrf[c], 4) for c in best])
        return found

    def retrieve(self, question: str, k: int = config.TOP_K, pool: int = config.POOL, regulator: str | None = None) -> pd.DataFrame:
        """The full search: hybrid candidates, then the re-ranker picks the best k."""
        candidates = self.hybrid(question, k=pool, pool=pool, regulator=regulator)
        if self.reranker is None or candidates.empty:
            candidates["rerank"] = np.nan
            return candidates.head(k)
        candidates["rerank"] = self.reranker.score(question, candidates["text"].tolist())
        return candidates.sort_values("rerank", ascending=False).head(k).reset_index(drop=True)

    def chunk(self, chunk_id: str) -> dict | None:
        if chunk_id not in self.by_id.index:
            return None
        return {"chunk_id": chunk_id, **self.by_id.loc[chunk_id].to_dict()}
