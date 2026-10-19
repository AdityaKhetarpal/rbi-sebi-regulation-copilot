// Shapes of the JSON files in public/data (written by scripts/build_index.py and scripts/run_eval.py)

export type Chunk = { id: string; regulator: string; title: string; page: number; text: string };

export type Doc = {
  file: string; regulator: string; title: string; official_title: string; url: string;
  pages: number; words: number; empty_pages: number; chunks?: number;
};

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
