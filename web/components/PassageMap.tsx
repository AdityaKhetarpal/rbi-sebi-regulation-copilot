"use client"; // hover and the document buttons run in the browser

// Every passage as a dot. Positions come from the embeddings (step 4) squashed to 2D:
// passages that mean similar things sit close together. Passages found for a question light up in orange.
import { useMemo, useRef, useState } from "react";
import map from "@/public/data/map.json";

const W = 640, H = 380, PAD = 16;
type Pt = { i: number; x: number; y: number; doc: number; page: number; id: string };

export default function PassageMap({ highlight = [], caption = true }: { highlight?: string[]; caption?: boolean }) {
  const [doc, setDoc] = useState<number | null>(null);          // document picked in the legend
  const [hover, setHover] = useState<Pt | null>(null);
  const svg = useRef<SVGSVGElement>(null);

  const pts: Pt[] = useMemo(() => map.points.map((p, i) => ({
    i, x: PAD + p[0] * (W - 2 * PAD), y: PAD + (1 - p[1]) * (H - 2 * PAD), doc: p[2], page: p[3], id: map.ids[i],
  })), []);
  const rank = new Map(highlight.map((id, r) => [id, r + 1]));
  const found = pts.filter((p) => rank.has(p.id)).sort((a, b) => rank.get(b.id)! - rank.get(a.id)!); // best drawn last

  // nearest dot to the pointer (generous hit area: 14px)
  const onMove = (e: React.PointerEvent) => {
    const box = svg.current!.getBoundingClientRect();
    const x = ((e.clientX - box.left) / box.width) * W, y = ((e.clientY - box.top) / box.height) * H;
    let best: Pt | null = null, d = 14 * 14;
    for (const p of pts) { const dd = (p.x - x) ** 2 + (p.y - y) ** 2; if (dd < d) { d = dd; best = p; } }
    setHover(best);
  };

  if (!pts.length) return null;
  return (
    <figure className="viz">
      <div className="viz-legend" role="group" aria-label="Highlight a document">
        <span className="key"><i className="dot dot-muted" />Passage</span>
        {highlight.length > 0 && <span className="key"><i className="dot dot-found" />Found for the question</span>}
        <span className="key-sep" />
        {map.documents.map((name, d) => (
          <button key={name} type="button" className="doc-chip" aria-pressed={doc === d} onClick={() => setDoc(doc === d ? null : d)}>
            <i className="dot dot-doc" />{name}
          </button>
        ))}
      </div>
      <div className="viz-plot">
        <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" onPointerMove={onMove} onPointerLeave={() => setHover(null)}
          aria-label={`Map of ${pts.length} passages; similar passages sit close together${highlight.length ? `; ${found.length} found for the question are highlighted` : ""}`}>
          {pts.map((p) => (
            <circle key={p.i} cx={p.x} cy={p.y} r={doc === p.doc ? 4.5 : 3.5}
              className={doc === p.doc ? "pt pt-doc" : doc !== null ? "pt pt-faded" : "pt"} />
          ))}
          {found.map((p) => (
            <g key={p.id}>
              <circle cx={p.x} cy={p.y} r={8} className="pt-found" />
              <text x={p.x + 11} y={p.y + 4} className="pt-label">{rank.get(p.id)}</text>
            </g>
          ))}
          {hover && <circle cx={hover.x} cy={hover.y} r={9} className="pt-hover" />}
        </svg>
        {hover && (
          <div className="viz-tip" style={{ left: `${(hover.x / W) * 100}%`, top: `${(hover.y / H) * 100}%` }}>
            <strong>{map.documents[hover.doc]}</strong>
            page {hover.page}{rank.has(hover.id) ? ` · result #${rank.get(hover.id)}` : ""}
          </div>
        )}
      </div>
      {caption && (
        <figcaption>
          Each dot is one of the {pts.length} passages. Dots close together mean similar things: their positions come from
          the embeddings (step 4), squashed from 384 numbers down to 2. Hover a dot, or pick a document to highlight it.
        </figcaption>
      )}
    </figure>
  );
}
