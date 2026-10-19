// Ask: the main page
import AskPanel from "@/components/AskPanel";
import meta from "@/public/data/meta.json";

export default function Home() {
  return (
    <>
      <p className="eyebrow">RAG + AI agent over official circulars</p>
      <h1>Ask the RBI and SEBI rulebooks.</h1>
      <p className="lead">
        RBI and SEBI are India&apos;s financial regulators, and their rules sit in long PDFs. Ask a question in plain English:
        the answer comes only from those official documents, with the page it came from. If they don&apos;t cover it, it says so.{" "}
        <a href="/how-it-works">How it works →</a>
      </p>
      {meta.chunks === 0 && (
        <p className="notice">The document index is being built. Questions will work once the first build finishes.</p>
      )}
      <AskPanel />
    </>
  );
}
