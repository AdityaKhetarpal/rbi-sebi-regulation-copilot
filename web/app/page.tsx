// Ask: the main page
import AskPanel from "@/components/AskPanel";
import meta from "@/public/data/meta.json";

export default function Home() {
  return (
    <>
      <p className="eyebrow">RAG + AI agent over official circulars</p>
      <h1>Ask the RBI and SEBI rulebooks.</h1>
      <p className="lead">
        Every answer is built only from the regulators&apos; own documents and cites the page it came from. If the
        documents don&apos;t cover your question, it says so instead of guessing.
      </p>
      {meta.chunks === 0 && (
        <p className="notice">The document index is being built. Questions will work once the first build finishes.</p>
      )}
      <AskPanel />
    </>
  );
}
