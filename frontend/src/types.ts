export type Mode = "none" | "conservative" | "aggressive";
export type Config = {
  query_normalization: Mode;
  corpus_normalization: Mode;
  k: number;
  k1: number;
  b: number;
};
export type Metric = "recall" | "precision" | "mrr" | "ndcg";
export type Metrics = Record<Metric, number | null>;
export type DatasetSummary = {
  id: string;
  hash: string;
  name: string;
  language: string;
  description: string;
  source: string;
  document_count: number;
  query_count: number;
};
export type Doc = {
  id: string;
  title: string;
  text: string;
  metadata: Record<string, unknown>;
};
export type Query = {
  id: string;
  question: string;
  expected_answer: string;
  qrels: Record<string, number>;
  metadata: Record<string, unknown>;
};
export type DatasetDetail = {
  id: string;
  hash: string;
  data: {
    name: string;
    source: string;
    description: string;
    documents: Doc[];
    queries: Query[];
  };
};
export type Ranking = { doc_id: string; score: number; rank: number };
export type Row = Query & {
  query_id: string;
  normalized_question: string;
  ranking: Ranking[];
  metrics: Metrics | null;
  hypotheses: string[];
};
export type Experiment = {
  id: string;
  name: string;
  dataset_id: string;
  config: Config;
  created_at: string;
  duration_ms: number;
  metrics: Metrics;
  scored_queries: number;
  excluded_queries: number;
  engine_version: string;
};
export type Status = "regressed" | "improved" | "unchanged" | "excluded";
export type ComparisonRow = {
  query_id: string;
  question: string;
  baseline: Row;
  candidate: Row;
  deltas: Metrics | null;
  status: Status;
};
export type Comparison = {
  baseline: Experiment;
  candidate: Experiment;
  rows: ComparisonRow[];
  counts: Record<Status, number>;
  summary: Record<
    Metric,
    {
      baseline: number | null;
      candidate: number | null;
      delta: number | null;
      bootstrap: {
        interval: [number, number] | null;
        n: number;
        caution: string;
      };
    }
  >;
};
export type Judgment = {
  engine?: "rubric" | "ragas";
  ragas_version?: string;
  ragas_metrics?: { faithfulness: number | null };
  id: string;
  experiment_id: string;
  query_id: string;
  answer: string;
  scores:
    | (Record<"correctness" | "faithfulness" | "relevance", number> & {
        rationale: string;
      })
    | null;
  raw: string;
  validation_error: string | null;
  rubric_version: string;
  config: { model: string };
};
export type HumanReview = {
  id: string;
  judgment_id: string;
  correctness: number;
  faithfulness: number;
  relevance: number;
  notes: string;
};
