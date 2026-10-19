"""Small fake models so the tests run in a second, offline, with no downloads."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import step5_search  # noqa: E402


def words(t):
    return re.findall(r"[a-z0-9]+", t.lower())


def fake_embed(text):
    """Bag of words hashed into 64 numbers: shared words -> similar numbers."""
    v = np.zeros(64)
    for w in words(text):
        v[hash(w) % 64] += 1
    return v / (np.linalg.norm(v) or 1)


class FakeReranker:
    """Score = shared meaningful words x 2 - 3, so unrelated text scores below 0 like the real model."""
    STOP = {"the", "a", "of", "in", "to", "is", "what", "how", "for", "must", "be", "who", "and", "current"}

    def predict(self, pairs):
        return np.array([len((set(words(q)) - self.STOP) & set(words(p))) * 2.0 - 3 for q, p in pairs])


CHUNKS = pd.DataFrame([
    ("RBI_KYC_p41_c0", "RBI", "KYC Master Direction", "RBI_KYC.pdf", 41,
     "Periodic updation of KYC shall be carried out at least once in every two years for high-risk customers. "
     "Medium risk customers shall be updated once in every eight years."),
    ("RBI_PPI_p11_c0", "RBI", "PPI Master Direction", "RBI_PPI.pdf", 11,
     "The amount loaded in such small PPIs during any month shall not exceed Rs.10,000 and the total amount "
     "loaded during the financial year shall not exceed Rs.1,20,000."),
    ("RBI_Fraud_p24_c0", "RBI", "Fraud Risk Management", "RBI_Fraud.pdf", 24,
     "The bank shall report instances of theft, burglary, dacoity and robbery to RBI immediately, not later than seven days."),
    ("RBI_Other_p2_c0", "RBI", "Other", "RBI_Other.pdf", 2,
     "The bank shall verify the current address through positive confirmation before allowing operations."),
], columns=["chunk_id", "regulator", "title", "file", "page", "text"])


@pytest.fixture(autouse=True)
def fake_models(monkeypatch):
    from rank_bm25 import BM25Okapi
    vectors = np.array([fake_embed(t) for t in CHUNKS["text"]])
    index = BM25Okapi([words(t) for t in CHUNKS["text"]])
    monkeypatch.setattr(step5_search, "load", lambda: (CHUNKS, vectors, index))
    monkeypatch.setattr(step5_search, "embed_question", fake_embed)
    monkeypatch.setattr(step5_search, "get_reranker", lambda: FakeReranker())
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
