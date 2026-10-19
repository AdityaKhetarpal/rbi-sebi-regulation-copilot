"""Step 6 - The agent: Claude decides which tools to call, reads the results, and repeats until it can answer.

RAG answers in one shot: search once, write once. The agent can search several times - for example once
for each regulator when comparing - open a specific chunk, or check which documents exist, before answering.
"""
import json
import os
import re

from . import config

AGENT_SYSTEM = """You are a compliance research assistant for Indian financial regulations (RBI and SEBI).
You can only use facts returned by your tools.

How to work:
1. Plan: decide what you need to look up. Comparisons or multi-part questions need one search per part.
2. Use search_regulations (optionally filtered by regulator). Use read_chunk to read a promising result in full.
3. When you have enough, answer in 2-6 sentences. Quote numbers and deadlines exactly.
4. Cite every fact with the chunk id in square brackets, e.g. [RBI_KYC_Master_Direction_p41_c0].
5. If the tools do not contain the answer, say exactly: "I couldn't find this in the provided RBI/SEBI documents."
This is information, not legal advice."""

TOOLS = [
    {"name": "search_regulations",
     "description": "Search the RBI/SEBI documents. Returns the 5 most relevant chunks with chunk_id, document title, page and text.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What to look for, in plain English"},
         "regulator": {"type": "string", "enum": ["RBI", "SEBI"], "description": "Optional: search one regulator only"}},
         "required": ["query"]}},
    {"name": "read_chunk",
     "description": "Read one chunk in full by its chunk_id.",
     "input_schema": {"type": "object", "properties": {"chunk_id": {"type": "string"}}, "required": ["chunk_id"]}},
    {"name": "list_documents",
     "description": "List the documents available, with regulator, title and number of pages.",
     "input_schema": {"type": "object", "properties": {}}},
]


def run_tool(name: str, args: dict, retriever, documents: list[dict]) -> str:
    """Run one tool and return its result as text for the model."""
    if name == "search_regulations":
        found = retriever.retrieve(args["query"], k=config.TOP_K, regulator=args.get("regulator"))
        return json.dumps([{"chunk_id": r.chunk_id, "title": r.title, "page": int(r.page), "text": r.text}
                           for r in found.itertuples()], ensure_ascii=False)
    if name == "read_chunk":
        c = retriever.chunk(args["chunk_id"])
        return json.dumps(c, ensure_ascii=False) if c else "No chunk with that id."
    if name == "list_documents":
        return json.dumps([{k: d.get(k) for k in ("regulator", "title", "pages")} for d in documents], ensure_ascii=False)
    return f"Unknown tool: {name}"


def readable_citations(answer: str, retriever) -> list[dict]:
    ids = dict.fromkeys(re.findall(r"\[([A-Za-z0-9_]+_p\d+_c\d+)\]", answer))       # keep order, drop repeats
    out = []
    for cid in ids:
        c = retriever.chunk(cid)
        if c:
            out.append({"chunk_id": cid, "title": c["title"], "page": int(c["page"])})
    return out


def run_agent(question: str, retriever, documents: list[dict], client=None, max_steps: int = 6) -> dict:
    """The agent loop. Returns the answer, its citations and a step-by-step trace."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages = [{"role": "user", "content": question}]
    trace = []
    for step in range(1, max_steps + 1):
        r = client.messages.create(model=config.CLAUDE_MODEL, max_tokens=800, system=AGENT_SYSTEM,
                                   tools=TOOLS, messages=messages)
        thoughts = " ".join(b.text for b in r.content if b.type == "text").strip()
        if r.stop_reason != "tool_use":                                   # the model is ready to answer
            trace.append({"step": step, "type": "answer"})
            return {"question": question, "answer": thoughts, "citations": readable_citations(thoughts, retriever),
                    "trace": trace, "steps": step}

        messages.append({"role": "assistant", "content": r.content})
        results = []
        for block in r.content:
            if block.type != "tool_use":
                continue
            output = run_tool(block.name, block.input, retriever, documents)
            trace.append({"step": step, "type": "tool", "tool": block.name, "input": block.input,
                          "thought": thoughts, "result_preview": output[:300]})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})

    return {"question": question, "answer": f"Stopped after {max_steps} steps without a final answer.",
            "citations": [], "trace": trace, "steps": max_steps}
