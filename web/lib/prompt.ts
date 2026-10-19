// The rules the AI must follow, and the helpers that turn found chunks into a prompt and [n] into citations.
import type { Chunk, Citation, Source } from "@/lib/types";

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
