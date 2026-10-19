// Documents: what the copilot has read
import type { Metadata } from "next";
import documents from "@/public/data/documents.json";
import meta from "@/public/data/meta.json";
import type { Doc } from "@/lib/types";

export const metadata: Metadata = { title: "Documents · Regulation Copilot" };

export default function DocumentsPage() {
  const docs = documents as Doc[];
  return (
    <>
      <p className="eyebrow">Documents</p>
      <h1>What the copilot has read.</h1>
      <p className="lead">
        {docs.length} documents, {meta.pages.toLocaleString("en-IN")} pages, cut into {meta.chunks.toLocaleString("en-IN")} passages of about{" "}
        {meta.chunk_words} words. RBI Master Directions are downloaded from rbi.org.in automatically every Monday{meta.built_on ? `; last built ${meta.built_on}` : ""}.
      </p>
      <div className="panel table-wrap" style={{ marginTop: 28, padding: 8 }}>
        <table>
          <thead><tr><th>Regulator</th><th>Document</th><th className="num">Pages</th><th className="num">Passages</th><th>Source</th></tr></thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.file}>
                <td><span className={`reg reg-${d.regulator.toLowerCase()}`}>{d.regulator}</span></td>
                <td>{d.title}{d.official_title && <div className="muted">{d.official_title}</div>}
                  {d.empty_pages > d.pages / 4 && <div className="warn-text">{d.empty_pages} pages look scanned and can&apos;t be searched</div>}</td>
                <td className="num">{d.pages}</td>
                <td className="num">{d.chunks ?? "–"}</td>
                <td>{d.url ? <a href={d.url} target="_blank" rel="noreferrer">PDF</a> : <span className="muted">added by hand</span>}</td>
              </tr>
            ))}
            {docs.length === 0 && <tr><td colSpan={5} className="muted">The index hasn&apos;t been built yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
