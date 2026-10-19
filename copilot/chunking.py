"""Step 2 - Chunking: clean the text and cut each page into overlapping ~300-word pieces."""
import re

import pandas as pd

from . import config


def clean(text: str) -> str:
    text = text.replace(" ", " ")             # odd invisible spaces -> normal spaces
    text = re.sub(r"-\n(\w)", r"\1", text)         # "regu-\nlation" -> "regulation"
    text = re.sub(r"[ \t]+", " ", text)            # many spaces -> one
    text = re.sub(r"\n{2,}", "\n\n", text)         # many blank lines -> one
    return text.strip()


def make_chunks(text: str, size: int = config.CHUNK_WORDS, overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than the chunk size")
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):             # reached the end of the page
            break
        start += size - overlap                    # step forward, repeating `overlap` words
    return chunks


def build_chunks(pages: pd.DataFrame) -> pd.DataFrame:
    """Every chunk keeps its document and page, so answers can cite 'KYC Master Direction, p.41'."""
    rows = []
    for _, row in pages.iterrows():
        for i, piece in enumerate(make_chunks(clean(row["text"]))):
            rows.append({
                "chunk_id": f"{row['file'][:-4]}_p{row['page']}_c{i}",
                "regulator": row["regulator"], "title": row["title"],
                "file": row["file"], "page": int(row["page"]), "text": piece,
            })
    return pd.DataFrame(rows, columns=["chunk_id", "regulator", "title", "file", "page", "text"])


def split_sentences(text: str, min_words: int = 8, max_words: int = 80) -> list[str]:
    """Sentences (or clauses ending in ; or :) of a sensible length."""
    parts = re.split(r"(?<=[.;:])\s+", text)
    return [p.strip() for p in parts if min_words <= len(p.split()) <= max_words]
