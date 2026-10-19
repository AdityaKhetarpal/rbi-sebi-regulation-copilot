from types import SimpleNamespace as NS

from copilot.agent import run_agent, run_tool


class FakeClient:
    """Plays back scripted model turns: first a tool call, then a final answer."""
    def __init__(self, turns):
        self.turns, self.calls = list(turns), []
        self.messages = self
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.turns.pop(0)


def tool_turn(name, args):
    return NS(stop_reason="tool_use", content=[NS(type="text", text="I'll search."),
                                               NS(type="tool_use", id="t1", name=name, input=args)])


def final_turn(text):
    return NS(stop_reason="end_turn", content=[NS(type="text", text=text)])


def test_agent_searches_then_answers_with_citations(retriever):
    client = FakeClient([tool_turn("search_regulations", {"query": "KYC high risk"}),
                         final_turn("At least once every two years [RBI_KYC_p41_c0].")])
    out = run_agent("How often is KYC updated for high-risk customers?", retriever, [], client=client)
    assert out["steps"] == 2
    assert out["trace"][0]["tool"] == "search_regulations"
    assert out["citations"] == [{"chunk_id": "RBI_KYC_p41_c0", "title": "KYC Master Direction", "page": 41}]
    tool_result = client.calls[1]["messages"][-1]["content"][0]          # the search result was sent back
    assert tool_result["type"] == "tool_result" and "RBI_KYC_p41_c0" in tool_result["content"]


def test_agent_stops_after_max_steps(retriever):
    client = FakeClient([tool_turn("list_documents", {}) for _ in range(3)])
    out = run_agent("loop forever", retriever, [{"regulator": "RBI", "title": "KYC", "pages": 80}], client=client, max_steps=3)
    assert out["steps"] == 3 and "Stopped" in out["answer"]


def test_tools(retriever):
    assert "RBI_PPI_p11_c0" in run_tool("search_regulations", {"query": "small PPI month"}, retriever, [])
    assert "SEBI" not in run_tool("search_regulations", {"query": "grievances", "regulator": "RBI"}, retriever, []).replace("SEBI_", "")
    assert run_tool("read_chunk", {"chunk_id": "missing"}, retriever, []) == "No chunk with that id."
    assert run_tool("nope", {}, retriever, []).startswith("Unknown tool")
