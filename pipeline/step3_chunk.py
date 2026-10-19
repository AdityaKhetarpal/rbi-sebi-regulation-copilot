"""
STEP 3 - CUT THE PAGES INTO SMALL PIECES ("CHUNKS")
---------------------------------------------------
What:  Cut every page into pieces of about 300 words. Neighbouring pieces share 50 words.
Why:   We can't send a 100-page rulebook to the AI for every question - it's slow and costly.
       Instead we find the 5 best pieces and send only those. The 50-word overlap means a rule
       that sits across a cut still appears whole in one piece.
Out:   data/chunks.csv  (columns: chunk_id, regulator, title, file, page, text)

Run:   python pipeline/step3_chunk.py
"""
import re

import pandas as pd

import settings


def clean(text):
    text = text.replace(" ", " ")             # odd invisible spaces -> normal spaces
    text = re.sub(r"-\n(\w)", r"\1", text)         # "regu-\nlation" -> "regulation"
    text = re.sub(r"\s+", " ", text)               # many spaces / new lines -> one space
    return text.strip()


def make_chunks(text, size=settings.CHUNK_WORDS, overlap=settings.OVERLAP_WORDS):
    """'w1 w2 ... w700' -> ['w1..w300', 'w251..w550', 'w501..w700']"""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):             # reached the end of the page
            break
        start += size - overlap                    # move on, repeating `overlap` words
    return chunks


def chunk_all(pages):
    rows = []
    for _, page in pages.iterrows():
        text = page["text"] if isinstance(page["text"], str) else ""   # empty pages come back as NaN
        for i, piece in enumerate(make_chunks(clean(text))):
            rows.append({
                "chunk_id": f"{page['file'][:-4]}_p{page['page']}_c{i}",   # e.g. RBI_KYC_Master_Direction_p41_c0
                "regulator": page["regulator"], "title": page["title"],
                "file": page["file"], "page": int(page["page"]), "text": piece,
            })
    return pd.DataFrame(rows, columns=["chunk_id", "regulator", "title", "file", "page", "text"])


if __name__ == "__main__":
    print("Step 3: cutting pages into chunks")
    chunks = chunk_all(pd.read_csv(settings.PAGES_FILE))
    chunks.to_csv(settings.CHUNKS_FILE, index=False)
    print(chunks.groupby("title").size().to_string())
    example = chunks.iloc[len(chunks) // 2]
    print(f"\nExample chunk {example['chunk_id']}:\n{example['text'][:400]}...")
    print(f"\nSaved {len(chunks)} chunks to {settings.CHUNKS_FILE.name}")
