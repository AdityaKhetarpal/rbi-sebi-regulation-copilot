// Headline numbers: documents, pages, passages, test score
import meta from "@/public/data/meta.json";
import report from "@/public/data/eval.json";
import type { TestReport } from "@/lib/types";

export default function Kpis() {
  const r = report as unknown as TestReport;
  const passed = r.results.filter((t) => t.right).length;
  const items = [
    { value: meta.documents, label: "RBI rulebooks" },
    { value: meta.pages.toLocaleString("en-IN"), label: "pages read" },
    { value: meta.chunks.toLocaleString("en-IN"), label: "passages indexed" },
    { value: r.results.length ? `${passed}/${r.results.length}` : "–", label: "test questions passed" },
  ];
  return (
    <dl className="kpis">
      {items.map((k) => (
        <div className="kpi" key={k.label}><dt>{k.label}</dt><dd>{k.value}</dd></div>
      ))}
    </dl>
  );
}
