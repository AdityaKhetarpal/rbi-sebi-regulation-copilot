"use client"; // typing, sending and showing answers happen in the browser

import { useEffect, useState } from "react";
import AnswerText from "@/components/AnswerText";
import PassageMap from "@/components/PassageMap";
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
      const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: text, mode }) });
      const data = await res.json();
      setTurns((t) => [{ ...data, question: text, mode }, ...t]);
    } catch {
      setTurns((t) => [{ question: text, mode, error: "Couldn't reach the site. Try again.", answer: "", engine: "", refused: false, citations: [], sources: [] }, ...t]);
    } finally {
      setBusy(false);
    }
  }

  const latest = turns[0];
  const found = latest && !latest.refused ? latest.sources.map((s) => s.id) : [];

  return (
    <div className="ask">
      <form className="ask-box" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <label className="sr-only" htmlFor="q">Your question</label>
        <span className="prompt" aria-hidden="true">›</span>
        <textarea id="q" rows={2} maxLength={300} value={question} placeholder="Ask about KYC, prepaid wallets, fraud reporting, payment aggregators…"
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(question); } }} />
        <div className="ask-controls">
          <div className="segmented" role="group" aria-label="Mode">
            <button type="button" aria-pressed={mode === "answer"} onClick={() => setMode("answer")} title="Search once, answer once (RAG)">Answer</button>
            <button type="button" aria-pressed={mode === "agent"} onClick={() => setMode("agent")}
              title={status?.ai ? "The AI plans and searches in several steps" : "Needs the AI key on this deployment"}>Agent</button>
          </div>
          <span className="status-line">
            {status ? (status.ai ? "Claude writes the answers" : "Quote mode · answers are the rulebook's own words") : ""}
          </span>
          <button className="btn-primary" type="submit" disabled={busy || !question.trim()}>{busy ? "Searching…" : "Ask →"}</button>
        </div>
      </form>

      <div className="examples" aria-label="Example questions">
        <span className="examples-label">Try:</span>
        {EXAMPLES.map((e) => <button key={e} type="button" className="chip" onClick={() => ask(e)} disabled={busy}>{e}</button>)}
      </div>

      {turns.map((t, i) => (
        <article className={`result ${i === 0 ? "result-latest" : ""}`} key={turns.length - i} aria-live={i === 0 ? "polite" : undefined}>
          <p className="result-q">{t.question}</p>
          {t.error ? <p className="error">{t.error}</p> : (
            <>
              <div className="result-meta">
                <span className={`tag ${t.refused ? "tag-refused" : "tag-ok"}`}>{t.refused ? "✕ not in the documents" : "✓ answered from the rulebook"}</span>
                {!t.refused && <span className="tag">{t.engine}</span>}
                {t.note && <span className="muted">{t.note}</span>}
              </div>
              <AnswerText text={t.answer} />

              {t.trace && t.trace.length > 0 && (
                <ol className="trace" aria-label="Agent steps">
                  {t.trace.map((s, j) => <li key={j}><code>{s.tool}</code> {Object.values(s.input).map(String).join(" · ")}</li>)}
                </ol>
              )}

              {t.sources.length > 0 && (
                <div className="sources">
                  <p className="sources-head">{t.refused ? "Closest passages (not a real match)" : "Passages it used · match score"}</p>
                  {t.sources.map((s) => (
                    <details key={s.id} id={i === 0 ? `src-${s.n}` : undefined}>
                      <summary>
                        <span className="src-n">{s.n}</span>
                        <span className="src-title">{s.title} <span className="muted">p.{s.page}</span></span>
                        {s.match !== undefined && !t.refused && (
                          <span className="match" title={`Match ${Math.round(s.match * 100)}% of the best passage`}>
                            <span className="match-bar"><span style={{ width: `${Math.max(4, s.match * 100)}%` }} /></span>
                            <span className="match-num">{Math.round(s.match * 100)}</span>
                          </span>
                        )}
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

      <section className="panel map-panel">
        <div className="panel-head">
          <h2>Map of everything it has read</h2>
          <p className="muted">{found.length ? "The orange dots are the passages used for your last question." : "Ask a question to see which passages light up."}</p>
        </div>
        <PassageMap highlight={found} />
      </section>
    </div>
  );
}
