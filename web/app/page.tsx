// Ask: the main page
import AskPanel from "@/components/AskPanel";
import Kpis from "@/components/Kpis";
import PipelineStrip from "@/components/PipelineStrip";
import meta from "@/public/data/meta.json";

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="wrap">
          <p className="eyebrow-chip">RAG · embeddings · re-ranking · AI agent</p>
          <h1>Ask India&apos;s banking rulebooks a question.</h1>
          <p className="lead">
            RBI and SEBI write the rules banks and fintechs must follow, in PDFs hundreds of pages long. Ask in plain English
            and get the answer <strong>from the official text, with the page number</strong>. If the rulebooks don&apos;t cover it,
            it says so instead of guessing. <a href="/how-it-works">See how it works →</a>
          </p>
          <Kpis />
          <PipelineStrip />
        </div>
      </section>
      <div className="wrap">
        {meta.chunks === 0 && <p className="notice">The document index is being built. Questions will work once the first build finishes.</p>}
        <AskPanel />
      </div>
    </>
  );
}
