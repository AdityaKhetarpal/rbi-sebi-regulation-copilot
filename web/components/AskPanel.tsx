"use client"; // typing, sending and showing answers happen in the browser

import { useEffect, useState } from "react";
import AnswerText from "@/components/AnswerText";
import type { AskResult } from "@/lib/types";

const EXAMPLES = [
  "How often must KYC be updated for high-risk customers?",
  "What is the maximum amount that can be loaded in a small PPI in a month?",
  "Within how many days must a bank report theft or robbery to RBI?",
  "What is the current repo rate?",
];
type Mode = "answer" | "agent";
type Turn = AskResult & { error?: string; mode: Mode };

export default function AskPanel() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("answer");
  const [status, setStatus] = useState<{ ai: boolean; chunks: number } | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/ask").then((r) => r.json()).then(setStatus).catch(() => setStatus({ ai: false, chunks: 0 }));
  }, []);

  async function ask(q: string) {
    const text = q.trim();
    if (!text || busy) return;
    setBusy(true);
    setQuestion("");
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, mode }),
      });
      const data = await res.json();
      setTurns((t) => [{ ...data, question: text, mode }, ...t]);
    } catch {
      setTurns((t) => [{ question: text, mode, error: "Couldn't reach the site. Try again.", answer: "", engine: "", refused: false, citations: [], sources: [] }, ...t]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ask">
      <form className="ask-box" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <label className="sr-only" htmlFor="q">Your question</label>
        <textarea id="q" rows={2} maxLength={300} value={question} placeholder="Ask about KYC, prepaid wallets, fraud reporting, payment aggregators…"
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(question); } }} />
        <div className="ask-controls">
          <div className="segmented" role="group" aria-label="Mode">
            <button type="button" aria-pressed={mode === "answer"} onClick={() => setMode("answer")} title="Search once, answer once (RAG)">Answer</button>
            <button type="button" aria-pressed={mode === "agent"} onClick={() => setMode("agent")}
              title={status?.ai ? "Claude plans and searches in several steps" : "Needs the AI key on this deployment"}>Agent</button>
          </div>
          <button className="btn-primary" type="submit" disabled={busy || !question.trim()}>{busy ? "Searching…" : "Ask"}</button>
        </div>
      </form>

      <div className="examples" aria-label="Example questions">
        {EXAMPLES.map((e) => <button key={e} type="button" className="chip" onClick={() => ask(e)} disabled={busy}>{e}</button>)}
      </div>

      {status && (
        <p className="status-line">
          {status.chunks.toLocaleString("en-IN")} passages indexed ·{" "}
          {status.ai ? "Answers written by Claude · Agent mode available" : "Quote mode: answers are the regulation's own sentences, word for word (no AI key on this site)"}
        </p>
      )}

      {turns.map((t, i) => (
        <article className="result" key={turns.length - i} aria-live={i === 0 ? "polite" : undefined}>
          <p className="result-q">{t.question}</p>
          {t.error ? <p className="error">{t.error}</p> : (
            <>
              <div className="result-meta">
                <span className={`engine ${t.refused ? "engine-refused" : ""}`}>{t.refused ? "Not in the documents" : t.engine}</span>
                {t.note && <span className="note-inline">{t.note}</span>}
              </div>
              <AnswerText text={t.answer} />

              {t.trace && t.trace.length > 0 && (
                <ol className="trace" aria-label="Agent steps">
                  {t.trace.map((s, j) => (
                    <li key={j}><code>{s.tool}</code> {Object.values(s.input).map(String).join(" · ")}</li>
                  ))}
                </ol>
              )}

              {t.sources.length > 0 && (
                <div className="sources">
                  <p className="sources-head">{t.refused ? "Closest passages found (not a match)" : "Sources"}</p>
                  {t.sources.map((s) => (
                    <details key={s.id} id={i === 0 ? `src-${s.n}` : undefined} open={!t.refused && t.citations.some((c) => c.n === s.n) && i === 0}>
                      <summary>
                        <span className="src-n">{s.n}</span>
                        <span className={`reg reg-${s.regulator.toLowerCase()}`}>{s.regulator}</span>
                        <span className="src-title">{s.title}</span>
                        <span className="src-page">p.{s.page}</span>
                      </summary>
                      <p className="src-text">{s.text}</p>
                    </details>
                  ))}
                </div>
              )}
            </>
          )}
        </article>
      ))}
    </div>
  );
}
