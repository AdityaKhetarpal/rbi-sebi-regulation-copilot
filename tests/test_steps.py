"""One small test per step, in the same order as the pipeline."""
import json
from types import SimpleNamespace as NS

import pandas as pd
import pymupdf

import settings
import step1_download
import step2_read_pdfs
import step3_chunk
import step5_search
import step6_answer
import step7_test
import step8_agent


# ---------- step 1: download ----------
LIST_PAGE = """
<td><span>Prepaid Payment Instruments - notification <a href='https://rbidocs.rbi.org.in/rdocs/notification/PDFs/NOT385.PDF'>pdf</a></td>
<td>Master Direction on Prepaid Payment Instruments (PPIs) <a href='https://rbidocs.rbi.org.in/rdocs/notification/PDFs/82MDPPIS27.PDF'>pdf</a></td>
<td>Know Your Customer - Ombudsman scheme <a href='https://rbidocs.rbi.org.in/rdocs/PDFs/OMB.PDF'>pdf</a></td>
<td>Reserve Bank of India (Know Your Customer) Directions, 2025 <a href='https://rbidocs.rbi.org.in/rdocs/notification/PDFs/169MD.PDF'>pdf</a></td>
"""


def test_step1_prefers_the_master_direction_and_skips_ombudsman():
    link, title = step1_download.find_pdf(LIST_PAGE, "Prepaid Payment Instruments")
    assert link.endswith("82MDPPIS27.PDF") and title.startswith("Master Direction on Prepaid")
    link, title = step1_download.find_pdf(LIST_PAGE, "Know Your Customer")
    assert link.endswith("169MD.PDF") and title.startswith("Reserve Bank of India (Know Your Customer)")
    assert step1_download.find_pdf(LIST_PAGE, "Digital Lending") is None


# ---------- step 2: read PDFs ----------
def test_step2_reads_every_page_with_regulator_and_title(tmp_path):
    pdf = pymupdf.open()
    for text in ["Page one about KYC rules for banks and their customers", "Page two"]:
        pdf.new_page().insert_text((72, 72), text)
    pdf.save(tmp_path / "RBI_KYC_Master_Direction.pdf")
    pages = step2_read_pdfs.read_all_pdfs(tmp_path)
    assert list(pages["page"]) == [1, 2]
    assert set(pages["regulator"]) == {"RBI"} and set(pages["title"]) == {"KYC Master Direction"}


# ---------- step 3: chunk ----------
def test_step3_chunks_overlap_and_keep_pages():
    chunks = step3_chunk.make_chunks(" ".join(f"w{i}" for i in range(700)), size=300, overlap=50)
    assert len(chunks) == 3 and chunks[1].split()[0] == "w250" and chunks[-1].split()[-1] == "w699"
    assert step3_chunk.clean("regu-\nlation  of KYC") == "regulation of KYC"
    pages = pd.DataFrame([{"file": "RBI_KYC.pdf", "regulator": "RBI", "title": "KYC", "page": 12, "text": "a " * 400},
                          {"file": "RBI_KYC.pdf", "regulator": "RBI", "title": "KYC", "page": 13, "text": float("nan")}])
    out = step3_chunk.chunk_all(pages)
    assert list(out["chunk_id"]) == ["RBI_KYC_p12_c0", "RBI_KYC_p12_c1"]     # the empty page adds nothing


# ---------- step 5: search ----------
def test_step5_combine_rewards_items_high_in_both_lists():
    order = step5_search.combine(pd.DataFrame({"chunk_id": ["a", "b", "c"]}), pd.DataFrame({"chunk_id": ["b", "a", "d"]}))
    assert set(order[:2]) == {"a", "b"} and order.index("c") > 1


def test_step5_search_finds_the_rule():
    found = step5_search.search("How often must KYC be updated for high-risk customers?", top_k=2)
    assert found["chunk_id"][0] == "RBI_KYC_p41_c0"
    assert found["score"].is_monotonic_decreasing


# ---------- step 6: answer ----------
def test_step6_quotes_the_rule_with_its_source():
    out = step6_answer.ask("What is the maximum amount loaded in small PPIs during a month?")
    assert out["method"] == "quote (no AI)"
    assert "Rs.10,000" in out["answer"] and out["citations"][0] == "[1] PPI Master Direction, p.11"


def test_step6_refuses_questions_the_documents_dont_cover():
    out = step6_answer.ask("What is the current repo rate?")
    assert out["answer"] == settings.NOT_FOUND and out["method"] == "not in the documents"


def test_step6_citations_ignore_numbers_out_of_range():
    found = step5_search.load()[0].head(2)
    assert step6_answer.citations("A [2]. B [1]. C [9].", found) == ["[1] KYC Master Direction, p.41", "[2] PPI Master Direction, p.11"]


# ---------- step 7: test ----------
def test_step7_scores_facts_and_refusals():
    questions = json.loads(settings.QUESTIONS_FILE.read_text())
    assert {q["kind"] for q in questions} == {"fact", "refuse"}
    report = step7_test.run_tests([
        {"id": "kyc", "kind": "fact", "question": "How often must KYC be updated for high-risk customers?", "expect_doc": "KYC", "must_include": ["two years"]},
        {"id": "repo", "kind": "refuse", "question": "What is the current repo rate?"},
    ])
    assert report["summary"] == {"questions": 2, "found_pct": 100.0, "right_pct": 100.0, "refused_pct": 100.0}
    assert step7_test.loose("1,20,000") in step7_test.loose("Rs.1,20,000/-")


# ---------- step 8: agent ----------
class FakeClaude:
    """Plays back scripted replies: first 'use the search tool', then a final answer."""
    def __init__(self, replies):
        self.replies, self.calls, self.messages = list(replies), [], self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


def test_step8_agent_uses_a_tool_then_answers():
    client = FakeClaude([
        NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t1", name="search_rules", input={"query": "KYC high risk"})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="Every two years [RBI_KYC_p41_c0].")]),
    ])
    out = step8_agent.run_agent("How often is KYC updated for high-risk customers?", client=client)
    assert out["answer"] == "Every two years [RBI_KYC_p41_c0]."
    assert out["steps"][0].startswith("step 1: search_rules")
    sent_back = client.calls[1]["messages"][-1]["content"][0]
    assert sent_back["type"] == "tool_result" and "RBI_KYC_p41_c0" in sent_back["content"]


def test_step8_agent_stops_after_max_steps():
    loop = NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t", name="read_chunk", input={"chunk_id": "x"})])
    out = step8_agent.run_agent("loop", client=FakeClaude([loop] * 3), max_steps=3)
    assert out["answer"].startswith("Stopped")
