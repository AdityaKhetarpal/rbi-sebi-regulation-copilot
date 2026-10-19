// How it works: follow ONE real question through the 8 steps, using the real data (worked out when the site is built)
import type { Metadata } from "next";
import { Searcher } from "@/lib/search";
import { answer } from "@/lib/answer";
import AnswerText from "@/components/AnswerText";
import chunks from "@/public/data/chunks.json";
import documents from "@/public/data/documents.json";
import meta from "@/public/data/meta.json";
import report from "@/public/data/eval.json";
import type { Chunk, Doc, TestReport } from "@/lib/types";

export const metadata: Metadata = { title: "How it works · Regulation Copilot" };

const QUESTION = "How often must KYC be updated for high-risk customers?";
const OFF_TOPIC = "What is the current repo rate?";
const CODE = "https://github.com/AdityaKhetarpal/rbi-sebi-regulation-copilot/blob/main/pipeline/";

function Step({ n, title, file, children }: { n: number; title: string; file?: string; children: React.ReactNode }) {
  return (
    <li className="walk-step">
      <div className="walk-n" aria-hidden="true">{n}</div>
      <div className="walk-body">
        <h3>{title}</h3>
        {children}
        {file && <p className="walk-file">Code: <a href={CODE + file} target="_blank" rel="noreferrer">pipeline/{file}</a></p>}
      </div>
    </li>
  );
}

export default async function HowPage() {
  const all = chunks as Chunk[];
  const docs = documents as Doc[];
  const r = report as unknown as TestReport;
  const s = all.length ? new Searcher(all) : null;
  const found = s ? s.search(QUESTION, 3) : [];
  const result = s ? await answer(QUESTION, s, null) : null;
  const refused = s ? await answer(OFF_TOPIC, s, null) : null;
  const example = found[0];

  return (
    <>
      <p className="eyebrow">How it works</p>
      <h1>Follow one question through the system.</h1>
      <p className="lead">
        The idea is called <strong>RAG</strong> (retrieval-augmented generation): look the rule up in the official
        documents first, then answer only from what was found, like an open-book exam. Here is the real path of one
        question: <em>&ldquo;{QUESTION}&rdquo;</em>
      </p>

      <div className="split">
        <p><strong>Steps 1–4</strong> prepare the library once a week.</p>
        <p><strong>Steps 5–6</strong> run every time someone asks.</p>
        <p><strong>Steps 7–8</strong> check quality and handle harder questions.</p>
      </div>

      <ol className="walk">
        <Step n={1} title="Download the rulebooks" file="step1_download.py">
          <p>RBI publishes its rules as long PDFs called Master Directions. A script reads RBI&apos;s list page and downloads the ones we want.</p>
          <p className="walk-data">{docs.length} documents downloaded: {docs.map((d) => d.title).join(", ") || "not built yet"}.</p>
        </Step>

        <Step n={2} title="Read every page" file="step2_read_pdfs.py">
          <p>The text is pulled out of each PDF into a table, one row per page, keeping the page number so answers can cite it.</p>
          <p className="walk-data">{meta.pages.toLocaleString("en-IN")} pages of text.</p>
        </Step>

        <Step n={3} title="Cut pages into small passages" file="step3_chunk.py">
          <p>A 100-page rulebook is too much to read for every question, so each page is cut into passages of about {meta.chunk_words} words. Neighbouring passages overlap a little, so no rule gets cut in half.</p>
          <p className="walk-data">{meta.chunks.toLocaleString("en-IN")} passages. For example, <code>{example?.id ?? "RBI_KYC_Master_Direction_p41_c0"}</code>:</p>
          {example && <blockquote className="walk-quote">{example.text.slice(0, 320)}…</blockquote>}
        </Step>

        <Step n={4} title="Turn passages into numbers" file="step4_embed.py">
          <p>A free AI model turns each passage into 384 numbers that capture its meaning. Passages that mean the same thing get similar numbers, even with different words. That lets &ldquo;how often must KYC be updated&rdquo; match &ldquo;periodic updation of KYC shall be carried out…&rdquo;.</p>
        </Step>

        <Step n={5} title="Search for the best passages" file="step5_search.py">
          <p>The question is compared with every passage. The Python version combines meaning search, keyword search and a re-ranker; this website uses fast keyword search. The top results for our question:</p>
          <ol className="walk-found">
            {found.map((c) => <li key={c.id}><strong>{c.title}</strong>, page {c.page}<span className="muted"> · {c.text.slice(0, 110)}…</span></li>)}
          </ol>
        </Step>

        <Step n={6} title="Answer only from those passages" file="step6_answer.py">
          <p>The best passages are numbered [1], [2]… and the answer is built only from them, with each fact citing its passage. With an AI key, Claude writes it; without one, the system quotes the best sentences word for word.</p>
          {result && <div className="walk-answer"><AnswerText text={result.answer} />
            <p className="muted">{result.citations.map((c) => `[${c.n}] ${c.title}, page ${c.page}`).join(" · ")}</p></div>}
          <p>Before answering, it checks the passages actually match the question. Asked <em>&ldquo;{OFF_TOPIC}&rdquo;</em> (not in these rulebooks), it says:</p>
          {refused && <div className="walk-answer"><p>{refused.answer}</p></div>}
        </Step>

        <Step n={7} title="Test it on questions with known answers" file="step7_test.py">
          <p>11 test questions run automatically every week: 8 whose answers we know, and 3 it must refuse. If any score drops below 90%, for example because RBI changed its website and a wrong PDF was downloaded, the new version isn&apos;t published.</p>
          {r.summary && <p className="walk-data">Latest: right passage found {Math.round(r.summary.found_pct ?? 0)}%, right fact in the answer {Math.round(r.summary.right_pct ?? 0)}%, off-topic refused {Math.round(r.summary.refused_pct ?? 0)}%. <a href="/results">See every question →</a></p>}
        </Step>

        <Step n={8} title="The agent, for harder questions" file="step8_agent.py">
          <p>Step 6 searches once. For a question like &ldquo;compare KYC rules for high, medium and low risk customers&rdquo;, the <strong>agent</strong> lets the AI decide what to look up: it searches, reads, searches again, then answers. Try it with the <em>Agent</em> button on the Ask page (needs the AI key).</p>
        </Step>
      </ol>

      <section className="section grid-2">
        <div className="panel">
          <h3>Words you&apos;ll hear</h3>
          <ul className="list">
            <li><strong>Chunk</strong>: a small passage of a document (step 3).</li>
            <li><strong>Embedding</strong>: numbers that capture a passage&apos;s meaning (step 4).</li>
            <li><strong>Retrieval</strong>: finding the best passages for a question (step 5).</li>
            <li><strong>RAG</strong>: retrieve first, then generate the answer from what was found (steps 5–6).</li>
            <li><strong>Agent</strong>: an AI that uses tools in a loop and decides its next step (step 8).</li>
          </ul>
        </div>
        <div className="panel">
          <h3>Limits</h3>
          <ul className="list">
            <li>It only knows the documents on the Results page.</li>
            <li>Scanned PDFs can&apos;t be read.</li>
            <li>Information, not legal advice. Check the original circular.</li>
          </ul>
          <p className="body" style={{ marginTop: 12 }}>
            Build it yourself, step by step: <a href="https://github.com/AdityaKhetarpal/rbi-sebi-regulation-copilot/blob/main/notebooks/regcopilot.ipynb" target="_blank" rel="noreferrer">the notebook</a>.
          </p>
        </div>
      </section>
    </>
  );
}
