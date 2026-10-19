// POST /api/ask -> answer from the RBI/SEBI chunks only. GET /api/ask -> what this deployment can do.
// Runs on the server, so an API key (if set in Vercel) never reaches the visitor's browser.

import Anthropic from "@anthropic-ai/sdk";
import { Searcher } from "@/lib/search";
import { validateQuestion } from "@/lib/prompt";
import { agent, answer, type LLM } from "@/lib/copilot";
import chunks from "@/public/data/chunks.json";
import documents from "@/public/data/documents.json";
import type { Chunk, Doc } from "@/lib/types";

export const maxDuration = 60;

const searcher = new Searcher(chunks as Chunk[]);                 // built once per server instance
const docs = (documents as Doc[]).map(({ regulator, title, pages }) => ({ regulator, title, pages }));

const LIMIT = 8;                       // AI questions per visitor...
const WINDOW_MS = 10 * 60 * 1000;      // ...per 10 minutes; the provider's monthly spend cap is the hard stop
const hits = new Map<string, number[]>();
function allowed(ip: string): boolean {
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS);
  if (recent.length >= LIMIT) return false;
  hits.set(ip, [...recent, now]);
  return true;
}

export async function GET() {
  return Response.json({ ai: Boolean(process.env.ANTHROPIC_API_KEY), chunks: searcher.chunks.length });
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const check = validateQuestion(body?.question);
  if (!check.ok) return Response.json({ error: check.error }, { status: 400 });
  if (!searcher.chunks.length) return Response.json({ error: "The document index hasn't been built yet." }, { status: 503 });

  const regulator = body?.regulator === "RBI" || body?.regulator === "SEBI" ? body.regulator : undefined;
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "local";
  const client: LLM | null = process.env.ANTHROPIC_API_KEY && allowed(ip) ? (new Anthropic() as unknown as LLM) : null;

  if (body?.mode === "agent") {
    if (!client) {
      const r = await answer(check.question, searcher, null, regulator);
      return Response.json({ ...r, note: "Agent mode needs the AI key, so this is the single-step answer." });
    }
    try {
      return Response.json(await agent(check.question, searcher, client, docs));
    } catch (err) {
      console.error("[ask] agent failed:", err);
      const r = await answer(check.question, searcher, null, regulator);
      return Response.json({ ...r, note: "The agent was unavailable, so this is the single-step answer." });
    }
  }
  return Response.json(await answer(check.question, searcher, client, regulator));
}
