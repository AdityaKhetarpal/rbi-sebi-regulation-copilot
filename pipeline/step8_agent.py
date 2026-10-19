"""
STEP 8 - THE AGENT: LET THE AI DECIDE WHAT TO LOOK UP
-----------------------------------------------------
Step 6 searches ONCE and answers ONCE. Some questions need more, e.g.
  "Compare the KYC update rules for high, medium and low risk customers."
An agent is an AI in a loop that can use tools:
    question -> AI thinks "I should search X" -> we run the search -> AI reads the result
             -> AI decides: search again? read a page? or answer now?
Here the AI (Claude) gets two tools: search_rules (step 5) and read_chunk (look up one chunk by id).
Needs ANTHROPIC_API_KEY.

Run:   python pipeline/step8_agent.py "Compare KYC update rules for high and low risk customers"
"""
import json
import sys

import settings
import step5_search

TOOLS = [
    {"name": "search_rules",
     "description": "Search the RBI/SEBI documents. Returns the 5 best chunks with chunk_id, title, page and text.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "read_chunk",
     "description": "Read one chunk in full by its chunk_id.",
     "input_schema": {"type": "object", "properties": {"chunk_id": {"type": "string"}}, "required": ["chunk_id"]}},
]

AGENT_RULES = f"""You research Indian financial regulations (RBI and SEBI) using only your tools.
Plan first: a comparison needs one search per part. Use search_rules, and read_chunk to read more.
Answer in 2-6 sentences, quote numbers exactly, and cite each fact with its chunk_id in brackets,
e.g. [RBI_KYC_Master_Direction_p41_c0]. If the tools don't have it, say: "{settings.NOT_FOUND}" """


def run_tool(name, tool_input):
    """Run one tool and return the result as text for the AI."""
    if name == "search_rules":
        found = step5_search.search(tool_input["query"])
        return found[["chunk_id", "title", "page", "text"]].to_json(orient="records")
    if name == "read_chunk":
        chunks, _, _ = step5_search.load()
        row = chunks[chunks["chunk_id"] == tool_input["chunk_id"]]
        return row.to_json(orient="records") if len(row) else "No chunk with that id."
    return f"Unknown tool: {name}"


def run_agent(question, client=None, max_steps=6):
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]
    steps = []
    for step in range(1, max_steps + 1):
        reply = client.messages.create(model=settings.CLAUDE_MODEL, max_tokens=800, system=AGENT_RULES,
                                       tools=TOOLS, messages=messages)
        if reply.stop_reason != "tool_use":                        # the AI is ready to answer
            answer = " ".join(b.text for b in reply.content if b.type == "text")
            return {"answer": answer, "steps": steps}
        messages.append({"role": "assistant", "content": reply.content})   # remember what it asked for
        results = []
        for block in reply.content:
            if block.type == "tool_use":
                output = run_tool(block.name, block.input)
                steps.append(f"step {step}: {block.name}({json.dumps(block.input)})")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})               # give it the results
    return {"answer": "Stopped: too many steps.", "steps": steps}


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Compare how often KYC must be updated for high, medium and low risk customers."
    out = run_agent(question)
    print("\n".join(out["steps"]))
    print("\n" + out["answer"])
