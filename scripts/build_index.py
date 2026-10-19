"""Build everything the copilot needs, end to end:

    download RBI PDFs -> read pages -> chunk -> embed -> save index -> export website data

Run from the repo root:  python scripts/build_index.py          (add --skip-download to reuse PDFs already in data/pdfs)
The GitHub workflow .github/workflows/build-index.yml runs this every Monday.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from copilot import config  # noqa: E402
from copilot.chunking import build_chunks  # noqa: E402
from copilot.index import Embedder, save_index  # noqa: E402
from copilot.ingest import document_list, download_rbi, load_pages, save_downloads  # noqa: E402


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    print("1. Downloading RBI Master Directions")
    if args.skip_download:
        prev = config.INDEX_DIR / "downloads.json"
        downloads = json.loads(prev.read_text())["documents"] if prev.exists() else []
    else:
        downloads = download_rbi()
        save_downloads(downloads)

    print("2. Reading PDFs page by page")
    pages = load_pages(config.PDF_DIR, config.MANUAL_PDF_DIR)
    if pages.empty:
        raise SystemExit("STOP: no PDFs found - nothing to index")
    docs = document_list(pages, downloads)
    for d in docs:
        flag = "  <- many empty pages, probably scanned" if d["empty_pages"] > d["pages"] / 4 else ""
        print(f"  {d['regulator']:5} {d['title'][:45]:45} {d['pages']:4} pages {d['words']:7} words{flag}")

    print("3. Chunking")
    chunks = build_chunks(pages)
    print(f"  {len(chunks)} chunks")

    print("4. Embedding (bge-small)")
    vectors = Embedder().encode(chunks["text"].tolist())
    save_index(chunks, vectors)
    counts = chunks.groupby("file").size().to_dict()
    for d in docs:
        d["chunks"] = int(counts.get(d["file"], 0))
    write_json(config.INDEX_DIR / "documents.json", docs)

    print("5. Exporting website data")
    write_json(config.SITE_DATA / "chunks.json",
               chunks.rename(columns={"chunk_id": "id"})[["id", "regulator", "title", "page", "text"]].to_dict("records"))
    write_json(config.SITE_DATA / "documents.json", docs)
    write_json(config.SITE_DATA / "meta.json", {
        "built_on": dt.date.today().isoformat(), "documents": len(docs), "pages": int(len(pages)),
        "chunks": int(len(chunks)), "embed_model": config.EMBED_MODEL, "rerank_model": config.RERANK_MODEL,
        "chunk_words": config.CHUNK_WORDS, "chunk_overlap": config.CHUNK_OVERLAP,
    })
    print("Done.")


if __name__ == "__main__":
    main()
