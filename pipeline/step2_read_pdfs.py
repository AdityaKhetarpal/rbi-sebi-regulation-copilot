"""
STEP 2 - READ THE PDFS, PAGE BY PAGE
------------------------------------
What:  Pull the text out of every PDF and put it in a table: one row per page.
Why:   We keep the page number from the start, so every answer can later say "KYC Direction, page 41".
Out:   data/pages.csv  (columns: file, regulator, title, page, words, text)

Run:   python pipeline/step2_read_pdfs.py
"""
import pandas as pd
import pymupdf

import settings


def read_pdf(path):
    """One dictionary per page: {"page": 1, "text": "..."}"""
    with pymupdf.open(path) as pdf:
        return [{"page": number, "text": page.get_text()} for number, page in enumerate(pdf, start=1)]


def read_all_pdfs(*folders):
    rows = []
    for folder in folders:
        for path in sorted(folder.glob("*.pdf")):
            regulator = path.name.split("_")[0].upper()             # "RBI_KYC_Master_Direction.pdf" -> "RBI"
            title = path.stem[len(regulator) + 1:].replace("_", " ")   # -> "KYC Master Direction"
            for page in read_pdf(path):
                rows.append({"file": path.name, "regulator": regulator, "title": title, **page})
    pages = pd.DataFrame(rows, columns=["file", "regulator", "title", "page", "text"])
    pages["words"] = pages["text"].str.split().str.len().fillna(0).astype(int)
    return pages


def quality_check(pages):
    """Pages with almost no words are probably scanned images - the search can't read those."""
    summary = pages.groupby("title").agg(pages=("page", "count"), words=("words", "sum"),
                                         empty_pages=("words", lambda w: int((w < 20).sum())))
    print(summary.to_string())
    return summary


if __name__ == "__main__":
    print("Step 2: reading PDFs")
    pages = read_all_pdfs(settings.PDF_FOLDER, settings.MANUAL_PDF_FOLDER)
    quality_check(pages)
    pages.to_csv(settings.PAGES_FILE, index=False)
    print(f"Saved {len(pages)} pages to {settings.PAGES_FILE.name}")
