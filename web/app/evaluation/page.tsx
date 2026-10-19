// Evaluation: how well the full pipeline does on questions with known answers
import type { Metadata } from "next";
import report from "@/public/data/eval.json";

export const metadata: Metadata = { title: "Evaluation · Regulation Copilot" };

type Row = { id: string; kind: string; question: string; engine: string; retrieval_hit: boolean | null; answer_correct: boolean; answer: string };
type Summary = { questions: number; retrieval_hit_rate_pct: number | null; answer_accuracy_pct: number | null; refusal_accuracy_pct: number | null; overall_pct: number | null };

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${v}%`);

export default function EvaluationPage() {
  const s = report.summary as Summary | null;
  const rows = report.results as Row[];
  return (
    <>
      <p className="eyebrow">Evaluation</p>
      <h1>Measured, not assumed.</h1>
      <p className="lead">
        A fixed set of questions with known answers from the documents, plus questions it must refuse. Scored automatically
        every time the index is rebuilt{report.run_on ? ` (last run ${report.run_on})` : ""}.
      </p>
      {!s ? <p className="notice">The first evaluation runs right after the first index build.</p> : (
        <>
          <div className="stats">
            <div className="stat"><p className="stat-label">Right passage found (top 5)</p><p className="stat-value">{pct(s.retrieval_hit_rate_pct)}</p><p className="stat-note">retrieval</p></div>
            <div className="stat"><p className="stat-label">Answer contains the right fact</p><p className="stat-value">{pct(s.answer_accuracy_pct)}</p><p className="stat-note">generation</p></div>
            <div className="stat"><p className="stat-label">Off-topic questions refused</p><p className="stat-value">{pct(s.refusal_accuracy_pct)}</p><p className="stat-note">no made-up answers</p></div>
          </div>
          <p className="note">Pipeline: {report.pipeline}. {s.questions} questions.</p>
          <div className="panel table-wrap" style={{ marginTop: 20, padding: 8 }}>
            <table>
              <thead><tr><th>Question</th><th>Type</th><th>Retrieval</th><th>Result</th><th>Answer given</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.question}</td>
                    <td className="muted">{r.kind === "refuse" ? "must refuse" : "fact"}</td>
                    <td>{r.retrieval_hit === null ? "–" : r.retrieval_hit ? "✓ found" : "✗ missed"}</td>
                    <td><span className={r.answer_correct ? "pass" : "fail"}>{r.answer_correct ? "Pass" : "Fail"}</span></td>
                    <td className="muted answer-cell">{r.answer.slice(0, 220)}{r.answer.length > 220 ? "…" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
