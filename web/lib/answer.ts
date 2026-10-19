// STEP 6 on the website - answer only from the passages found (same idea as pipeline/step6_answer.py).
//   R: search (lib/search.ts)  ->  A: number the passages [1]..[6]  ->  G: Claude writes, or quote mode picks sentences
// Safety check first: if the passages don't really match the question, say "I couldn't find this..." instead of guessing.

import type { AskResult, Chunk, Citation, Source } from "@/lib/types";
import { Searcher, RELEVANCE, extractive } from "@/lib/search";

export const REFUSAL = "I couldn't find this in the provided RBI/SEBI documents.";
export const MAX_QUESTION = 300;

export const SYSTEM = `You answer questions about Indian financial regulations using ONLY the numbered sources provided.

Rules:
1. Every factual sentence must end with its source number in square brackets, e.g. [2].
2. Quote numbers, limits and deadlines exactly as written in the sources.
3. If the sources do not contain the answer, say exactly: "${REFUSAL}" Do not guess or use outside knowledge.
4. If the sources only partly answer, say what is covered and what is missing.
5. Keep it short: 2-5 sentences. Plain English.
6. This is information, not legal advice.`;

export function numbered(found: Chunk[]): Source[] {
  return found.map((c, i) => ({ ...c, n: i + 1 }));
}

export function buildContext(sources: Source[]): string {
  return sources.map((s) => `[${s.n}] ${s.title}, page ${s.page}\n${s.text}`).join("\n\n");
}

export function citations(answer: string, sources: Source[]): Citation[] {
  const used = [...new Set([...answer.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1])))]
    .filter((n) => n >= 1 && n <= sources.length)
    .sort((a, b) => a - b);
  return used.map((n) => ({ n, id: sources[n - 1].id, title: sources[n - 1].title, page: sources[n - 1].page }));
}

export function validateQuestion(q: unknown): { ok: true; question: string } | { ok: false; error: string } {
  if (typeof q !== "string" || !q.trim()) return { ok: false, error: "Please type a question." };
  if (q.length > MAX_QUESTION) return { ok: false, error: `Please keep questions under ${MAX_QUESTION} characters.` };
  return { ok: true, question: q.trim() };
}

export const MODEL = process.env.ASK_MODEL ?? "claude-haiku-5-5";
export const TOP_K = 6; // keyword search needs one more passage than the Python hybrid search (measured on the eval set)

// the only part of the Anthropic client we use, so tests can pass a fake one
type Block = { type: string; text?: string; id?: string; name?: string; input?: Record<string, unknown> };
export type LLM = { messages: { create(params: Record<string, unknown>): Promise<{ stop_reason: string | null; content: Block[] }> } };

export const textOf = (content: Block[]) => content.filter((b) => b.type === "text").map((b) => b.text ?? "").join("\n").trim();

function refusal(question: string, sources: Source[], engine = "relevance check"): AskResult {
  return { question, answer: REFUSAL, engine, refused: true, citations: [], sources };
}

export async function answer(question: string, s: Searcher, client: LLM | null): Promise<AskResult> {
  const sources = numbered(s.search(question, TOP_K));                   // R
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
