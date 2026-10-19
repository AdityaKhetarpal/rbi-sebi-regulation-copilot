import pymupdf

from copilot.ingest import clean_title, document_list, find_pdf, load_pages

PAGE = """
<td>Know Your Customer (KYC) - Ombudsman Directions <a href='https://rbidocs.rbi.org.in/rdocs/PDFs/OMB.PDF'>pdf</a></td>
<td>Reserve Bank of India (Know Your Customer) Directions, 2025 (Updated as on October 1, 2026) <a id='APDF_1' href='https://rbidocs.rbi.org.in/rdocs/notification/PDFs/169MD.PDF'>pdf</a></td>
"""


def test_find_pdf_skips_ombudsman_and_finds_main_direction():
    url, title = find_pdf(PAGE, "Know Your Customer")
    assert url.endswith("169MD.PDF")
    assert "Updated as on October 1, 2026" in title
    assert title.startswith("Reserve Bank of India (Know Your Customer)")
    assert "<a" not in title


def test_find_pdf_returns_none_when_missing():
    assert find_pdf(PAGE, "Digital Lending") is None


def test_clean_title():
    assert clean_title("Payment Aggregator (PA)   <a id='APDF_141'") == "Payment Aggregator (PA)"


def test_load_pages_reads_regulator_title_and_pages(tmp_path):
    doc = pymupdf.open()
    for text in ["First page about KYC rules for banks and customers today", "Second page"]:
        doc.new_page().insert_text((72, 72), text)
    doc.save(tmp_path / "RBI_KYC_Master_Direction.pdf")
    pages = load_pages(tmp_path)
    assert list(pages["page"]) == [1, 2]
    assert set(pages["regulator"]) == {"RBI"}
    assert set(pages["title"]) == {"KYC Master Direction"}
    docs = document_list(pages, [{"file": "RBI_KYC_Master_Direction.pdf", "url": "u", "title": "T"}])
    assert docs[0]["pages"] == 2 and docs[0]["empty_pages"] == 2 and docs[0]["url"] == "u"
