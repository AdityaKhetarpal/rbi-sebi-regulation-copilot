// How it works: the pipeline, the design decisions, and the limits
import type { Metadata } from "next";
import meta from "@/public/data/meta.json";

export const metadata: Metadata = { title: "How it works · Regulation Copilot" };

const STEPS: [string, string][] = [
  ["Ingest", "A weekly GitHub workflow downloads the current RBI Master Directions from rbi.org.in. SEBI master circulars are added by hand."],
  ["Chunk", "Each page is cleaned and cut into ~300-word passages that overlap by 50 words, keeping document and page for citations."],
  ["Embed", "Each passage becomes 384 numbers (bge-small) so the search can match meaning, not just words."],
  ["Retrieve", "Meaning search + keyword search (BM25), merged with Reciprocal Rank Fusion, then a cross-encoder re-ranks the top 20."],
  ["Answer", "The best 5 passages go to the writer with strict rules: only these sources, cite [n], quote numbers exactly, refuse if missing."],
  ["Agent", "For multi-part questions, Claude plans and calls tools (search, read a passage, list documents) in a loop before answering."],
];

export default function HowPage() {
  return (
    <>
      <p className="eyebrow">How it works</p>
      <h1>From PDF to cited answer.</h1>
      <p className="lead">Retrieval-augmented generation (RAG): look up the rules first, then write only from what was found.</p>

      <section className="section">
        <ol className="steps">{STEPS.map(([t, d]) => <li className="step" key={t}><h3>{t}</h3><p>{d}</p></li>)}</ol>
      </section>

      <section className="section grid-2">
        <div className="panel">
          <h3>Never depends on a paid key</h3>
          <p className="body">The writer is whichever engine is available, best first:</p>
          <ol className="list">
            <li><strong>Claude</strong> ({"claude-haiku-5-5"}) when an API key is set.</li>
            <li><strong>A free open-source model</strong> (Qwen2.5-1.5B) on a GPU, in the notebook.</li>
            <li><strong>Extractive</strong>: the best sentences from the regulation, word for word, with citations. Always works.</li>
          </ol>
        </div>
        <div className="panel">
          <h3>Saying &ldquo;I don&apos;t know&rdquo;</h3>
          <p className="body">
            Before writing anything, the system checks how relevant the best passage is. Below a threshold, it refuses
            instead of guessing. The threshold was set from data: real questions scored above 4 on the re-ranker, an off-topic
            question (&ldquo;current repo rate&rdquo;) scored −10.
          </p>
        </div>
      </section>

      <section className="section grid-2">
        <div className="panel">
          <h3>Two versions of the same pipeline</h3>
          <p className="body">
            <strong>Python (notebook and scripts)</strong>: full hybrid search with embeddings and the re-ranker. This is what the Evaluation page measures.
          </p>
          <p className="body" style={{ marginTop: 10 }}>
            <strong>This website</strong>: the same passages with keyword search (BM25) and a word-rarity relevance check, so it
            runs instantly on a free server without loading models.
          </p>
        </div>
        <div className="panel">
          <h3>Limitations</h3>
          <ul className="list">
            <li>Covers only the documents listed on the Documents page ({meta.documents} so far).</li>
            <li>Scanned PDFs can&apos;t be searched; the Documents page flags them.</li>
            <li>Amendments issued after a Direction&apos;s last update may not be reflected until RBI updates the Direction.</li>
            <li>Information, not legal advice. Always confirm against the original circular.</li>
          </ul>
        </div>
      </section>

      <section className="section">
        <h2>Code</h2>
        <ul className="list">
          <li><a href="https://github.com/AdityaKhetarpal/rbi-sebi-regulation-copilot/blob/main/notebooks/regcopilot.ipynb" target="_blank" rel="noreferrer">Step-by-step notebook</a>: every part, explained, runs in Google Colab.</li>
          <li><a href="https://github.com/AdityaKhetarpal/rbi-sebi-regulation-copilot/tree/main/copilot" target="_blank" rel="noreferrer">Python package</a>: ingest, chunking, retrieval, the three engines, the agent, evaluation.</li>
          <li><a href="https://github.com/AdityaKhetarpal/rbi-sebi-regulation-copilot/tree/main/.github/workflows" target="_blank" rel="noreferrer">Workflows</a>: tests on every push, weekly re-download and re-index.</li>
        </ul>
      </section>
    </>
  );
}
