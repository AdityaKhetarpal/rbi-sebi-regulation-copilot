import pandas as pd

from copilot import config
from copilot.answer import ExtractiveEngine, ask, build_context, citations


def test_context_numbers_sources_with_title_and_page(chunks):
    ctx = build_context(chunks.head(2))
    assert ctx.startswith("[1] KYC Master Direction, page 41")
    assert "[2] PPI Master Direction, page 11" in ctx


def test_citations_ignore_out_of_range_numbers(chunks):
    found = chunks.head(2)
    out = citations("Two years [1]. Rs.10,000 [2]. Made up [9].", found)
    assert [(c["n"], c["page"]) for c in out] == [(1, 41), (2, 11)]


def test_extractive_picks_the_rule(retriever, reranker):
    q = "How often must KYC be updated for high-risk customers?"
    found = retriever.retrieve(q)
    out = ExtractiveEngine(reranker).generate(q, build_context(found), found)
    assert "two years" in out and "[1]" in out


def test_off_topic_question_is_refused_before_any_engine(retriever):
    class Boom:
        name = "boom"
        def generate(self, *a):
            raise AssertionError("should not be called")
    out = ask("Who won the cricket final?", retriever, [Boom()])
    assert out["refused"] and out["answer"] == config.REFUSAL and out["engine"] == "retrieval threshold"


def test_falls_back_when_an_engine_fails(retriever, reranker):
    class Broken:
        name = "broken"
        def generate(self, *a):
            raise RuntimeError("no credit")
    out = ask("What is the monthly loading limit for small PPIs?", retriever, [Broken(), ExtractiveEngine(reranker)])
    assert out["engine"].startswith("Extractive")
    assert "10,000" in out["answer"]
    assert out["citations"][0]["title"] == "PPI Master Direction"


def test_extractive_without_reranker_still_refuses_unrelated_text():
    found = pd.DataFrame([{"chunk_id": "x", "title": "T", "page": 1,
                           "text": "The bank shall verify the current address through positive confirmation before operations."}])
    out = ExtractiveEngine(reranker=None).generate("What is the current repo rate?", "", found)
    assert out == config.REFUSAL
