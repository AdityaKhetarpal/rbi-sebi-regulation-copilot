"""Step 1 - Ingestion: download the official PDFs and read them page by page."""
import datetime as dt
import html
import json
import re
from pathlib import Path

import pandas as pd

from . import config

PDF_LINK = re.compile(r"""https?://rbidocs\.rbi\.org\.in/[^"'\s>]+?\.pdf""", flags=re.I)
BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
}


def clean_title(raw: str) -> str:
    """'Know Your Customer) Directions, 2025 (Updated as on ...)   <a id=...' -> readable title."""
    text = re.sub(r"<[^>]+>|\s+", " ", html.unescape(raw)).strip()
    return text.split(" <a ")[0].split("<a ")[0].strip()


def find_pdf(page: str, topic: str, window: int = 3000):
    """Find the topic on RBI's list page and return (pdf_url, title) of the Master Direction.

    RBI's page also links notifications about the same topic, so every candidate is collected and
    Master Direction files (named like 169MD.PDF or 82MDPPIS...PDF) are preferred over anything else.
    """
    candidates = []
    for size in (window, window * 3):                                   # second pass with a wider window
        for m in re.finditer(re.escape(topic), page, flags=re.I):
            # the title starts after the previous tag, e.g. "Reserve Bank of India (Know Your Customer) Directions"
            begin = max(page.rfind(">", max(0, m.start() - 200), m.start()) + 1, m.start() - 200)
            title = clean_title(page[begin: m.start() + 200])
            if any(w in title.lower() for w in config.SKIP_WORDS) or title.startswith("<") or len(title) < len(topic):
                continue
            pdf = PDF_LINK.search(page[m.start(): m.start() + size])
            if pdf:
                candidates.append((pdf.group(0), title))
        if candidates:
            break
    if not candidates:
        return None
    is_md = lambda url: re.search(r"/\d+MD[^/]*\.pdf$", url, flags=re.I) is not None  # noqa: E731
    return next((c for c in candidates if is_md(c[0])), candidates[0])


def download_rbi(pdf_dir: Path = config.PDF_DIR, wanted: dict = config.RBI_WANTED) -> list[dict]:
    """Download each wanted Master Direction. Returns one record per document (found or not)."""
    import requests

    pdf_dir.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers.update({**BROWSER, "Referer": config.RBI_LIST_PAGE})
    page = s.get(config.RBI_LIST_PAGE, timeout=60).text                 # also picks up cookies

    records = []
    for topic, filename in wanted.items():
        found = find_pdf(page, topic)
        if not found:
            print(f"NOT FOUND: {topic}")
            records.append({"topic": topic, "file": filename, "status": "not found"})
            continue
        url, title = found
        r = s.get(url, timeout=120)
        if r.ok and r.content[:4] == b"%PDF":                           # a real PDF starts with %PDF
            (pdf_dir / filename).write_bytes(r.content)
            print(f"saved {filename} ({len(r.content) // 1024} KB) - {title[:80]}")
            records.append({"topic": topic, "file": filename, "status": "downloaded", "title": title, "url": url})
        else:
            print(f"FAILED {topic}: {r.status_code} {r.headers.get('Content-Type')}")
            records.append({"topic": topic, "file": filename, "status": f"failed {r.status_code}", "url": url})
    return records


def read_pdf(path: Path) -> list[dict]:
    """One record per page: {page, text}."""
    import pymupdf

    with pymupdf.open(path) as doc:
        return [{"page": n, "text": p.get_text()} for n, p in enumerate(doc, start=1)]


def load_pages(*folders: Path) -> pd.DataFrame:
    """Read every PDF in the folders. File names look like REGULATOR_Short_Title.pdf."""
    rows = []
    for folder in folders:
        for path in sorted(Path(folder).glob("*.pdf")):
            regulator = path.name.split("_")[0].upper()                 # "RBI_KYC_..." -> "RBI"
            title = path.stem[len(regulator) + 1:].replace("_", " ")    # -> "KYC Master Direction"
            for p in read_pdf(path):
                rows.append({"file": path.name, "regulator": regulator, "title": title, **p})
    data = pd.DataFrame(rows, columns=["file", "regulator", "title", "page", "text"])
    data["words"] = data["text"].str.split().str.len().fillna(0).astype(int)
    return data


def document_list(pages: pd.DataFrame, downloads: list[dict]) -> list[dict]:
    """Summary per document for the website: pages, words, scanned pages, official title and link."""
    meta = {d["file"]: d for d in downloads}
    docs = []
    for (file, regulator, title), g in pages.groupby(["file", "regulator", "title"]):
        d = meta.get(file, {})
        docs.append({
            "file": file, "regulator": regulator, "title": title,
            "official_title": d.get("title", ""), "url": d.get("url", ""),
            "pages": int(g["page"].max()), "words": int(g["words"].sum()),
            "empty_pages": int((g["words"] < 20).sum()),        # under 20 words = probably a scanned image
        })
    return docs


def save_downloads(records: list[dict], index_dir: Path = config.INDEX_DIR):
    index_dir.mkdir(parents=True, exist_ok=True)
    out = {"downloaded_on": dt.date.today().isoformat(), "documents": records}
    (index_dir / "downloads.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
