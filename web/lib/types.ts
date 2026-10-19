// Shapes of the JSON files in public/data (written by scripts/build_index.py and scripts/run_eval.py)

export type Chunk = { id: string; regulator: string; title: string; page: number; text: string };

export type Doc = {
  file: string; regulator: string; title: string; official_title: string; url: string;
  pages: number; empty_pages: number; chunks: number;
};

export type TestRow = { id: string; kind: "fact" | "refuse"; question: string; method: string; answer: string; found: boolean | null; right: boolean };
export type TestReport = { summary: { questions: number; found_pct: number | null; right_pct: number | null; refused_pct: number | null } | null; results: TestRow[]; run_on: string | null };

export type Source = Chunk & { n: number };
export type Citation = { n: number; id: string; title: string; page: number };
export type Step = { step: number; tool: string; input: Record<string, unknown>; preview: string };

export type AskResult = {
  question: string;
  answer: string;
  engine: string;
  refused: boolean;
  citations: Citation[];
  sources: Source[];
  trace?: Step[];
  note?: string;
};
