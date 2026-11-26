import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { evalApi, evalClient, evalErrorMessage } from "@/api/eval.api";
import { useSelectedDataset } from "@/features/evaluation/hooks/useEval";
import { useEvalStore } from "@/store/eval.store";
import { Button } from "@/components/ui/button";
import {
  Field,
  Panel,
  TextArea,
  TextField,
  SelectBox,
  JobBar,
} from "@/features/evaluation/components/EvalPrimitives";
import type { GoldenItem, Job } from "@/types/eval";

interface Model {
  name: string;
  digest: string;
  query_prefix: string;
  passage_prefix: string;
}
interface Metric {
  mean: number;
  low: number | null;
  high: number | null;
}
interface Cell {
  query: string;
  query_id: string;
  hit: number;
  rank: number | null;
  ranked: { doc_id: string; score: number; rank: number; excerpt?: string }[];
}
interface PairRow {
  pair_id: string;
  cluster: string;
  qrels: Record<string, number>;
  bm25_msa: Cell;
  bm25_jo: Cell;
  dense_msa: Cell;
  dense_jo: Cell;
}
interface Run {
  id: string;
  status: string;
  split: string;
  confirmatory: boolean;
  error?: string;
  rows: PairRow[];
  index?: { identity: string; dimension: number };
  report?: {
    metrics: Record<string, Metric>;
    pairs: number;
    clusters: number;
    primary: string;
    threshold_supported: boolean;
    confidence: number;
    warnings: string[];
  };
}
interface Study {
  id: string;
  name: string;
  status: string;
  dataset_id: string;
  dataset_version: number;
  hypothesis: string;
  rationale: string;
  model: Model;
  primary: string;
  k: number;
  dataset_hash: string;
  protocol_hash?: string;
  run_records?: Run[];
  holdout_access: { at: string; reason: string; run_id: string }[];
}
interface PairEdit {
  pair_id: string;
  msa_id: string;
  jo_id: string;
  msa: string;
  jo: string;
  qrels: string;
  source_article: string;
  reviewed: boolean;
  reviewer: string;
}
interface Preview {
  pairs: number;
  passages: number;
  excluded: { example_id: string; reason: string }[];
  warning: string;
  sample: GoldenItem[];
  dataset_id?: string;
}
const emptyPair: PairEdit = {
  pair_id: "",
  msa_id: "",
  jo_id: "",
  msa: "",
  jo: "",
  qrels: "{}",
  source_article: "",
  reviewed: false,
  reviewer: "",
};
const cells = ["bm25_msa", "bm25_jo", "dense_msa", "dense_jo"] as const;
const labels: Record<string, string> = {
  bm25_msa: "BM25 · MSA",
  bm25_jo: "BM25 · Jordanian",
  dense_msa: "Dense · MSA",
  dense_jo: "Dense · Jordanian",
  bm25_gap: "BM25 dialect gap",
  dense_gap: "Dense dialect gap",
  jo_gain: "Dense gain for Jordanian",
  msa_gain: "Dense gain for MSA",
  gap_change: "Change in dialect gap",
};
const get = async <T,>(path: string) =>
  (await evalClient.get<T>("/paired" + path)).data;
const post = async <T,>(path: string, body?: unknown) =>
  (await evalClient.post<T>("/paired" + path, body)).data;

export function PairedStudyPage() {
  const qc = useQueryClient();
  const { data: bundle, datasetId, version } = useSelectedDataset();
  const select = useEvalStore((s) => s.select);
  const [params, setParams] = useSearchParams();
  const sid = params.get("study") ?? "";
  const [stage, setStage] = useState("data");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState("");
  const [pair, setPair] = useState<PairEdit>(emptyPair);
  const [seed, setSeed] = useState(42);
  const [fraction, setFraction] = useState(0.3);
  const [model, setModel] = useState("");
  const [name, setName] = useState(
    "Jordanian versus MSA across BM25 and dense",
  );
  const [hypothesis, setHypothesis] = useState(
    "Jordanian Hit@5 will be lower than MSA Hit@5 under BM25. Dense retrieval may reduce this deficit.",
  );
  const [rationale, setRationale] = useState(
    "BM25 depends on word overlap; dense embeddings may connect equivalent meanings. Both forms use the same intent, passages and qrels.",
  );
  const [primary, setPrimary] = useState("bm25_gap");
  const [direction, setDirection] = useState("decrease");
  const [effect, setEffect] = useState(0.05);
  const [confidence, setConfidence] = useState(0.95);
  const [k, setK] = useState(5);
  const [reason, setReason] = useState("");
  const [selectedRun, setSelectedRun] = useState("");
  const [rowIndex, setRowIndex] = useState(0);
  const [wanaText, setWanaText] = useState("");
  const [wanaLimit, setWanaLimit] = useState(50);
  const [preview, setPreview] = useState<Preview | null>(null);
  const models = useQuery({
    queryKey: ["paired", "models"],
    queryFn: () => get<{ models: Model[] }>("/models"),
    retry: false,
  });
  const studies = useQuery({
    queryKey: ["paired", "studies"],
    queryFn: () => get<Study[]>("/studies"),
  });
  const studyQuery = useQuery({
    queryKey: ["paired", sid],
    queryFn: () => get<Study>(`/studies/${sid}`),
    enabled: !!sid,
    refetchInterval: q => jobId || q.state.data?.run_records?.some(r => r.status === 'running') ? 2000 : false,
  });
  const validation = useQuery({
    queryKey: ["paired", "validation", datasetId, version],
    queryFn: () =>
      get<{ issues: string[] }>(`/datasets/${datasetId}/${version}`),
    enabled: !!datasetId && !!version,
  });
  const job = useQuery({
    queryKey: ["paired", "job", jobId],
    queryFn: () => evalApi.job(jobId),
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 1000 : false),
  });
  useEffect(() => {
    if (job.data && job.data.status !== "running") {
      if (job.data.error) setError(job.data.error);
      else {
        setNotice("All four conditions completed.");
        setStage("report");
        setSelectedRun(String(job.data.result.run_id));
      }
      void qc.invalidateQueries({ queryKey: ["paired", sid] });
      setJobId("");
    }
  }, [job.data, qc, sid]);
  useEffect(() => {
    setPair(emptyPair);
  }, [datasetId, version]);
  const study = studyQuery.data;
  const runs = study?.run_records ?? [];
  const run =
    runs.find((r) => r.id === selectedRun) ??
    [...runs].reverse().find((r) => r.status === "done");
  const frozen = bundle?.manifest.status === "frozen";
  const pairIds = [
    ...new Set(
      (bundle?.items ?? []).map((i) => String(i.metadata?.pair_id ?? "")),
    ),
  ].filter(Boolean);
  const action = async (work: () => Promise<void>) => {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await work();
      await qc.invalidateQueries({ queryKey: ["paired"] });
      await qc.invalidateQueries({ queryKey: ["eval"] });
    } catch (e) {
      setError(evalErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const edit = (id: string) => {
    const items = bundle?.items.filter((i) => i.metadata?.pair_id === id) ?? [];
    const msa = items.find((i) => i.metadata?.form === "msa");
    const jo = items.find((i) => i.metadata?.form === "jo");
    const base = msa ?? jo;
    setPair({
      pair_id: id,
      msa_id: msa?.id ?? `${id}_msa`,
      jo_id: jo?.id ?? `${id}_jo`,
      msa: msa?.query ?? "",
      jo: jo?.query ?? "",
      qrels: JSON.stringify(
        {
          ...Object.fromEntries(
            (base?.judged_nonrelevant ?? []).map((d) => [d, 0]),
          ),
          ...base?.relevant,
        },
        null,
        2,
      ),
      source_article: String(base?.metadata?.source_article ?? ""),
      reviewed: base?.metadata?.pair_reviewed === true,
      reviewer: String(base?.metadata?.reviewer ?? ""),
    });
  };
  const pairField = (key: keyof PairEdit, value: string | boolean) =>
    setPair((p) => ({
      ...p,
      [key]: value,
      ...(key !== "reviewed" && key !== "reviewer" ? { reviewed: false } : {}),
    }));

  return (
    <div className="space-y-5">
      <div>
        <Link className="text-sm text-neon" to="/evaluation/experiments">
          ← Retrieval experiments
        </Link>
        <h1 className="mt-3 font-display text-2xl font-semibold">
          Jordanian and MSA · BM25 and dense
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          One corpus, paired questions, four conditions. Review the data, lock a
          protocol, then measure the dialect gap.
        </p>
      </div>
      <nav
        className="grid grid-cols-2 gap-2 md:grid-cols-4"
        aria-label="Paired study steps"
      >
        {["data", "design", "run", "report"].map((s, i) => (
          <Button
            key={s}
            variant={stage === s ? "neon" : "outline"}
            onClick={() => setStage(s)}
          >
            {i + 1}. {s[0].toUpperCase() + s.slice(1)}
          </Button>
        ))}
      </nav>
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-400/40 p-4 text-sm text-red-400"
        >
          {error}
        </div>
      )}
      {notice && (
        <p role="status" className="text-sm text-emerald-400">
          {notice}
        </p>
      )}
      {stage === "data" && (
        <>
          <Panel title="Import a TyDi QA-WANA subset">
            <p className="mb-3 text-sm text-muted-foreground">
              Upload labeled Jordanian JSONL or a JSON array below 11 MB. Byte
              offsets become candidate passage qrels. MSA wording is left for
              human review; no automatic translation is assumed. Larger releases
              must be sampled outside the browser.
            </p>
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Source file">
                <input
                  type="file"
                  accept=".json,.jsonl"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f)
                      void action(async () => {
                        if (f.size > 11000000)
                          throw Error("Choose a subset below 11 MB");
                        setWanaText(await f.text());
                        setPreview(null);
                      });
                  }}
                />
              </Field>
              <Field label="Maximum pairs">
                <TextField
                  type="number"
                  min={1}
                  max={500}
                  value={wanaLimit}
                  onChange={(e) => {
                    setWanaLimit(Number(e.target.value));
                    setPreview(null);
                  }}
                />
              </Field>
              <Field label="Sampling and split seed">
                <TextField
                  type="number"
                  min={0}
                  value={seed}
                  onChange={(e) => {
                    setSeed(Number(e.target.value));
                    setPreview(null);
                  }}
                />
              </Field>
            </div>
            <div className="mt-3 flex gap-3">
              <Button
                disabled={!wanaText || busy}
                onClick={() =>
                  void action(async () =>
                    setPreview(
                      await post<Preview>("/wana", {
                        text: wanaText,
                        limit: wanaLimit,
                        seed,
                      }),
                    ),
                  )
                }
              >
                Preview adaptation
              </Button>
              <Button
                disabled={!preview?.pairs || busy}
                onClick={() =>
                  void action(async () => {
                    const result = await post<Preview>("/wana", {
                      text: wanaText,
                      limit: wanaLimit,
                      seed,
                      confirm: true,
                    });
                    select(result.dataset_id!, 1);
                    setPreview(result);
                    setNotice(
                      "Imported a draft. Review and complete every MSA pair.",
                    );
                  })
                }
              >
                Import preview as draft
              </Button>
            </div>
            {preview && (
              <div className="mt-3 space-y-2 text-sm">
                <p>
                  {preview.pairs} candidate pairs · {preview.passages} passages
                  · {preview.excluded.length} excluded records
                </p>
                <p>{preview.warning}</p>
                {preview.sample
                  .filter((i) => i.metadata?.form === "jo")
                  .map((i) => (
                    <p key={i.id} dir="auto">
                      {i.query}
                    </p>
                  ))}
                <ul className="max-h-40 overflow-auto">
                  {preview.excluded.map((x, i) => (
                    <li key={i}>
                      {x.example_id}: {x.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>
          {!bundle ? (
            <p>Select a Golden Set above, or import a benchmark subset.</p>
          ) : (
            <>
              <Panel
                title={`Paired questions · ${bundle.meta.name} v${version}`}
              >
                <p className="mb-3 text-sm text-muted-foreground">
                  {pairIds.length} pair IDs · {bundle.items.length} questions ·{" "}
                  {bundle.corpus.length} passages · {bundle.manifest.status}.
                  Existing JSON/qrels imports remain available in{" "}
                  <Link to="/evaluation/dataset" className="text-neon">
                    Golden Sets
                  </Link>
                  .
                </p>
                <div className="flex flex-wrap gap-2">
                  <SelectBox
                    value={pair.pair_id}
                    options={[
                      { value: "", label: "New pair or select a pair" },
                      ...pairIds.map((id) => ({ value: id, label: id })),
                    ]}
                    onChange={(id) => (id ? edit(id) : setPair(emptyPair))}
                  />
                  <Button variant="outline" onClick={() => setPair(emptyPair)}>
                    New pair
                  </Button>
                </div>
                <p className="my-2 text-xs text-muted-foreground">
                  For unpaired imports, enter the existing question IDs to link
                  them. Shared qrels are applied to both forms.
                </p>
                <fieldset disabled={frozen || busy} className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-3">
                    {(["pair_id", "msa_id", "jo_id"] as const).map((key) => (
                      <Field key={key} label={key.replace(/_/g, " ")}>
                        <TextField
                          value={pair[key]}
                          onChange={(e) => pairField(key, e.target.value)}
                        />
                      </Field>
                    ))}
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Field label="MSA question">
                      <TextArea
                        dir="auto"
                        value={pair.msa}
                        onChange={(e) => pairField("msa", e.target.value)}
                      />
                    </Field>
                    <Field label="Jordanian question">
                      <TextArea
                        dir="auto"
                        value={pair.jo}
                        onChange={(e) => pairField("jo", e.target.value)}
                      />
                    </Field>
                    <Field
                      label="Shared qrels JSON"
                      hint='Example: {"passage-1": 1}. Grades 0–3.'
                    >
                      <TextArea
                        value={pair.qrels}
                        onChange={(e) => pairField("qrels", e.target.value)}
                      />
                    </Field>
                    <div className="space-y-3">
                      <Field label="Source article or source group">
                        <TextField
                          value={pair.source_article}
                          onChange={(e) =>
                            pairField("source_article", e.target.value)
                          }
                        />
                      </Field>
                      <Field label="Reviewer name or ID">
                        <TextField
                          value={pair.reviewer}
                          onChange={(e) =>
                            pairField("reviewer", e.target.value)
                          }
                        />
                      </Field>
                    </div>
                  </div>
                  <label className="flex gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={pair.reviewed}
                      onChange={(e) => pairField("reviewed", e.target.checked)}
                    />
                    I checked that both forms ask the same thing and that the
                    shared qrels are correct.
                  </label>
                  <Button
                    onClick={() =>
                      void action(async () => {
                        await evalClient.put(
                          `/paired/datasets/${datasetId}/${version}/pair`,
                          { ...pair, qrels: JSON.parse(pair.qrels) },
                        );
                        setNotice("Pair saved. Reassign splits after editing.");
                      })
                    }
                  >
                    Save pair
                  </Button>
                </fieldset>
                {frozen && (
                  <p className="mt-3 text-sm">
                    This version is frozen. Fork it in Golden Sets to edit.
                  </p>
                )}
                <details className="mt-4">
                  <summary>Passages and existing question IDs</summary>
                  <div className="mt-3 max-h-80 space-y-3 overflow-auto text-sm">
                    {bundle.items.map((i) => (
                      <p key={i.id}>
                        <strong>{i.id}</strong> · {i.split ?? "unassigned"} ·{" "}
                        <span dir="auto">{i.query}</span>
                      </p>
                    ))}
                    {bundle.corpus.map((d) => (
                      <p key={d.doc_id}>
                        <strong>{d.doc_id}</strong> ·{" "}
                        <span dir="auto">{d.body}</span>
                      </p>
                    ))}
                  </div>
                </details>
              </Panel>
              <Panel title="Validate and split by intent and source">
                {validation.data?.issues.length ? (
                  <ul className="mb-3 max-h-52 list-disc overflow-auto pl-5 text-sm text-amber-300">
                    {validation.data.issues.map((x, i) => (
                      <li key={i}>{x}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mb-3 text-sm text-emerald-400">
                    Pairs have matching labels and review records.
                  </p>
                )}
                <p className="mb-3 text-sm text-muted-foreground">
                  Both forms stay together. All connected source articles and
                  relevant passages stay in one split. This prevents related
                  questions from leaking across dev and holdout.
                </p>
                <div className="flex flex-wrap items-end gap-3">
                  <Field label="Holdout fraction">
                    <TextField
                      type="number"
                      min={0.1}
                      max={0.5}
                      step={0.05}
                      value={fraction}
                      onChange={(e) => setFraction(Number(e.target.value))}
                    />
                  </Field>
                  <Button
                    disabled={busy || frozen}
                    onClick={() =>
                      void action(async () => {
                        await post(`/datasets/${datasetId}/${version}/split`, {
                          seed,
                          holdout_fraction: fraction,
                        });
                        setNotice(
                          "Paired source groups assigned to dev and holdout.",
                        );
                      })
                    }
                  >
                    Assign paired splits
                  </Button>
                  <Button
                    disabled={
                      busy || frozen || !!validation.data?.issues.length
                    }
                    onClick={() =>
                      void action(async () => {
                        await evalClient.post(
                          `/datasets/${datasetId}/versions/${version}/freeze`,
                        );
                        setNotice("Dataset version frozen.");
                      })
                    }
                  >
                    Freeze version
                  </Button>
                </div>
                <p className="mt-3 text-sm">
                  Dev: {bundle.items.filter((i) => i.split === "dev").length}{" "}
                  questions · Holdout:{" "}
                  {bundle.items.filter((i) => i.split === "holdout").length} ·
                  Unassigned: {bundle.items.filter((i) => !i.split).length}
                </p>
              </Panel>
            </>
          )}
        </>
      )}
      {stage === "design" && (
        <Panel title="Define the four-condition study">
          <p className="mb-4 text-sm text-muted-foreground">
            BM25/MSA · BM25/Jordanian · Dense/MSA · Dense/Jordanian. Every
            condition uses the same full passages, qrels and cutoff. Dense uses
            exact cosine similarity, no hybrid search or extra chunking, and
            rejects input truncation.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Study name">
              <TextField
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field
              label="Local embedding model"
              hint="Installed models only. BGE-M3 is multilingual; Nomic is a pipeline baseline, not an Arabic quality guarantee."
            >
              <SelectBox
                value={model}
                options={[
                  { value: "", label: "Select installed embedding model" },
                  ...(models.data?.models ?? []).map((m) => ({
                    value: m.name,
                    label: m.name,
                  })),
                ]}
                onChange={setModel}
              />
              <Button variant="ghost" onClick={() => void models.refetch()}>
                Refresh models
              </Button>
            </Field>
            <Field
              label="Hypothesis"
              hint="A testable expectation: specify the contrast, direction and useful effect."
            >
              <TextArea
                value={hypothesis}
                onChange={(e) => setHypothesis(e.target.value)}
              />
            </Field>
            <Field
              label="Rationale"
              hint="Explain the mechanism and prior evidence without assuming the result."
            >
              <TextArea
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
              />
            </Field>
          </div>
          {(models.isError || !models.data?.models.length) && (
            <p className="my-3 text-sm text-amber-300">
              Start local Ollama and install a supported embedding model, for
              example <code>ollama pull bge-m3</code>, then refresh. Model
              downloads are not automatic.{" "}
              {models.isError ? evalErrorMessage(models.error) : ""}
            </p>
          )}
          {model && (
            <p className="my-3 break-all text-xs text-muted-foreground">
              Model digest:{" "}
              {models.data?.models.find((m) => m.name === model)?.digest}
            </p>
          )}
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <Field label="Primary contrast">
              <SelectBox
                value={primary}
                options={["bm25_gap", "dense_gap", "jo_gain", "gap_change"].map(
                  (v) => ({ value: v, label: labels[v] }),
                )}
                onChange={setPrimary}
              />
            </Field>
            <Field label="Expected direction">
              <SelectBox
                value={direction}
                options={[
                  { value: "decrease", label: "Decrease" },
                  { value: "increase", label: "Increase" },
                ]}
                onChange={setDirection}
              />
            </Field>
            <Field
              label="Minimum meaningful effect"
              hint="0.05 = five percentage points."
            >
              <TextField
                type="number"
                min={0.01}
                max={1}
                step={0.01}
                value={effect}
                onChange={(e) => setEffect(Number(e.target.value))}
              />
            </Field>
            <Field label="Hit rate cutoff k">
              <TextField
                type="number"
                min={1}
                max={50}
                value={k}
                onChange={(e) => setK(Number(e.target.value))}
              />
            </Field>
            <Field label="Confidence level">
              <SelectBox
                value={confidence}
                options={[
                  { value: 0.9, label: "90%" },
                  { value: 0.95, label: "95%" },
                  { value: 0.99, label: "99%" },
                ]}
                onChange={setConfidence}
              />
            </Field>
            <Field label="Bootstrap seed">
              <TextField
                type="number"
                min={0}
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </Field>
          </div>
          <p className="my-4 text-sm text-muted-foreground">
            Dialect gap = Jordanian − MSA. Gap change = dense gap − BM25 gap.
            Secondary comparisons are exploratory. BM25 is fixed at k1=1.5 and
            b=0.75 with normalization off.
          </p>
          <Button
            disabled={busy || !datasetId || !model}
            onClick={() =>
              void action(async () => {
                const s = await post<Study>("/studies", {
                  name,
                  dataset_id: datasetId,
                  dataset_version: version,
                  hypothesis,
                  rationale,
                  model_name: model,
                  primary,
                  direction,
                  min_effect: effect,
                  confidence,
                  k,
                  seed,
                });
                setParams({ study: s.id });
                setStage("run");
                setNotice(
                  "Draft saved. Register after the dataset is frozen and split.",
                );
              })
            }
          >
            Save new study draft
          </Button>
        </Panel>
      )}
      {(stage === "run" || stage === "report") && (
        <>
          <Panel title="Saved studies">
            <SelectBox
              value={sid}
              options={[
                { value: "", label: "Select a saved study" },
                ...(studies.data ?? []).map((s) => ({
                  value: s.id,
                  label: `${s.name} · ${s.status}`,
                })),
              ]}
              onChange={(id) => {
                setParams(id ? { study: id } : {});
                setSelectedRun("");
                setRowIndex(0);
              }}
            />
            {studyQuery.isError && (
              <p role="alert">{evalErrorMessage(studyQuery.error)}</p>
            )}
            {study && (
              <div className="mt-3 space-y-2 text-sm">
                <p>
                  {study.dataset_id} v{study.dataset_version} · {study.status} ·
                  Hit@{study.k} · Primary: {labels[study.primary]}
                </p>
                <p>{study.hypothesis}</p>
                <p className="text-muted-foreground">{study.rationale}</p>
                <p className="break-all text-xs">
                  Model: {study.model.name} · {study.model.digest}
                </p>
                <p className="break-all text-xs">
                  Dataset: {study.dataset_hash}
                </p>
                {study.protocol_hash && (
                  <p className="break-all text-xs">
                    Registered protocol: {study.protocol_hash}
                  </p>
                )}
              </div>
            )}
          </Panel>
          {stage === "run" && study && (
            <Panel title="Register and evaluate">
              <p className="mb-3 text-sm">
                A run scores all four conditions. Registration locks the dataset
                hash, model identity and primary criterion. Holdout is available
                only after registration; repeat access is logged and marked
                exploratory.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button
                  disabled={busy || !!jobId || study.status !== "draft"}
                  onClick={() =>
                    void action(async () => {
                      await post(`/studies/${sid}/register`);
                      setNotice("Protocol registered.");
                    })
                  }
                >
                  Register protocol
                </Button>
                {(["dev", "holdout"] as const).map((split) => (
                  <Button
                    key={split}
                    disabled={
                      busy ||
                      !!jobId ||
                      (split === "holdout" && study.status !== "registered")
                    }
                    onClick={() =>
                      void action(async () => {
                        const j = await post<Job>(`/studies/${sid}/runs`, {
                          split,
                          reason,
                        });
                        setJobId(j.id);
                        useEvalStore.getState().trackJob(j.id);
                      })
                    }
                  >
                    Run all four on {split}
                  </Button>
                ))}
              </div>
              <Field label="Reason for repeat holdout access">
                <TextArea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain why another access is necessary (at least 10 characters)."
                />
              </Field>
              <JobBar jobId={jobId || null} />
              <ul className="mt-3 text-sm">
                {study.holdout_access.map((a) => (
                  <li key={a.run_id}>
                    {a.at} · {a.reason || "First access"} · {a.run_id}
                  </li>
                ))}
              </ul>
              <div className="mt-4 space-y-2">
                {runs.map((r) => (
                  <p key={r.id} className="text-sm">
                    {r.id} · {r.split} · {r.status}{" "}
                    {r.error && <span className="text-red-400">{r.error}</span>}
                  </p>
                ))}
              </div>
            </Panel>
          )}
          {stage === "report" && study && (
            <>
              <div className="flex flex-wrap gap-3">
                <SelectBox
                  value={run?.id ?? ""}
                  options={[
                    { value: "", label: "Choose a run" },
                    ...runs.map((r) => ({
                      value: r.id,
                      label: `${r.id} · ${r.split} · ${r.status}`,
                    })),
                  ]}
                  onChange={(id) => {
                    setSelectedRun(id);
                    setRowIndex(0);
                  }}
                />
                <Button
                  disabled={busy}
                  onClick={() =>
                    void action(async () => {
                      const response = await evalClient.get(
                        `/paired/studies/${sid}/export`,
                        { responseType: "blob" },
                      );
                      const url = URL.createObjectURL(response.data);
                      const anchor = document.createElement("a");
                      anchor.href = url;
                      anchor.download = `${sid}.zip`;
                      anchor.click();
                      URL.revokeObjectURL(url);
                    })
                  }
                >
                  Export complete experiment ZIP
                </Button>
              </div>
              {!run && (
                <p>
                  No completed run yet. Open Run to score the four conditions.
                </p>
              )}
              {run?.status === "failed" && (
                <p role="alert" className="text-red-400">
                  Failed run: {run.error}. Partial traces remain in the export;
                  do not interpret them as a completed comparison.
                </p>
              )}
              {run?.report && (
                <>
                  <p className="text-sm">
                    {run.confirmatory
                      ? "First registered holdout evaluation"
                      : "Exploratory evaluation"}{" "}
                    · {run.report.pairs} intents · {run.report.clusters}{" "}
                    independent source groups ·{" "}
                    {Math.round(run.report.confidence * 100)}% cluster bootstrap
                    intervals
                  </p>
                  <div className="grid gap-3 md:grid-cols-4">
                    {cells.map((cell) => (
                      <Panel key={cell} title={labels[cell]}>
                        <p className="text-3xl font-semibold">
                          {(run.report!.metrics[cell].mean * 100).toFixed(1)}%
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Hit@{study.k}
                        </p>
                      </Panel>
                    ))}
                  </div>
                  <Panel title="Paired contrasts">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr>
                            <th className="p-2">Contrast</th>
                            <th>Difference</th>
                            <th>Confidence interval</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            "bm25_gap",
                            "dense_gap",
                            "jo_gain",
                            "msa_gain",
                            "gap_change",
                          ].map((key) => {
                            const m = run.report!.metrics[key];
                            return (
                              <tr
                                key={key}
                                className="border-t border-white/10"
                              >
                                <td className="p-2">
                                  {labels[key]}{" "}
                                  {study.primary === key && "· primary"}
                                </td>
                                <td>{(m.mean * 100).toFixed(1)} pp</td>
                                <td>
                                  {m.low === null
                                    ? "Insufficient source groups"
                                    : `${(m.low * 100).toFixed(1)} to ${(m.high! * 100).toFixed(1)} pp`}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="mt-4 text-sm">
                      Primary practical threshold:{" "}
                      {run.report.threshold_supported
                        ? "supported by this interval"
                        : "not established by this interval"}
                      .{" "}
                      {run.confirmatory
                        ? "Interpret within the sampled task."
                        : "This is not a confirmatory conclusion."}
                    </p>
                    <ul className="mt-3 list-disc pl-4 text-xs text-muted-foreground">
                      {run.report.warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  </Panel>
                  <Panel title="Inspect an intent across all four conditions">
                    <div className="mb-3 flex items-center gap-3">
                      <Button
                        disabled={rowIndex === 0}
                        onClick={() => setRowIndex((i) => i - 1)}
                      >
                        Previous
                      </Button>
                      <span>
                        {Math.min(rowIndex + 1, run.rows.length)} /{" "}
                        {run.rows.length}
                      </span>
                      <Button
                        disabled={rowIndex >= run.rows.length - 1}
                        onClick={() => setRowIndex((i) => i + 1)}
                      >
                        Next
                      </Button>
                    </div>
                    {run.rows[rowIndex] && (
                      <>
                        <p className="mb-3 text-xs">
                          {run.rows[rowIndex].pair_id} · Relevant passages:{" "}
                          {Object.keys(run.rows[rowIndex].qrels).join(", ")}
                        </p>
                        <div className="grid gap-4 md:grid-cols-2">
                          {cells.map((cell) => {
                            const c = run.rows[rowIndex][cell];
                            return (
                              <div
                                key={cell}
                                className="rounded-xl border border-white/10 p-3"
                              >
                                <h3 className="font-semibold">
                                  {labels[cell]} ·{" "}
                                  {c.hit ? `hit at ${c.rank}` : "miss"}
                                </h3>
                                <p className="my-2" dir="auto">
                                  {c.query}
                                </p>
                                <ol className="space-y-1 text-xs">
                                  {c.ranked.map((hit) => (
                                    <li key={hit.doc_id}>
                                      {hit.rank}. {hit.doc_id}{" "}
                                      {run.rows[rowIndex].qrels[hit.doc_id]
                                        ? "✓ relevant"
                                        : ""}
                                      {hit.excerpt && <p dir="auto" className="my-2 text-muted-foreground">{hit.excerpt}</p>}
                                    </li>
                                  ))}
                                </ol>
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                  </Panel>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
