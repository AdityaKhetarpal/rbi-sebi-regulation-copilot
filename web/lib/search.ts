// STEP 5 on the website - find the best passages for a question (same idea as pipeline/step5_search.py).
// The website uses keyword search (BM25, the classic search-engine formula) so it runs instantly without
// loading AI models, plus a relevance check that lets it say "not in the documents" instead of guessing.

import type { Chunk } from "@/lib/types";

export const tokenize = (text: string): string[] => text.toLowerCase().match(/[a-z0-9]+/g) ?? [];

const STOP = new Set(["the", "a", "an", "of", "in", "to", "is", "are", "what", "how", "for", "must", "be", "by", "on",
  "and", "or", "can", "does", "do", "which", "who", "when", "within", "under", "with", "as", "at", "it", "that",
  "many", "much", "there", "any", "i", "my", "we", "this", "from", "per", "will", "should", "about", "why", "where",
  "whom", "whose", "has", "have", "was", "were", "if", "than", "then", "so", "its", "into", "our", "your", "their"]);

// "updated" and "updation" should count as the same word: compare the first 5 letters
const stem = (w: string) => {
  const base = w.length > 4 ? w.replace(/(es|s)$/, "") : w;     // plural -> singular: "ppis" -> "ppi"
  return base.length > 5 ? base.slice(0, 5) : base;               // "updated", "updation" -> "updat"
};

export class BM25 {
  private docs: Map<string, number>[];
  private lengths: number[];
  private avgdl: number;
  private idf = new Map<string, number>();
  private stemDf = new Map<string, number>();
  readonly n: number;
  constructor(texts: string[], private k1 = 1.5, private b = 0.75, epsilon = 0.25) {
    this.n = texts.length;
    this.docs = texts.map((t) => {
      const m = new Map<string, number>();
      for (const w of tokenize(t)) m.set(w, (m.get(w) ?? 0) + 1);
      return m;
    });
    this.lengths = this.docs.map((d) => [...d.values()].reduce((a, c) => a + c, 0));
    this.avgdl = this.lengths.reduce((a, c) => a + c, 0) / Math.max(1, this.n);

    const df = new Map<string, number>();
    for (const d of this.docs) for (const w of d.keys()) df.set(w, (df.get(w) ?? 0) + 1);
    let sum = 0;
    const neg: string[] = [];
    for (const [w, f] of df) {
      const v = Math.log(this.n - f + 0.5) - Math.log(f + 0.5);
      this.idf.set(w, v);
      sum += v;
      if (v < 0) neg.push(w);
    }
    const eps = epsilon * (sum / Math.max(1, df.size));            // rank_bm25: very common words get a small positive idf
    for (const w of neg) this.idf.set(w, eps);
    for (const d of this.docs) for (const s of new Set([...d.keys()].map(stem))) this.stemDf.set(s, (this.stemDf.get(s) ?? 0) + 1);
  }

  scores(query: string): number[] {
    const q = tokenize(query);
    return this.docs.map((d, i) => {
      let s = 0;
      for (const w of q) {
        const f = d.get(w);
        if (!f) continue;
        s += (this.idf.get(w) ?? 0) * (f * (this.k1 + 1)) / (f + this.k1 * (1 - this.b + (this.b * this.lengths[i]) / this.avgdl));
      }
      return s;
    });
  }

  // how rare a word is across all chunks; words that never appear count as the rarest
  weight(word: string): number {
    const f = this.stemDf.get(stem(word)) ?? 0;
    return Math.log((this.n + 1) / (f + 0.5));
  }
}

// Share of the question's meaningful words found in a text, weighted by rarity.
// "current repo rate": "repo" never appears in our documents and is rare, so coverage stays low -> refuse.
export function coverage(question: string, text: string, bm: BM25): number {
  const words = [...new Set(tokenize(question).filter((w) => !STOP.has(w)))];
  if (!words.length) return 0;
  const have = new Set(tokenize(text).map(stem));
  let found = 0, total = 0;
  for (const w of words) {
    const wt = bm.weight(w);
    total += wt;
    if (have.has(stem(w))) found += wt;
  }
  return total > 0 ? found / total : 0;
}

export const RELEVANCE = 0.5; // below this, "not in the documents". Calibrated on the real index: real questions 0.62-1.0, off-topic 0.18-0.38
const SENTENCE_FLOOR = 0.25; // a quoted sentence must cover at least this much of the question

export class Searcher {
  readonly bm: BM25;
  constructor(readonly chunks: Chunk[]) {
    this.bm = new BM25(chunks.map((c) => c.text));
  }

  search(question: string, k = 5, regulator?: string): Chunk[] {
    const s = this.bm.scores(question);
    return this.chunks
      .map((c, i) => ({ c, s: s[i] }))
      .filter((x) => x.s > 0 && (!regulator || x.c.regulator.toUpperCase() === regulator.toUpperCase()))
      .sort((a, b) => b.s - a.s)
      .slice(0, k)
      .map((x) => x.c);
  }

  // best coverage among the found chunks: are the documents actually about this?
  relevance(question: string, found: Chunk[]): number {
    return Math.max(0, ...found.map((c) => coverage(question, c.text, this.bm)));
  }

  get(id: string): Chunk | undefined {
    return this.chunks.find((c) => c.id === id);
  }
}

export function splitSentences(text: string): string[] {
  return text.split(/(?<=[.;:])\s+/).map((s) => s.trim()).filter((s) => {
    const n = s.split(/\s+/).length;
    return n >= 8 && n <= 80;
  });
}

// Engine 3 on the website: the best sentences, word for word, each with its source number
export function extractive(question: string, found: Chunk[], bm: BM25, n = 2): string | null {
  const cands = found.flatMap((c, i) => splitSentences(c.text).map((s) => ({ i: i + 1, s, score: coverage(question, s, bm) + (/\d/.test(s) ? 0.05 : 0) })));
  const keep = cands.sort((a, b) => b.score - a.score).filter((x) => x.score >= SENTENCE_FLOOR).slice(0, n);
  if (!keep.length) return null;
  return keep.map((x) => `${x.s} [${x.i}]`).join(" ");
}
