// Passages per document: one hue, value written at the end of each bar
import type { Doc } from "@/lib/types";

export default function DocBars({ docs }: { docs: Doc[] }) {
  const rows = [...docs].sort((a, b) => b.chunks - a.chunks);
  const max = Math.max(1, ...rows.map((d) => d.chunks));
  return (
    <div className="bars" role="list" aria-label="Passages per document">
      {rows.map((d) => (
        <div className="bar-row" role="listitem" key={d.file}>
          <span className="bar-name">{d.title}<small>{d.pages} pages</small></span>
          <span className="bar-track">
            <span className="bar" style={{ width: `${(d.chunks / max) * 82}%` }} />
            <span className="bar-value">{d.chunks}</span>
          </span>
        </div>
      ))}
    </div>
  );
}
