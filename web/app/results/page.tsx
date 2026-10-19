// Results: what the copilot has read (steps 1-3) and how it scored on the test questions (step 7)
import type { Metadata } from "next";
import documents from "@/public/data/documents.json";
import meta from "@/public/data/meta.json";
import report from "@/public/data/eval.json";
import type { Doc, TestReport } from "@/lib/types";
import Kpis from "@/components/Kpis";
import DocBars from "@/components/DocBars";

export const metadata: Metadata = { title: "Results · Regulation Copilot" };

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${Math.round(v)}%`);

export default function ResultsPage() {
  const docs = documents as Doc[];
  const r = report as unknown as TestReport;
  return (
    <>
      <section className="hero hero-small"><div className="wrap">
        <p className="eyebrow-chip">Results</p>
        <h1>What it has read, and how well it answers.</h1>
        <Kpis />
      </div></section>

      <div className="wrap">
      <section className="section" style={{ marginTop: 40 }}>
        <h2>The documents</h2>
        <p className="body">
          {docs.length} RBI rulebooks, {meta.pages.toLocaleString("en-IN")} pages, cut into {meta.chunks.toLocaleString("en-IN")} passages.
          Downloaded fresh from rbi.org.in every Monday{meta.built_on ? `; last built ${meta.built_on}` : ""}.
        </p>
        <div className="panel" style={{ marginTop: 14 }}><DocBars docs={docs} /></div>
        <div className="panel table-wrap" style={{ marginTop: 12, padding: 8 }}>
          <table>
            <thead><tr><th>Document</th><th className="num">Pages</th><th className="num">Passages</th><th>Official PDF</th></tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.file}>
                  <td><span className={`reg reg-${d.regulator.toLowerCase()}`}>{d.regulator}</span> {d.title}
                    {d.official_title && <div className="muted">{d.official_title}</div>}</td>
                  <td className="num">{d.pages}</td>
                  <td className="num">{d.chunks}</td>
                  <td>{d.url ? <a href={d.url} target="_blank" rel="noreferrer">Open</a> : <span className="muted">added by hand</span>}</td>
                </tr>
              ))}
              {docs.length === 0 && <tr><td colSpan={4} className="muted">Not built yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section">
        <h2>The test</h2>
        <p className="body">
          {r.summary?.questions ?? 11} questions: 8 with answers we know from the documents, and 3 off-topic ones it must refuse.
          Checked automatically every week{r.run_on ? ` (last run ${r.run_on})` : ""}; if a score drops below 90%, the new version isn&apos;t published.
        </p>
        {r.summary && (
          <div className="stats">
            <div className="stat"><p className="stat-label">Found the right passage</p><p className="stat-value">{pct(r.summary.found_pct)}</p><p className="stat-note">of the 8 known-answer questions</p></div>
            <div className="stat"><p className="stat-label">Answer has the right fact</p><p className="stat-value">{pct(r.summary.right_pct)}</p><p className="stat-note">e.g. &ldquo;two years&rdquo;, &ldquo;Rs.10,000&rdquo;</p></div>
            <div className="stat"><p className="stat-label">Refused off-topic questions</p><p className="stat-value">{pct(r.summary.refused_pct)}</p><p className="stat-note">no made-up answers</p></div>
          </div>
        )}
        <div className="panel table-wrap" style={{ marginTop: 16, padding: 8 }}>
          <table>
            <thead><tr><th>Question</th><th>Result</th><th>Answer given</th></tr></thead>
            <tbody>
              {r.results.map((t) => (
                <tr key={t.id}>
                  <td>{t.question}<div className="muted">{t.kind === "refuse" ? "must refuse" : "known answer"}</div></td>
                  <td><span className={`tag ${t.right ? "tag-ok" : "tag-refused"}`}>{t.right ? "✓ pass" : "✕ fail"}</span></td>
                  <td className="muted answer-cell">{t.answer.slice(0, 200)}{t.answer.length > 200 ? "…" : ""}</td>
                </tr>
              ))}
              {r.results.length === 0 && <tr><td colSpan={3} className="muted">The first test runs right after the first build.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="note">Scored on the full Python pipeline (meaning + keyword search, re-ranker, quote mode). The website&apos;s keyword search is checked on the same questions in its own tests.</p>
      </section>
      </div>
    </>
  );
}
