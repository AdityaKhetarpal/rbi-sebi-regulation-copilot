"""
STEP 1 - DOWNLOAD THE RULEBOOKS
-------------------------------
What:  Download RBI's "Master Directions" (the official rulebooks) as PDFs.
How:   RBI has one web page listing every Master Direction. We read that page, find each topic we want
       (e.g. "Know Your Customer"), take the PDF link next to it, and download it.
Out:   data/pdfs/RBI_KYC_Master_Direction.pdf ... and data/downloads.json (what we got, from where)

Run:   python pipeline/step1_download.py
"""
import html
import json
import re

import requests

import settings

# RBI keeps its PDFs on rbidocs.rbi.org.in
PDF_LINK = re.compile(r"""https?://rbidocs\.rbi\.org\.in/[^"'\s>]+?\.pdf""", flags=re.I)
# words that mean "this is not the main rulebook" (amendments, ombudsman schemes...)
SKIP = ["ombudsman", "amendment", "repeal", "withdrawal"]


def find_pdf(page_html, topic):
    """Find `topic` on RBI's list page. Returns (pdf_link, title) or None."""
    found = []
    for match in re.finditer(re.escape(topic), page_html, flags=re.I):
        # the title: from the previous HTML tag up to the link (or the end of the table cell)
        start = max(page_html.rfind(">", max(0, match.start() - 200), match.start()) + 1, match.start() - 200)
        raw = re.split(r"<a\b|</td>|</tr>|<br", page_html[start: match.start() + 300], flags=re.I)[0]
        title = re.sub(r"<[^>]+>|\s+", " ", html.unescape(raw)).strip()
        if title.startswith("<") or any(word in title.lower() for word in SKIP):
            continue
        link = PDF_LINK.search(page_html[match.start(): match.start() + 3000])   # first PDF link after the title
        if link:
            found.append((link.group(0), title))
    if not found:
        return None
    # the page also links notifications about the same topic; Master Direction files are named like "169MD.PDF"
    for link, title in found:
        if re.search(r"/\d+MD[^/]*\.pdf$", link, flags=re.I):
            return link, title
    return found[0]


def download_all():
    settings.PDF_FOLDER.mkdir(parents=True, exist_ok=True)
    browser = requests.Session()                       # behaves like one browser tab (keeps cookies)
    browser.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
                            "Referer": settings.RBI_PAGE})
    page_html = browser.get(settings.RBI_PAGE, timeout=60).text

    report = []
    for topic, filename in settings.DOCUMENTS.items():
        result = find_pdf(page_html, topic)
        if result is None:
            print(f"  not found on RBI's page: {topic}")
            report.append({"topic": topic, "file": filename, "status": "not found"})
            continue
        link, title = result
        pdf = browser.get(link, timeout=120).content
        if pdf[:4] != b"%PDF":                         # every real PDF starts with "%PDF"
            print(f"  download failed: {topic}")
            report.append({"topic": topic, "file": filename, "status": "failed", "url": link})
            continue
        (settings.PDF_FOLDER / filename).write_bytes(pdf)
        print(f"  saved {filename} ({len(pdf) // 1024} KB) - {title[:70]}")
        report.append({"topic": topic, "file": filename, "status": "downloaded", "title": title, "url": link})

    settings.DOWNLOADS_FILE.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print("Step 1: downloading RBI Master Directions")
    download_all()
