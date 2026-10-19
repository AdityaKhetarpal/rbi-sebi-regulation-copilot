import pandas as pd
import pytest

from copilot.chunking import build_chunks, clean, make_chunks, split_sentences


def test_chunk_count_and_overlap():
    words = [f"w{i}" for i in range(700)]
    chunks = make_chunks(" ".join(words), size=300, overlap=50)
    assert len(chunks) == 3                                   # 0-299, 250-549, 500-699
    assert chunks[1].split()[0] == "w250"                     # 50 words repeated
    assert chunks[-1].split()[-1] == "w699"                   # nothing lost at the end


def test_short_text_is_one_chunk_and_empty_is_none():
    assert make_chunks("just a few words") == ["just a few words"]
    assert make_chunks("") == []


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        make_chunks("a b c", size=10, overlap=10)


def test_clean_joins_broken_words_and_spaces():
    assert clean("regu-\nlation   of KYC\n\n\n\nnext") == "regulation of KYC\n\nnext"


def test_build_chunks_keeps_document_and_page():
    pages = pd.DataFrame([{"file": "RBI_KYC.pdf", "regulator": "RBI", "title": "KYC", "page": 12, "text": "a " * 400}])
    out = build_chunks(pages)
    assert list(out["chunk_id"]) == ["RBI_KYC_p12_c0", "RBI_KYC_p12_c1"]
    assert set(out["page"]) == {12}


def test_split_sentences_keeps_sensible_lengths():
    text = "Too short. The bank shall carry out periodic updation at least once in every two years; next clause here is fine too."
    out = split_sentences(text)
    assert out[0].startswith("The bank shall")
    assert all(len(s.split()) >= 8 for s in out)
