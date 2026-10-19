// The 8 steps as a strip of chips, grouped by when they run
const GROUPS: { label: string; steps: [number, string][] }[] = [
  { label: "Prepare · weekly", steps: [[1, "Download"], [2, "Read pages"], [3, "Chunk"], [4, "Embed"]] },
  { label: "Answer · every question", steps: [[5, "Search"], [6, "Answer + cite"]] },
  { label: "Check", steps: [[7, "Test"], [8, "Agent"]] },
];

export default function PipelineStrip() {
  return (
    <div className="strip" aria-label="The 8 steps">
      {GROUPS.map((g) => (
        <div className="strip-group" key={g.label}>
          <p className="strip-label">{g.label}</p>
          <ol>
            {g.steps.map(([n, name]) => <li key={n}><span>{String(n).padStart(2, "0")}</span>{name}</li>)}
          </ol>
        </div>
      ))}
    </div>
  );
}
