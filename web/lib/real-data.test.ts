// Runs the evaluation questions against the REAL index once it has been built (skipped while chunks.json is empty).
// This is how the site's relevance threshold is checked on actual RBI/SEBI text.
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { Searcher, RELEVANCE } from "@/lib/search";
import { answer } from "@/lib/answer";
import chunks from "@/public/data/chunks.json";
import type { Chunk } from "@/lib/types";

type Q = { id: string; kind: "fact" | "refuse"; question: string; must_include?: string[] };
const questions: Q[] = JSON.parse(readFileSync(new URL("../../data/test_questions.json", import.meta.url), "utf-8"));
const norm = (t: string) => t.toLowerCase().replace(/[\s,/-]/g, "");
const real = (chunks as Chunk[]).length > 0;

describe.skipIf(!real)("website pipeline on the real documents", () => {
  const s = new Searcher(chunks as Chunk[]);
  for (const q of questions) {
    it(`${q.kind}: ${q.id}`, async () => {
      const r = await answer(q.question, s, null);
      const rel = s.relevance(q.question, r.sources);
      if (q.kind === "refuse") {
        expect(r.refused, `relevance ${rel.toFixed(2)}`).toBe(true);
      } else {
        expect(rel, "relevance").toBeGreaterThanOrEqual(RELEVANCE);
        expect(r.sources.some((src) => norm(src.text).includes(norm(q.must_include![0])))).toBe(true);
      }
    });
  }
});
