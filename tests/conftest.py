"""Small fake models so the tests run in seconds, offline, with no downloads."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from copilot.retrieve import Retriever, tokenize  # noqa: E402


class FakeEmbedder:
    """Bag of words hashed into 64 numbers: similar words -> similar vectors."""
    def encode(self, texts, is_query=False):
        out = np.zeros((len(texts), 64))
        for i, t in enumerate(texts):
            for w in tokenize(t):
                out[i, hash(w) % 64] += 1
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)


class FakeReranker:
    """Score = shared content words x 2 - 3, so unrelated text scores below 0 like the real model."""
    STOP = {"the", "a", "of", "in", "to", "is", "what", "how", "for", "must", "be", "who", "and"}
    def score(self, question, passages):
        q = set(tokenize(question)) - self.STOP
        return np.array([len(q & set(tokenize(p))) * 2.0 - 3 for p in passages])


@pytest.fixture
def chunks():
    rows = [
        ("RBI_KYC_p41_c0", "RBI", "KYC Master Direction", "RBI_KYC.pdf", 41,
         "Periodic updation of KYC shall be carried out at least once in every two years for high-risk customers. "
         "Medium risk customers shall be updated once in every eight years."),
        ("RBI_PPI_p11_c0", "RBI", "PPI Master Direction", "RBI_PPI.pdf", 11,
         "The amount loaded in such small PPIs during any month shall not exceed Rs.10,000 and the total amount loaded "
         "during the financial year shall not exceed Rs.1,20,000."),
        ("RBI_Fraud_p24_c0", "RBI", "Fraud Risk Management", "RBI_Fraud.pdf", 24,
         "The bank shall report instances of theft, burglary, dacoity and robbery to RBI immediately, not later than seven days."),
        ("SEBI_Brokers_p3_c0", "SEBI", "Master Circular Stock Brokers", "SEBI_Brokers.pdf", 3,
         "Stock brokers shall redress investor grievances within 21 days of receipt of the complaint."),
    ]
    return pd.DataFrame(rows, columns=["chunk_id", "regulator", "title", "file", "page", "text"])


@pytest.fixture
def retriever(chunks):
    emb = FakeEmbedder()
    return Retriever(chunks, emb.encode(chunks["text"].tolist()), emb, FakeReranker())


@pytest.fixture
def reranker():
    return FakeReranker()
