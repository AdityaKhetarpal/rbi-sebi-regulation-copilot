// The website's question answering: retrieve -> (refuse if off-topic) -> write with the best available engine.
// Also the agent: Claude picks tools in a loop. Kept free of Next.js so it can be tested directly.

import type { AskResult, Chunk, Source, Step } from "@/lib/types";
import { Searcher, RELEVANCE, extractive } from "@/lib/search";
import { REFUSAL, SYSTEM, buildContext, citations, numbered } from "@/lib/prompt";

export const MODEL = process.env.ASK_MODEL ?? "claude-haiku-5-5";
export const TOP_K = 6; // keyword search needs one more passage than the Python hybrid search (measured on the eval set)

// the only part of the Anthropic client we use, so tests can pass a fake
type Block = { type: string; text?: string; id?: string; name?: string; input?: Record<string, unknown> };
export type LLM = { messages: { create(params: Record<string, unknown>): Promise<{ stop_reason: string | null; content: Block[] }> } };

const textOf = (content: Block[]) => content.filter((b) => b.type === "text").map((b) => b.text ?? "").join("\n").trim();

function refusal(question: string, sources: Source[], engine = "relevance check"): AskResult {
  return { question, answer: REFUSAL, engine, refused: true, citations: [], sources };
}

// ---------- RAG: one search, one answer ----------
export async function answer(question: string, s: Searcher, client: LLM | null, regulator?: string): Promise<AskResult> {
  const sources = numbered(s.search(question, TOP_K, regulator));                   // R
  if (!sources.length || s.relevance(question, sources) < RELEVANCE) return refusal(question, sources);

  if (client) {
    try {
      const r = await client.messages.create({
        model: MODEL, max_tokens: 400, system: SYSTEM,
        messages: [{ role: "user", content: `Sources:\n\n${buildContext(sources)}\n\nQuestion: ${question}` }],  // A
      });
      const text = textOf(r.content);                                                   // G
      return { question, answer: text, engine: `Claude (${MODEL})`, refused: text.startsWith(REFUSAL.slice(0, 25)),
               citations: citations(text, sources), sources };
    } catch (err) {
      console.error("[ask] Claude failed, falling back to extractive:", err);
    }
  }
  const text = extractive(question, sources, s.bm);
  if (!text) return refusal(question, sources, "Extractive (exact sentences, no AI)");
  return { question, answer: text, engine: "Extractive (exact sentences, no AI)", refused: false,
           citations: citations(text, sources), sources };
}

// ---------- Agent: Claude decides which tools to call ----------
export const AGENT_SYSTEM = `You are a compliance research assistant for Indian financial regulations (RBI and SEBI).
You can only use facts returned by your tools.
1. Plan what you need. Comparisons or multi-part questions need one search per part.
2. Use search_regulations (optionally filtered by regulator) and read_chunk to read a result in full.
3. Answer in 2-6 sentences. Quote numbers and deadlines exactly.
4. Cite every fact with its chunk id in square brackets, e.g. [RBI_KYC_Master_Direction_p41_c0].
5. If the tools do not contain the answer, say exactly: "${REFUSAL}"
This is information, not legal advice.`;

export const TOOLS = [
  { name: "search_regulations", description: "Search the RBI/SEBI documents. Returns the 5 most relevant chunks with id, title, page and text.",
    input_schema: { type: "object", properties: { query: { type: "string" }, regulator: { type: "string", enum: ["RBI", "SEBI"] } }, required: ["query"] } },
  { name: "read_chunk", description: "Read one chunk in full by its id.",
    input_schema: { type: "object", properties: { chunk_id: { type: "string" } }, required: ["chunk_id"] } },
  { name: "list_documents", description: "List the documents available, with regulator, title and pages.",
    input_schema: { type: "object", properties: {} } },
];

export function runTool(name: string, input: Record<string, unknown>, s: Searcher, docs: { regulator: string; title: string; pages: number }[]): string {
  if (name === "search_regulations") {
    return JSON.stringify(s.search(String(input.query ?? ""), 5, input.regulator ? String(input.regulator) : undefined));
  }
  if (name === "read_chunk") {
    const c = s.get(String(input.chunk_id ?? ""));
    return c ? JSON.stringify(c) : "No chunk with that id.";
  }
  if (name === "list_documents") return JSON.stringify(docs.map(({ regulator, title, pages }) => ({ regulator, title, pages })));
  return `Unknown tool: ${name}`;
}

export async function agent(question: string, s: Searcher, client: LLM, docs: { regulator: string; title: string; pages: number }[], maxSteps = 5): Promise<AskResult> {
  const messages: Record<string, unknown>[] = [{ role: "user", content: question }];
  const trace: Step[] = [];
  for (let step = 1; step <= maxSteps; step++) {
    const r = await client.messages.create({ model: MODEL, max_tokens: 800, system: AGENT_SYSTEM, tools: TOOLS, messages });
    if (r.stop_reason !== "tool_use") {
      // turn [chunk_id] citations into numbered sources the page can show
      const ids = [...new Set([...textOf(r.content).matchAll(/\[([A-Za-z0-9_]+_p\d+_c\d+)\]/g)].map((m) => m[1]))];
      const cited = ids.map((id) => s.get(id)).filter((c): c is Chunk => Boolean(c));
      const sources = numbered(cited);
      let text = textOf(r.content);
      sources.forEach((src) => { text = text.replaceAll(`[${src.id}]`, `[${src.n}]`); });
      return { question, answer: text, engine: `Agent · Claude (${MODEL})`, refused: text.startsWith(REFUSAL.slice(0, 25)),
               citations: citations(text, sources), sources, trace };
    }
    messages.push({ role: "assistant", content: r.content });
    const results = r.content.filter((b) => b.type === "tool_use").map((b) => {
      const output = runTool(b.name ?? "", b.input ?? {}, s, docs);
      trace.push({ step, tool: b.name ?? "", input: b.input ?? {}, preview: output.slice(0, 240) });
      return { type: "tool_result", tool_use_id: b.id, content: output };
    });
    messages.push({ role: "user", content: results });
  }
  return { question, answer: `Stopped after ${maxSteps} steps without a final answer.`, engine: "Agent", refused: false,
           citations: [], sources: [], trace };
}
