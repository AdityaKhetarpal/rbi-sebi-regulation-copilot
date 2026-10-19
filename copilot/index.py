"""Step 3 - Embeddings: turn every chunk into 384 numbers that capture its meaning, and save them."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


class Embedder:
    """Wraps the free bge-small model. Loaded only when first used (it downloads ~130 MB once)."""

    def __init__(self, model_name: str = config.EMBED_MODEL):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if is_query:
            texts = [config.QUERY_PREFIX + t for t in texts]          # bge: prefix on questions only
        return self._load().encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=not is_query)


class Reranker:
    """Wraps the cross-encoder that reads (question, passage) together and scores how well it answers."""

    def __init__(self, model_name: str = config.RERANK_MODEL):
        self.model_name = model_name
        self._model = None

    def score(self, question: str, passages: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
        if not passages:
            return np.array([])
        return np.asarray(self._model.predict([(question, p) for p in passages]), dtype=float)


def save_index(chunks: pd.DataFrame, vectors: np.ndarray, index_dir: Path = config.INDEX_DIR):
    if len(chunks) != len(vectors):
        raise ValueError("one vector per chunk is required")
    index_dir.mkdir(parents=True, exist_ok=True)
    chunks.to_json(index_dir / "chunks.jsonl", orient="records", lines=True, force_ascii=False)
    np.save(index_dir / "vectors.npy", vectors.astype(np.float32))


def load_index(index_dir: Path = config.INDEX_DIR):
    chunks = pd.read_json(index_dir / "chunks.jsonl", lines=True)
    vectors = np.load(index_dir / "vectors.npy")
    return chunks, vectors


def load_documents(index_dir: Path = config.INDEX_DIR) -> list[dict]:
    path = index_dir / "documents.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
