from copilot.retrieve import rrf_merge, tokenize


def test_tokenize():
    assert tokenize("Small PPIs (Rs.10,000)") == ["small", "ppis", "rs", "10", "000"]


def test_rrf_rewards_items_high_in_both_lists():
    scores = rrf_merge([["a", "b", "c"], ["b", "a", "d"]])
    assert max(scores, key=scores.get) in {"a", "b"}
    assert scores["b"] > scores["c"] and scores["a"] > scores["d"]


def test_keyword_finds_exact_terms(retriever):
    assert retriever.keyword("small PPI loaded month", k=1)["chunk_id"][0] == "RBI_PPI_p11_c0"


def test_regulator_filter(retriever):
    found = retriever.keyword("grievances days", k=5, regulator="RBI")
    assert "SEBI" not in set(found["regulator"])


def test_retrieve_uses_the_reranker_order(retriever):
    found = retriever.retrieve("How often must KYC be updated for high-risk customers?", k=2)
    assert found["chunk_id"][0] == "RBI_KYC_p41_c0"
    assert found["rerank"].is_monotonic_decreasing


def test_chunk_lookup(retriever):
    assert retriever.chunk("RBI_PPI_p11_c0")["page"] == 11
    assert retriever.chunk("nope") is None
