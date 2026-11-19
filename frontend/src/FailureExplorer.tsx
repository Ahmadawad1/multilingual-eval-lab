import { useMemo, useState } from "react";
import { Search, SlidersHorizontal, TriangleAlert } from "lucide-react";
import { Badge, delta, Empty, score } from "./components";
import type {
  Comparison,
  ComparisonRow,
  DatasetDetail,
  Metric,
  Row,
  Status,
} from "./types";

function PassageList({
  row,
  dataset,
  variant,
}: {
  row: Row;
  dataset: DatasetDetail;
  variant: string;
}) {
  const documents = new Map(dataset.data.documents.map((d) => [d.id, d]));
  return (
    <section className="ranking-column">
      <div className="ranking-header">
        <Badge tone={variant === "Candidate" ? "teal" : ""}>{variant}</Badge>
        <span>NDCG {score(row.metrics?.ndcg)}</span>
      </div>
      <p className="normalized">
        <span>Normalized query</span>
        <b dir="auto">{row.normalized_question}</b>
      </p>
      {row.ranking.length === 0 && (
        <div className="no-passages">No lexical matches retrieved.</div>
      )}
      {row.ranking.map((item) => {
        const doc = documents.get(item.doc_id);
        const grade = row.qrels[item.doc_id];
        return (
          <article
            className={`passage ${grade > 0 ? "relevant" : ""}`}
            key={item.doc_id}
          >
            <div className="passage-top">
              <span className="rank">#{item.rank}</span>
              <code>{item.doc_id}</code>
              <Badge tone={grade > 0 ? "teal" : "muted"}>
                {grade === undefined ? "Unjudged" : `Grade ${grade}/3`}
              </Badge>
            </div>
            <p className="arabic" dir="auto">
              {doc?.text ?? "Passage unavailable"}
            </p>
            <small>BM25 score {item.score.toFixed(4)}</small>
          </article>
        );
      })}
      <details className="relevance-details">
        <summary>
          All relevance judgments ({Object.keys(row.qrels).length})
        </summary>
        {Object.entries(row.qrels).map(([id, grade]) => (
          <div className="label-evidence" key={id}>
            <code>{id}</code>
            <Badge>Grade {grade}</Badge>
            <p dir="auto" className="arabic">
              {documents.get(id)?.text}
            </p>
          </div>
        ))}
      </details>
    </section>
  );
}

export default function FailureExplorer({
  comparison,
  dataset,
  onJudge,
}: {
  comparison: Comparison;
  dataset: DatasetDetail;
  onJudge: (row: ComparisonRow) => void;
}) {
  const [filter, setFilter] = useState<Status | "all">("regressed");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [metric, setMetric] = useState<Metric>("ndcg");
  const rows = useMemo(
    () =>
      comparison.rows
        .filter(
          (row) =>
            (filter === "all" || row.status === filter) &&
            `${row.question} ${row.query_id} ${String(row.candidate.metadata.category ?? "")}`
              .toLowerCase()
              .includes(search.toLowerCase()),
        )
        .sort((a, b) => (a.deltas?.[metric] ?? 0) - (b.deltas?.[metric] ?? 0)),
    [comparison, filter, search, metric],
  );
  const current = rows.find((row) => row.query_id === selected) ?? rows[0];
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Every regression has a story.</h2>
          <p>Inspect the evidence behind a score, one query at a time.</p>
        </div>
        <Badge tone="amber">
          Status uses NDCG@{comparison.baseline.config.k}
        </Badge>
      </div>
      <div className="filter-bar">
        <div className="segmented" aria-label="Query status filter">
          {(
            ["regressed", "improved", "unchanged", "excluded", "all"] as const
          ).map((s) => (
            <button
              className={filter === s ? "active" : ""}
              key={s}
              onClick={() => setFilter(s)}
            >
              {s}{" "}
              <span>
                {s === "all" ? comparison.rows.length : comparison.counts[s]}
              </span>
            </button>
          ))}
        </div>
        <label className="search-control">
          <Search size={16} />
          <input
            aria-label="Search queries"
            placeholder="Find a query or category…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      {!current ? (
        <Empty title="No matching queries">
          Try another filter or search term.
        </Empty>
      ) : (
        <div className="explorer">
          <aside className="query-list">
            <label className="sort-control">
              <SlidersHorizontal size={15} />
              Sort by delta
              <select
                aria-label="Sort query deltas"
                value={metric}
                onChange={(e) => setMetric(e.target.value as Metric)}
              >
                {["ndcg", "recall", "precision", "mrr"].map((m) => (
                  <option key={m} value={m}>
                    {m.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            {rows.map((row) => (
              <button
                key={row.query_id}
                className={`query-item ${current.query_id === row.query_id ? "selected" : ""}`}
                onClick={() => setSelected(row.query_id)}
                aria-pressed={current.query_id === row.query_id}
              >
                <div>
                  <span className="query-id">{row.query_id}</span>
                  <span
                    className={
                      (row.deltas?.[metric] ?? 0) < 0 ? "negative" : "positive"
                    }
                  >
                    {delta(row.deltas?.[metric])}
                  </span>
                </div>
                <p dir="auto" className="arabic">
                  {row.question}
                </p>
                <small>
                  {String(row.candidate.metadata.category ?? "Uncategorized")}
                </small>
              </button>
            ))}
          </aside>
          <div className="query-detail">
            <div className="query-detail-heading">
              <div>
                <div className="eyebrow">
                  QUERY EVIDENCE <span> / {current.query_id}</span>
                </div>
                <h2 dir="auto" className="arabic">
                  {current.question}
                </h2>
              </div>
              <Badge tone={current.status === "regressed" ? "red" : "teal"}>
                {current.status}
              </Badge>
            </div>
            <div className="query-metrics">
              {(["ndcg", "recall", "precision", "mrr"] as const).map((m) => (
                <div key={m}>
                  <span>{m.toUpperCase()} Δ</span>
                  <b
                    className={(current.deltas?.[m] ?? 0) < 0 ? "negative" : ""}
                  >
                    {delta(current.deltas?.[m])}
                  </b>
                </div>
              ))}
            </div>
            <div className="hypothesis">
              <TriangleAlert size={18} />
              <div>
                <strong>Diagnostic hypotheses · verify against evidence</strong>
                <ul>
                  {current.candidate.hypotheses.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="rankings">
              <PassageList
                row={current.baseline}
                dataset={dataset}
                variant="Baseline"
              />
              <PassageList
                row={current.candidate}
                dataset={dataset}
                variant="Candidate"
              />
            </div>
            <div className="expected-answer">
              <span className="eyebrow">EXPECTED ANSWER</span>
              <p dir="auto" className="arabic">
                {current.candidate.expected_answer ||
                  "No reference answer supplied."}
              </p>
              <button
                className="button secondary"
                onClick={() => onJudge(current)}
              >
                Review generation quality
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
