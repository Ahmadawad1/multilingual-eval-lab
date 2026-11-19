import { useEffect, useState } from "react";
import { api } from "./api";
import { Badge, Empty } from "./components";
import type { Comparison, HumanReview, Judgment } from "./types";

export default function JudgePanel({
  comparison,
  initialQuery,
  run,
  busy,
}: {
  comparison: Comparison;
  initialQuery: string;
  run: (task: () => Promise<void>) => Promise<void>;
  busy: boolean;
}) {
  const [queryId, setQueryId] = useState(
    initialQuery || comparison.rows[0]?.query_id || "",
  );
  const [answer, setAnswer] = useState("");
  const [judgments, setJudgments] = useState<Judgment[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [selected, setSelected] = useState("");
  const [notes, setNotes] = useState("");
  const [human, setHuman] = useState({
    correctness: 2,
    faithfulness: 2,
    relevance: 2,
  });
  const [loadError, setLoadError] = useState("");
  const query = comparison.rows.find((r) => r.query_id === queryId);
  const visible = judgments.filter(
    (j) =>
      j.experiment_id === comparison.candidate.id && j.query_id === queryId,
  );
  const judgment = visible.find((j) => j.id === selected) ?? visible[0];
  useEffect(() => {
    setNotes("");
    setHuman({ correctness: 2, faithfulness: 2, relevance: 2 });
  }, [judgment?.id]);
  async function refresh() {
    const result = await api<{ judgments: Judgment[]; reviews: HumanReview[] }>(
      "/judgments",
    );
    setJudgments(result.judgments);
    setReviews(result.reviews);
  }
  useEffect(() => {
    void refresh().catch((e) => setLoadError(String(e)));
  }, []);
  return (
    <div className="two-column">
      <section className="panel">
        <div className="panel-title">
          <h2>Local LLM judge</h2>
          <Badge tone="amber">Uncalibrated</Badge>
        </div>
        <p className="muted">
          Evaluate an answer against the candidate’s retrieved passages and
          reference answer. A local model must be installed and configured.
        </p>
        {loadError && <p className="notice amber">{loadError}</p>}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              const result = await api<Judgment>("/judgments", {
                experiment_id: comparison.candidate.id,
                query_id: queryId,
                answer,
              });
              await refresh();
              setSelected(result.id);
            });
          }}
        >
          <label>
            Query
            <select
              value={queryId}
              onChange={(e) => {
                setQueryId(e.target.value);
                setAnswer("");
                setNotes("");
              }}
            >
              {comparison.rows.map((r) => (
                <option value={r.query_id} key={r.query_id}>
                  {r.query_id} · {r.question}
                </option>
              ))}
            </select>
          </label>
          <div className="reference">
            <small>Reference answer</small>
            <p dir="auto" className="arabic">
              {query?.candidate.expected_answer ||
                "Missing reference answer; correctness judging unavailable."}
            </p>
          </div>
          <label>
            Answer to evaluate
            <textarea
              dir="auto"
              required
              maxLength={12000}
              rows={6}
              placeholder="Paste your system’s answer here…"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          </label>
          <button
            className="button primary"
            disabled={busy || !query?.candidate.expected_answer}
          >
            {busy ? "Evaluating…" : "Evaluate with local model"}
          </button>
        </form>
        <details className="rubric">
          <summary>Rubric and limitations</summary>
          <p>
            Each dimension uses a 0–4 ordinal scale: 0 = fails, 1 = mostly
            fails, 2 = partial, 3 = mostly meets, 4 = fully meets.
          </p>
          <ul>
            <li>Correctness: agreement with the expected answer.</li>
            <li>Faithfulness: factual support in retrieved passages.</li>
            <li>Relevance: directness and sufficiency for the question.</li>
          </ul>
          <p>
            The exact versioned rubric, request, configuration, model identity
            and raw output are saved in the JSON report. Human labels are
            independent; no calibrated agreement score is claimed. Local models
            can still follow malicious passage instructions.
          </p>
        </details>
      </section>
      <section className="panel">
        <h2>Judgment & human review</h2>
        {!judgment ? (
          <Empty title="No judgment for this query">
            Run the local judge to record its evidence, then add a human
            assessment.
          </Empty>
        ) : (
          <>
            <label>
              Recorded judgment
              <select
                value={judgment.id}
                onChange={(e) => setSelected(e.target.value)}
              >
                {visible.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.config.model} · {j.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </label>
            <div className="reference">
              <small>Answer evaluated in this saved judgment</small>
              <p dir="auto" className="arabic">
                {judgment.answer}
              </p>
            </div>
            {judgment.scores ? (
              <>
                <div className="judge-scores">
                  {(["correctness", "faithfulness", "relevance"] as const).map(
                    (key) => (
                      <div key={key}>
                        <small>{key}</small>
                        <strong>
                          {judgment.scores![key]}
                          <span>/4</span>
                        </strong>
                      </div>
                    ),
                  )}
                </div>
                <p dir="auto">{judgment.scores.rationale}</p>
              </>
            ) : (
              <p className="notice amber">
                Invalid structured response. No scores were accepted.{" "}
                {judgment.validation_error}
              </p>
            )}
            <details>
              <summary>Raw model output</summary>
              <pre>{judgment.raw}</pre>
            </details>
            <hr />
            <h3>Your independent assessment</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await api(`/judgments/${judgment.id}/reviews`, {
                    ...human,
                    notes,
                  });
                  await refresh();
                  setNotes("");
                });
              }}
            >
              <div className="form-grid">
                {(["correctness", "faithfulness", "relevance"] as const).map(
                  (key) => (
                    <label key={key}>
                      {key}
                      <select
                        value={human[key]}
                        onChange={(e) =>
                          setHuman({ ...human, [key]: Number(e.target.value) })
                        }
                      >
                        {[0, 1, 2, 3, 4].map((n) => (
                          <option key={n} value={n}>
                            {n} / 4
                          </option>
                        ))}
                      </select>
                    </label>
                  ),
                )}
              </div>
              <label>
                Review notes
                <textarea
                  required
                  maxLength={4000}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Explain the evidence behind your scores…"
                />
              </label>
              <button className="button secondary" disabled={busy}>
                Save human review
              </button>
            </form>
            {reviews
              .filter((r) => r.judgment_id === judgment.id)
              .map((r) => (
                <div className="saved-review" key={r.id}>
                  <Badge tone="teal">Human assessment saved</Badge>
                  <p>
                    Correctness {r.correctness} · Faithfulness {r.faithfulness}{" "}
                    · Relevance {r.relevance}
                  </p>
                  <p dir="auto">{r.notes}</p>
                </div>
              ))}
          </>
        )}
      </section>
    </div>
  );
}
