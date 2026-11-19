import type { ReactNode } from "react";
import { Inbox, LoaderCircle } from "lucide-react";
import type { Comparison, Config, Metric, Mode } from "./types";

export const metricNames: Record<Metric, string> = {
  recall: "Recall",
  precision: "Precision",
  mrr: "MRR",
  ndcg: "NDCG",
};
export const modes: Mode[] = ["none", "conservative", "aggressive"];
export const defaultConfig: Config = {
  query_normalization: "none",
  corpus_normalization: "none",
  k: 5,
  k1: 1.5,
  b: 0.75,
};
export const score = (value: number | null | undefined) =>
  value == null ? "—" : value.toFixed(3);
export const delta = (value: number | null | undefined) =>
  value == null ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(3)}`;

export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty">
      <Inbox size={30} />
      <h3>{title}</h3>
      <div>{children}</div>
    </div>
  );
}
export function Loading({ text = "Loading results…" }: { text?: string }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={20} />
      {text}
    </div>
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function ConfigFields({
  value,
  onChange,
}: {
  value: Config;
  onChange: (value: Config) => void;
}) {
  return (
    <>
      <div className="form-grid">
        <label>
          Query normalization
          <select
            value={value.query_normalization}
            onChange={(e) =>
              onChange({
                ...value,
                query_normalization: e.target.value as Mode,
              })
            }
          >
            {modes.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </label>
        <label>
          Corpus normalization
          <select
            value={value.corpus_normalization}
            onChange={(e) =>
              onChange({
                ...value,
                corpus_normalization: e.target.value as Mode,
              })
            }
          >
            {modes.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </label>
        <label>
          Retrieval cutoff K
          <input
            type="number"
            min="1"
            max="50"
            required
            value={value.k}
            onChange={(e) => onChange({ ...value, k: Number(e.target.value) })}
          />
        </label>
        <label>
          Term saturation k₁
          <input
            type="number"
            min="0.1"
            max="3"
            step="0.1"
            required
            value={value.k1}
            onChange={(e) => onChange({ ...value, k1: Number(e.target.value) })}
          />
        </label>
        <label>
          Length normalization b
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            required
            value={value.b}
            onChange={(e) => onChange({ ...value, b: Number(e.target.value) })}
          />
        </label>
      </div>
      {value.query_normalization !== value.corpus_normalization && (
        <p className="notice amber">
          Asymmetric normalization can break token alignment. Compare it as an
          explicit experiment.
        </p>
      )}
    </>
  );
}
export function MetricCards({ comparison }: { comparison: Comparison }) {
  return (
    <div className="metric-grid">
      {(Object.keys(metricNames) as Metric[]).map((key) => {
        const m = comparison.summary[key];
        return (
          <article className="metric-card" key={key}>
            <div className="eyebrow">
              {metricNames[key]}@{comparison.baseline.config.k}
            </div>
            <div className="metric-value">
              {score(m.candidate)}
              <span
                className={`delta ${(m.delta ?? 0) < 0 ? "negative" : (m.delta ?? 0) > 0 ? "positive" : ""}`}
              >
                {delta(m.delta)}
              </span>
            </div>
            <div className="metric-baseline">
              Baseline <strong>{score(m.baseline)}</strong>
            </div>
            <div className="metric-track">
              <span style={{ width: `${(m.candidate ?? 0) * 100}%` }} />
              <i style={{ left: `${(m.baseline ?? 0) * 100}%` }} />
            </div>
            <div className="ci">
              95% Δ CI{" "}
              {m.bootstrap.interval
                ? `[${delta(m.bootstrap.interval[0])}, ${delta(m.bootstrap.interval[1])}]`
                : "withheld"}
            </div>
          </article>
        );
      })}
    </div>
  );
}
