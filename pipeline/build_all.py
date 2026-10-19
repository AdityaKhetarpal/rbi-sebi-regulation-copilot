"""
Run the whole pipeline in order (steps 1, 2, 3, 4, then 7) and save the files the website reads.
The weekly GitHub job runs exactly this:

    python pipeline/build_all.py --min-score 90
"""
import argparse
import datetime as dt
import json

import numpy as np

import settings
import step1_download
import step2_read_pdfs
import step3_chunk
import step4_embed
import step7_test


def save_json(name, data):
    (settings.WEBSITE_DATA / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def export_map(chunks, vectors):
    """Every chunk as a dot (x, y) for the website's map, in the same order as chunks.json."""
    titles = sorted(chunks["title"].unique())
    xy = step4_embed.map_2d(vectors)
    points = [[round(float(x), 4), round(float(y), 4), titles.index(t), int(p)]
              for (x, y), t, p in zip(xy, chunks["title"], chunks["page"])]
    save_json("map.json", {"documents": titles, "ids": chunks["chunk_id"].tolist(), "points": points})


def export_for_website(pages, chunks, downloads):
    """The website reads three small files: the chunks, the document list, and a summary."""
    website_chunks = chunks.rename(columns={"chunk_id": "id"})[["id", "regulator", "title", "page", "text"]]
    save_json("chunks.json", website_chunks.to_dict("records"))

    info = {d["file"]: d for d in downloads}
    documents = []
    for (file, regulator, title), doc_pages in pages.groupby(["file", "regulator", "title"]):
        documents.append({
            "file": file, "regulator": regulator, "title": title,
            "official_title": info.get(file, {}).get("title", ""),
            "url": info.get(file, {}).get("url", ""),
            "pages": int(doc_pages["page"].max()),
            "empty_pages": int((doc_pages["words"] < 20).sum()),
            "chunks": int((chunks["file"] == file).sum()),
        })
    save_json("documents.json", documents)
    save_json("meta.json", {"built_on": dt.date.today().isoformat(), "documents": len(documents),
                            "pages": len(pages), "chunks": len(chunks), "chunk_words": settings.CHUNK_WORDS})


def main(min_score=0):
    print("Step 1: download")
    downloads = step1_download.download_all()

    print("Step 2: read PDFs")
    pages = step2_read_pdfs.read_all_pdfs(settings.PDF_FOLDER, settings.MANUAL_PDF_FOLDER)
    if pages.empty:
        raise SystemExit("No PDFs found - nothing to build")
    step2_read_pdfs.quality_check(pages)
    pages.to_csv(settings.PAGES_FILE, index=False)

    print("Step 3: chunk")
    chunks = step3_chunk.chunk_all(pages)
    chunks.to_csv(settings.CHUNKS_FILE, index=False)

    print("Step 4: embed")
    vectors = step4_embed.embed_texts(chunks["text"].tolist())
    np.save(settings.VECTORS_FILE, vectors.astype(np.float32))

    export_for_website(pages, chunks, downloads)
    export_map(chunks, vectors)
    step7_test.main(min_score)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0)
    main(parser.parse_args().min_score)
