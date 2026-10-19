import { describe, expect, it } from "vitest";
import { Searcher, coverage, extractive, splitSentences, tokenize } from "@/lib/search";
import { REFUSAL, answer, buildContext, citations, numbered, validateQuestion, type LLM } from "@/lib/answer";
import { agent, runTool } from "@/lib/agent";
import type { Chunk } from "@/lib/types";

const CHUNKS: Chunk[] = [
  { id: "RBI_KYC_Master_Direction_p41_c0", regulator: "RBI", title: "KYC Master Direction", page: 41,
    text: "However, the bank shall carry out periodic updation at least once in every two years for high-risk customers, once in every eight years for medium risk customers and once in every 10 years for low-risk customers. The bank shall verify the current address through positive confirmation before allowing operations." },
  { id: "RBI_PPI_Master_Direction_p11_c0", regulator: "RBI", title: "PPI Master Direction", page: 11,
    text: "d) The amount loaded in such PPIs during any month shall not exceed Rs.10,000 and the total amount loaded during the financial year shall not exceed Rs.1,20,000; e) The amount outstanding at any point of time in such PPIs shall not exceed Rs.10,000." },
  { id: "RBI_Fraud_Risk_Management_p24_c0", regulator: "RBI", title: "Fraud Risk Management", page: 24,
    text: "The bank shall report instances of theft, burglary, dacoity and robbery to Fraud Monitoring Group, Reserve Bank of India, immediately (not later than seven days) from their occurrence." },
  { id: "SEBI_Master_Circular_Stock_Brokers_p3_c0", regulator: "SEBI", title: "Master Circular Stock Brokers", page: 3,
    text: "Stock brokers shall redress investor grievances promptly and in any case within 21 days of the receipt of the complaint from the investor." },
  // filler so word rarity behaves like a real collection
  ...Array.from({ length: 12 }, (_, i) => ({ id: `RBI_Other_p${i}_c0`, regulator: "RBI", title: "Other", page: i,
    text: "The bank shall maintain records, the policy shall be approved by the board and reviewed annually by the bank, and the current account rate shall be disclosed." })),
];
const s = new Searcher(CHUNKS);

describe("search", () => {
  it("tokenizes like the Python pipeline", () => {
    expect(tokenize("Small PPIs (Rs.10,000)")).toEqual(["small", "ppis", "rs", "10", "000"]);
  });
  it("finds the right chunk by keywords", () => {
    expect(s.search("maximum amount loaded in a PPI in a month", 1)[0].page).toBe(11);
    expect(s.search("KYC updation high-risk customers", 1)[0].page).toBe(41);
  });
  it("filters by regulator", () => {
    expect(s.search("grievances within days", 5, "RBI").every((c) => c.regulator === "RBI")).toBe(true);
  });
  it("relevance is high for real questions and low for off-topic ones", () => {
    expect(coverage("How often must KYC be updated for high-risk customers?", CHUNKS[0].text, s.bm)).toBeGreaterThan(0.5);
    expect(s.relevance("What is the current repo rate?", s.search("What is the current repo rate?"))).toBeLessThan(0.5);
    expect(s.relevance("Who won the IPL final in 2024?", s.search("Who won the IPL final in 2024?"))).toBeLessThan(0.5);
  });
  it("splits into sensible sentences", () => {
    expect(splitSentences("Short. " + CHUNKS[0].text).every((x) => x.split(" ").length >= 8)).toBe(true);
  });
  it("extractive answer quotes the rule with its source number", () => {
    const found = s.search("How often must KYC be updated for high-risk customers?");
    const out = extractive("How often must KYC be updated for high-risk customers?", found, s.bm)!;
    expect(out).toContain("two years");
    expect(out).toMatch(/\[1\]/);
  });
});

describe("prompt helpers", () => {
  const src = numbered(CHUNKS.slice(0, 2));
  it("numbers sources with title and page", () => {
    expect(buildContext(src)).toMatch(/^\[1\] KYC Master Direction, page 41/);
  });
  it("turns [n] into citations and ignores numbers out of range", () => {
    expect(citations("A [2]. B [1]. C [7].", src).map((c) => c.page)).toEqual([41, 11]);
  });
  it("validates questions", () => {
    expect(validateQuestion("  ").ok).toBe(false);
    expect(validateQuestion("x".repeat(301)).ok).toBe(false);
    expect(validateQuestion(" ok? ")).toEqual({ ok: true, question: "ok?" });
  });
});

describe("answer without an AI key", () => {
  it("answers from exact sentences", async () => {
    const r = await answer("What amount can be loaded in PPIs during any month?", s, null);
    expect(r.engine).toMatch(/Extractive/);
    expect(r.answer).toContain("Rs.10,000");
    expect(r.citations[0].page).toBe(11);
  });
  it("refuses off-topic questions", async () => {
    const r = await answer("What is the current repo rate?", s, null);
    expect(r.refused).toBe(true);
    expect(r.answer).toBe(REFUSAL);
  });
});

function fake(turns: { stop_reason: string; content: Record<string, unknown>[] }[]): LLM & { calls: Record<string, unknown>[] } {
  const calls: Record<string, unknown>[] = [];
  return { calls, messages: { create: async (p: Record<string, unknown>) => { calls.push(p); return turns.shift() as never; } } };
}

describe("answer with Claude", () => {
  it("uses Claude and maps its citations", async () => {
    const client = fake([{ stop_reason: "end_turn", content: [{ type: "text", text: "Every two years [1]." }] }]);
    const r = await answer("How often must KYC be updated for high-risk customers?", s, client);
    expect(r.engine).toMatch(/Claude/);
    expect(r.citations[0].title).toBe("KYC Master Direction");
  });
  it("falls back to extractive if Claude fails", async () => {
    const client: LLM = { messages: { create: async () => { throw new Error("no credit"); } } };
    const r = await answer("How often must KYC be updated for high-risk customers?", s, client);
    expect(r.engine).toMatch(/Extractive/);
  });
});

describe("agent", () => {
  it("calls a tool, then answers with numbered citations", async () => {
    const client = fake([
      { stop_reason: "tool_use", content: [{ type: "tool_use", id: "t1", name: "search_regulations", input: { query: "KYC high risk" } }] },
      { stop_reason: "end_turn", content: [{ type: "text", text: "At least once every two years [RBI_KYC_Master_Direction_p41_c0]." }] },
    ]);
    const r = await agent("How often is KYC updated for high-risk customers?", s, client, []);
    expect(r.trace?.[0].tool).toBe("search_regulations");
    expect(r.answer).toBe("At least once every two years [1].");
    expect(r.citations).toEqual([{ n: 1, id: "RBI_KYC_Master_Direction_p41_c0", title: "KYC Master Direction", page: 41 }]);
    const sent = client.calls[1].messages as { content: unknown }[];
    expect(JSON.stringify(sent[sent.length - 1].content)).toContain("tool_result");
  });
  it("stops after the step limit", async () => {
    const turn = { stop_reason: "tool_use", content: [{ type: "tool_use", id: "t", name: "list_documents", input: {} }] };
    const r = await agent("loop", s, fake([turn, turn, turn]), [], 3);
    expect(r.answer).toMatch(/Stopped after 3 steps/);
  });
  it("tools behave", () => {
    expect(runTool("read_chunk", { chunk_id: "missing" }, s, [])).toBe("No chunk with that id.");
    expect(runTool("list_documents", {}, s, [{ regulator: "RBI", title: "KYC", pages: 80 }])).toContain("KYC");
    expect(runTool("x", {}, s, [])).toMatch(/Unknown tool/);
  });
});
