// Shows an answer with its [1] [2] markers turned into small citation chips
export default function AnswerText({ text }: { text: string }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p className="answer-text">
      {parts.map((p, i) => {
        const m = p.match(/^\[(\d+)\]$/);
        return m ? <a key={i} className="cite" href={`#src-${m[1]}`} aria-label={`Source ${m[1]}`}>{m[1]}</a> : <span key={i}>{p}</span>;
      })}
    </p>
  );
}
