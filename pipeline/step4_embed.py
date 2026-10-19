"""
STEP 4 - TURN EVERY CHUNK INTO NUMBERS ("EMBEDDINGS")
-----------------------------------------------------
What:  A free AI model reads each chunk and turns it into a list of 384 numbers.
Why:   Texts with similar MEANING get similar numbers, even if they use different words.
       "How often must KYC be re-verified?" can then match "periodic updation of KYC shall be carried out..."
       - not one word in common, but the same meaning.
Out:   data/vectors.npy  (one row of 384 numbers per chunk, same order as chunks.csv)

Run:   python pipeline/step4_embed.py
"""
from functools import lru_cache

import numpy as np
import pandas as pd

import settings

# this model works best when questions (not chunks) start with this sentence
QUESTION_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)                      # load the model only once (~130 MB download the first time)
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts):
    """List of texts -> array of shape (number of texts, 384). Every row has length 1 ("normalised")."""
    return get_model().encode(list(texts), normalize_embeddings=True, batch_size=32, show_progress_bar=len(texts) > 50)


def embed_question(question):
    return embed_texts([QUESTION_PREFIX + question])[0]


def similarity_demo():
    """See it work: A and B mean the same with different words, C is a different topic."""
    sentences = ["KYC must be updated periodically for high-risk customers",
                 "Customer identity details need re-verification every two years",
                 "The payment aggregator must have a minimum net worth"]
    v = embed_texts(sentences)
    print("Similarity (1 = same meaning, 0 = unrelated):")
    print(f"  A vs B (same meaning, different words): {v[0] @ v[1]:.2f}")
    print(f"  A vs C (different topic):                {v[0] @ v[2]:.2f}")


if __name__ == "__main__":
    print("Step 4: embedding chunks")
    similarity_demo()
    chunks = pd.read_csv(settings.CHUNKS_FILE)
    vectors = embed_texts(chunks["text"].tolist())
    np.save(settings.VECTORS_FILE, vectors.astype(np.float32))
    print(f"Saved {vectors.shape[0]} x {vectors.shape[1]} numbers to {settings.VECTORS_FILE.name}")
