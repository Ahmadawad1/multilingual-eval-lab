import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  Database,
  FileText,
  FlaskConical,
  GitCompareArrows,
  Layers3,
  Menu,
  MessageSquare,
  Moon,
  Play,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  Upload,
  X,
} from "lucide-react";
import { api, reportUrl } from "./api";
import {
  Badge,
  ConfigFields,
  defaultConfig,
  delta,
  Empty,
  Loading,
  MetricCards,
  score,
} from "./components";
import FailureExplorer from "./FailureExplorer";
import JudgePanel from "./JudgePanel";
import type {
  Comparison,
  Config,
  DatasetDetail,
  DatasetSummary,
  Experiment,
  Ranking,
} from "./types";

const navigation = [
  {
    name: "Overview",
    icon: Layers3,
    subtitle: "A clear view of retrieval quality.",
  },
  {
    name: "Dataset Lab",
    icon: Database,
    subtitle: "Good evaluation begins with trustworthy data.",
  },
  {
    name: "Experiment Lab",
    icon: FlaskConical,
    subtitle: "Change one thing. Measure what happens.",
  },
  {
    name: "Comparison",
    icon: GitCompareArrows,
    subtitle: "Measure the gains. Keep the regressions in view.",
  },
  {
    name: "Failure Explorer",
    icon: Search,
    subtitle: "From aggregate scores to passage-level evidence.",
  },
  {
    name: "Generation Review",
    icon: MessageSquare,
    subtitle: "Local model judgments, with a human in the loop.",
  },
  {
    name: "RAG Playground",
    icon: Play,
    subtitle: "Try a query against your local corpus.",
  },
  {
    name: "Reports",
    icon: FileText,
    subtitle: "Share the evidence and the uncertainty.",
  },
];

function configLabel(config: Config) {
  return `Query: ${config.query_normalization} · Corpus: ${config.corpus_normalization}`;
}

export default function App() {
  const [page, setPage] = useState("Overview");
  const [dark, setDark] = useState(
    () => localStorage.getItem("eval-theme") === "dark",
  );
  const [mobileNav, setMobileNav] = useState(false);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [baselineId, setBaselineId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [config, setConfig] = useState<Config>(defaultConfig);
  const [experimentName, setExperimentName] = useState("BM25 experiment");
  const [importName, setImportName] = useState("Imported Arabic dataset");
  const [importFormat, setImportFormat] = useState("json");
  const [importContent, setImportContent] = useState("");
  const [importLanguage, setImportLanguage] = useState("ar");
  const [querySearch, setQuerySearch] = useState("");
  const [judgeQuery, setJudgeQuery] = useState("");
  const [playQuestion, setPlayQuestion] = useState("اجراءات السفر");
  const [playConfig, setPlayConfig] = useState<Config>({
    ...defaultConfig,
    query_normalization: "aggressive",
    corpus_normalization: "aggressive",
  });
  const [generate, setGenerate] = useState(false);
  const [playResult, setPlayResult] = useState<{
    passages: (Ranking & { text: string })[];
    generation: { raw: string; config: { model: string } } | null;
  } | null>(null);
  const [inference, setInference] = useState<{
    connected: boolean;
    model_available: boolean;
    config?: { model: string; provider: string };
    message?: string;
  } | null>(null);

  const available = experiments.filter((e) => e.dataset_id === datasetId);
  const baseline = available.find((e) => e.id === baselineId);
  const candidates = available.filter(
    (e) => e.id !== baselineId && e.config.k === baseline?.config.k,
  );
  const activeDataset = datasets.find((d) => d.id === datasetId);
  const currentPage = navigation.find((n) => n.name === page)!;
  const needsComparison = [
    "Comparison",
    "Failure Explorer",
    "Reports",
    "Generation Review",
  ].includes(page);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("eval-theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [page]);

  async function refresh() {
    const [ds, runs] = await Promise.all([
      api<DatasetSummary[]>("/datasets"),
      api<Experiment[]>("/experiments"),
    ]);
    setDatasets(ds);
    setExperiments(runs);
    setDatasetId((previous) => previous || ds[0]?.id || "");
    return { ds, runs };
  }
  useEffect(() => {
    void refresh()
      .catch((e) => setError(String(e)))
      .finally(() => setInitialLoading(false));
  }, []);
  useEffect(() => {
    let active = true;
    setDataset(null);
    setPlayResult(null);
    if (datasetId)
      void api<DatasetDetail>(`/datasets/${datasetId}`)
        .then((d) => {
          if (active) setDataset(d);
        })
        .catch((e) => {
          if (active) setError(String(e));
        });
    return () => {
      active = false;
    };
  }, [datasetId]);
  useEffect(() => {
    const valid = experiments.filter((e) => e.dataset_id === datasetId);
    setBaselineId((previous) =>
      valid.some((e) => e.id === previous) ? previous : valid.at(-1)?.id || "",
    );
  }, [datasetId, experiments]);
  useEffect(() => {
    const base = experiments.find((e) => e.id === baselineId);
    const valid = experiments.filter(
      (e) =>
        e.dataset_id === datasetId &&
        e.id !== baselineId &&
        e.config.k === base?.config.k,
    );
    setCandidateId((previous) =>
      valid.some((e) => e.id === previous) ? previous : valid[0]?.id || "",
    );
  }, [baselineId, datasetId, experiments]);
  useEffect(() => {
    let active = true;
    setComparison(null);
    if (!baselineId || !candidateId) {
      setComparisonLoading(false);
      return;
    }
    setComparisonLoading(true);
    void api<Comparison>(
      `/comparison?${new URLSearchParams({ baseline: baselineId, candidate: candidateId })}`,
    )
      .then((c) => {
        if (active) setComparison(c);
      })
      .catch((e) => {
        if (active) setError(String(e));
      })
      .finally(() => {
        if (active) setComparisonLoading(false);
      });
    return () => {
      active = false;
    };
  }, [baselineId, candidateId]);

  async function run(task: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  async function demo() {
    await run(async () => {
      const result = await api<{
        dataset_id: string;
        baseline_id: string;
        candidate_id: string;
      }>("/demo", {});
      await refresh();
      setDatasetId(result.dataset_id);
      setBaselineId(result.baseline_id);
      setCandidateId(result.candidate_id);
      setPage("Comparison");
      setNotice(
        "Synthetic dataset loaded. All three BM25 configurations have measured results.",
      );
    });
  }
  function navigate(name: string) {
    setPage(name);
    setMobileNav(false);
    setNotice("");
    setError("");
  }

  const comparisonControls = (
    <div className="comparison-controls">
      <label>
        <span>
          <i className="legend-dot baseline" />
          Baseline
        </span>
        <select
          value={baselineId}
          onChange={(e) => setBaselineId(e.target.value)}
          disabled={!available.length}
        >
          <option value="" disabled>
            Select baseline
          </option>
          {available.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name} · K={e.config.k}
            </option>
          ))}
        </select>
      </label>
      <div className="versus">vs</div>
      <label>
        <span>
          <i className="legend-dot candidate" />
          Candidate
        </span>
        <select
          value={candidateId}
          onChange={(e) => setCandidateId(e.target.value)}
          disabled={!candidates.length}
        >
          <option value="" disabled>
            Select candidate
          </option>
          {candidates.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name} · K={e.config.k}
            </option>
          ))}
        </select>
      </label>
      <div className="comparison-note">
        <ShieldCheck size={18} />
        <span>
          Same dataset & cutoff
          <br />
          <strong>Paired query evaluation</strong>
        </span>
      </div>
    </div>
  );

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            ع<span>∙</span>
          </div>
          <div>
            Multilingual<span>Eval Lab</span>
          </div>
          <button
            className="icon-button mobile-close"
            onClick={() => setMobileNav(false)}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>
        <div className="workspace-label">
          <span className="workspace-icon">M</span>
          <div>
            Local workspace<small>Personal environment</small>
          </div>
          <Badge>v0.1</Badge>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              aria-current={page === name ? "page" : undefined}
              onClick={() => navigate(name)}
            >
              <Icon size={19} />
              <span>{name}</span>
              {name === "Failure Explorer" &&
                comparison &&
                comparison.counts.regressed > 0 && (
                  <span className="nav-count">
                    {comparison.counts.regressed}
                  </span>
                )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={20} />
            <div>
              <strong>Local by design</strong>
              <p>
                Your data stays on this machine.
                <br />
                No paid API required.
              </p>
            </div>
          </div>
          <button className="theme-switch" onClick={() => setDark(!dark)}>
            {dark ? <Sun size={18} /> : <Moon size={18} />}
            <span>{dark ? "Light appearance" : "Dark appearance"}</span>
          </button>
          <div className="sidebar-footer">
            <span className="avatar">ML</span>
            <div>
              Arabic-first. Multilingual-ready.
              <small>Open source · Apache 2.0</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              onClick={() => setMobileNav(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div className="topbar-right">
            <span className="local-indicator" />
            Local mode
            <span className="topbar-divider" />
            <span className="language-label">ع / EN</span>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">MULTILINGUAL EVALUATION WORKSPACE</div>
              <h1>{page}</h1>
              <p>{currentPage.subtitle}</p>
            </div>
            <div className="heading-actions">
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => void demo()}
              >
                <Sparkles size={16} />
                {busy
                  ? "Working…"
                  : datasets.length
                    ? "Load Arabic demo"
                    : "Start with Arabic demo"}
              </button>
              {comparison && (
                <a
                  className="button primary"
                  href={reportUrl(baselineId, candidateId, "json")}
                  download
                >
                  <ArrowDownToLine size={16} />
                  Export results
                </a>
              )}
            </div>
          </div>
          {error && (
            <div className="alert error" role="alert">
              <strong>Couldn’t complete that action.</strong>
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={18} />
              </button>
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              <Check size={18} />
              <span>{notice}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={18} />
              </button>
            </div>
          )}
          {busy && (
            <div className="work-indicator" role="status">
              <Activity size={16} />
              Processing locally… Model requests may take up to two minutes.
            </div>
          )}
          {initialLoading ? (
            <Loading text="Opening your local workspace…" />
          ) : (
            <>
              {datasets.length > 0 && (
                <div className="dataset-context">
                  <Database size={17} />
                  <label htmlFor="active-dataset">Active dataset</label>
                  <select
                    id="active-dataset"
                    value={datasetId}
                    onChange={(e) => {
                      setDatasetId(e.target.value);
                      setBaselineId("");
                      setCandidateId("");
                      setComparison(null);
                    }}
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                  <Badge>{activeDataset?.language.toUpperCase()}</Badge>
                  <span className="dataset-counts">
                    {activeDataset?.query_count} queries ·{" "}
                    {activeDataset?.document_count} passages
                  </span>
                </div>
              )}

              {page === "Overview" && (
                <>
                  <div className="welcome-panel">
                    <div>
                      <Badge tone="teal">EVIDENCE BEFORE RELEASES</Badge>
                      <h2>
                        Know where your
                        <br />
                        retrieval gets lost.
                      </h2>
                      <p>
                        Compare configurations, investigate Arabic language edge
                        cases, and turn evaluation into an informed release
                        decision.
                      </p>
                      <button
                        className="button primary"
                        disabled={busy}
                        onClick={() =>
                          comparison
                            ? navigate("Failure Explorer")
                            : void demo()
                        }
                      >
                        {comparison
                          ? "Explore query-level failures"
                          : "Run the synthetic Arabic demo"}
                        <Search size={17} />
                      </button>
                    </div>
                    <div className="welcome-visual" aria-hidden="true">
                      <div className="arabic-glyphs">
                        <span>أ</span>
                        <span>ا</span>
                        <span>إ</span>
                      </div>
                      <div className="visual-rule" />
                      <div className="visual-label">
                        ONE FOLD. DIFFERENT OUTCOMES.
                      </div>
                      <div className="visual-tags">
                        <span>better recall</span>
                        <span>entity collisions</span>
                      </div>
                    </div>
                  </div>
                  <div className="overview-stats">
                    <article>
                      <Database size={20} />
                      <div>
                        <strong>{datasets.length}</strong>
                        <span>Versioned datasets</span>
                      </div>
                    </article>
                    <article>
                      <FlaskConical size={20} />
                      <div>
                        <strong>{experiments.length}</strong>
                        <span>Measured experiments</span>
                      </div>
                    </article>
                    <article>
                      <BookOpen size={20} />
                      <div>
                        <strong>{activeDataset?.query_count ?? 0}</strong>
                        <span>Queries in active dataset</span>
                      </div>
                    </article>
                    <article>
                      <Activity size={20} />
                      <div>
                        <strong>{comparison?.counts.regressed ?? "—"}</strong>
                        <span>Selected-pair regressions</span>
                      </div>
                    </article>
                  </div>
                  {comparison && (
                    <>
                      <div className="section-heading">
                        <div>
                          <h2>Current comparison</h2>
                          <p>
                            {comparison.baseline.name} vs{" "}
                            {comparison.candidate.name}
                          </p>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => navigate("Comparison")}
                        >
                          View comparison
                        </button>
                      </div>
                      <MetricCards comparison={comparison} />
                    </>
                  )}
                  <section className="panel">
                    <div className="panel-title">
                      <h2>Recent experiments</h2>
                      <button
                        className="text-button"
                        onClick={() => navigate("Experiment Lab")}
                      >
                        Open Experiment Lab
                      </button>
                    </div>
                    {!experiments.length ? (
                      <Empty title="Your first baseline starts here">
                        Import your own dataset or load the labeled synthetic
                        demo.
                      </Empty>
                    ) : (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Experiment</th>
                              <th>Configuration</th>
                              <th>Recall@K</th>
                              <th>NDCG@K</th>
                              <th>Runtime</th>
                            </tr>
                          </thead>
                          <tbody>
                            {experiments.slice(0, 6).map((e) => (
                              <tr key={e.id}>
                                <td>
                                  <strong>{e.name}</strong>
                                  <small>
                                    {new Date(e.created_at).toLocaleString()}
                                  </small>
                                </td>
                                <td>
                                  {configLabel(e.config)}
                                  <small>K={e.config.k}</small>
                                </td>
                                <td>{score(e.metrics.recall)}</td>
                                <td>{score(e.metrics.ndcg)}</td>
                                <td>{e.duration_ms} ms</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>
                </>
              )}

              {page === "Dataset Lab" && (
                <>
                  <div className="two-column">
                    <section className="panel">
                      <div className="panel-title">
                        <h2>Import an evaluation dataset</h2>
                        <Badge>JSON · JSONL · CSV</Badge>
                      </div>
                      <p className="muted">
                        Include passages, questions and document-level relevance
                        judgments. Imports create immutable, content-hashed
                        versions.
                      </p>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          void run(async () => {
                            const result = await api<DatasetDetail>(
                              "/datasets/import",
                              {
                                name: importName,
                                language: importLanguage,
                                format: importFormat,
                                content: importContent,
                              },
                            );
                            await refresh();
                            setDatasetId(result.id);
                            setNotice(
                              "Dataset validated and saved locally. You can now run a baseline.",
                            );
                            setImportContent("");
                          });
                        }}
                      >
                        <div className="form-grid">
                          <label>
                            Dataset name (JSONL / CSV)
                            <input
                              required
                              maxLength={120}
                              value={importName}
                              onChange={(e) => setImportName(e.target.value)}
                            />
                          </label>
                          <label>
                            Format
                            <select
                              value={importFormat}
                              onChange={(e) => setImportFormat(e.target.value)}
                            >
                              {["json", "jsonl", "csv"].map((f) => (
                                <option key={f}>{f}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Language (JSONL / CSV)
                            <input
                              required
                              minLength={2}
                              maxLength={35}
                              value={importLanguage}
                              onChange={(e) =>
                                setImportLanguage(e.target.value)
                              }
                            />
                          </label>
                        </div>
                        <label className="upload-zone">
                          <Upload size={22} />
                          <strong>Choose a local dataset file</strong>
                          <span>Up to 10 MB · UTF-8 encoded</span>
                          <input
                            type="file"
                            accept=".json,.jsonl,.csv"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file)
                                void run(async () => {
                                  if (file.size > 10_000_000)
                                    throw new Error(
                                      "Dataset file exceeds 10 MB",
                                    );
                                  setImportContent(await file.text());
                                  const ext = file.name.split(".").pop();
                                  if (
                                    ext &&
                                    ["json", "jsonl", "csv"].includes(ext)
                                  )
                                    setImportFormat(ext);
                                });
                            }}
                          />
                        </label>
                        <label>
                          Or paste dataset content
                          <textarea
                            className="code-input"
                            rows={7}
                            required
                            value={importContent}
                            onChange={(e) => setImportContent(e.target.value)}
                            placeholder={
                              '{"name":"My dataset","documents":[…],"queries":[…]}'
                            }
                          />
                        </label>
                        <button
                          className="button primary"
                          disabled={busy || !importContent}
                        >
                          <Upload size={16} />
                          Validate & import
                        </button>
                      </form>
                    </section>
                    <section className="panel schema-panel">
                      <div className="panel-title">
                        <h2>A small, explicit schema</h2>
                        <BookOpen size={19} />
                      </div>
                      <p>
                        Relevance grades: <strong>0</strong> irrelevant,{" "}
                        <strong>1–3</strong> increasingly relevant. Unknown
                        passage IDs and duplicate IDs are rejected.
                      </p>
                      <pre>
                        {JSON.stringify(
                          {
                            name: "Arabic support",
                            language: "ar",
                            documents: [
                              { id: "d1", text: "الدعم متاح صباحا." },
                            ],
                            queries: [
                              {
                                id: "q1",
                                question: "الدعم",
                                expected_answer: "الدعم متاح صباحا.",
                                qrels: { d1: 3 },
                                metadata: { category: "support" },
                              },
                            ],
                          },
                          null,
                          2,
                        )}
                      </pre>
                      <p>
                        For JSONL or CSV, use one <code>type=document</code> or{" "}
                        <code>type=query</code> record per row. Encode{" "}
                        <code>qrels</code> and <code>metadata</code> as JSON
                        objects. CSV uses a union of fields; leave unused cells
                        empty.
                      </p>
                      <a
                        className="button secondary"
                        href="/api/demo/dataset"
                        download="arabic-demo.json"
                      >
                        Download example JSON
                      </a>
                      <p className="muted">
                        Limits: 10,000 passages, 1,000 queries, 20,000
                        characters per text, 8 million corpus characters.
                        Requests are limited to 12 MB.
                      </p>
                    </section>
                  </div>
                  {dataset && (
                    <section className="panel">
                      <div className="panel-title">
                        <h2>Dataset preview</h2>
                        <Badge tone="teal">Immutable version</Badge>
                      </div>
                      <p>{dataset.data.description}</p>
                      <p className="provenance">
                        <strong>Provenance:</strong> {dataset.data.source}
                      </p>
                      <p className="hash">SHA-256 {dataset.hash}</p>
                      <label className="search-control">
                        <Search size={16} />
                        <input
                          aria-label="Search dataset questions"
                          placeholder="Search dataset questions…"
                          value={querySearch}
                          onChange={(e) => setQuerySearch(e.target.value)}
                        />
                      </label>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Query ID</th>
                              <th>Question</th>
                              <th>Relevant passages</th>
                              <th>Category</th>
                            </tr>
                          </thead>
                          <tbody>
                            {dataset.data.queries
                              .filter((q) =>
                                `${q.id} ${q.question}`.includes(querySearch),
                              )
                              .slice(0, 100)
                              .map((q) => (
                                <tr key={q.id}>
                                  <td>
                                    <code>{q.id}</code>
                                  </td>
                                  <td className="arabic" dir="auto">
                                    {q.question}
                                  </td>
                                  <td>
                                    {
                                      Object.values(q.qrels).filter(
                                        (g) => g > 0,
                                      ).length
                                    }
                                  </td>
                                  <td>{String(q.metadata.category ?? "—")}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                      <small>
                        Preview shows up to 100 matching queries. Full records
                        are included in report exports.
                      </small>
                    </section>
                  )}
                </>
              )}

              {page === "Experiment Lab" && (
                <>
                  {!datasetId ? (
                    <Empty title="Import a dataset first">
                      Open Dataset Lab or load the Arabic demo to begin.
                    </Empty>
                  ) : (
                    <div className="two-column">
                      <section className="panel">
                        <div className="panel-title">
                          <h2>Configure a retrieval experiment</h2>
                          <Badge tone="teal">CPU · BM25</Badge>
                        </div>
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            void run(async () => {
                              const result = await api<Experiment>(
                                "/experiments",
                                {
                                  dataset_id: datasetId,
                                  name: experimentName,
                                  config,
                                },
                              );
                              await refresh();
                              if (baselineId) setCandidateId(result.id);
                              else setBaselineId(result.id);
                              setNotice(
                                `Experiment saved: ${result.scored_queries} scored, ${result.excluded_queries} excluded; ${result.duration_ms} ms.`,
                              );
                            });
                          }}
                        >
                          <label>
                            Experiment name
                            <input
                              required
                              maxLength={120}
                              value={experimentName}
                              onChange={(e) =>
                                setExperimentName(e.target.value)
                              }
                            />
                          </label>
                          <ConfigFields value={config} onChange={setConfig} />
                          <button className="button primary" disabled={busy}>
                            <Play size={16} />
                            Run experiment
                          </button>
                        </form>
                      </section>
                      <section className="panel normalization-guide">
                        <h2>Arabic normalization, explicitly</h2>
                        <div>
                          <Badge>None</Badge>
                          <p>
                            NFC Unicode normalization and case folding only.
                            Arabic spelling stays intact.
                          </p>
                          <span className="arabic" dir="rtl">
                            إِدارة ← إِدارة
                          </span>
                        </div>
                        <div>
                          <Badge tone="teal">Conservative</Badge>
                          <p>
                            Removes Arabic diacritics and Tatweel. Preserves
                            letter distinctions.
                          </p>
                          <span className="arabic" dir="rtl">
                            إِدارة ← إدارة
                          </span>
                        </div>
                        <div>
                          <Badge tone="amber">Aggressive</Badge>
                          <p>
                            Also folds Alef variants, Alef Maqsura and Taa
                            Marbuta. May merge names and distinct words.
                          </p>
                          <span className="arabic" dir="rtl">
                            إدارة ← اداره · على ← علي
                          </span>
                        </div>
                        <p className="muted">
                          Standalone Hamza and Hamza on waw/ya remain unchanged.
                          No stemming, stopword removal or morphological
                          analysis.
                        </p>
                      </section>
                    </div>
                  )}
                  <section className="panel">
                    <h2>Experiments on this dataset</h2>
                    {available.length ? (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Normalization</th>
                              <th>K</th>
                              <th>NDCG@K</th>
                              <th>Scored / excluded</th>
                              <th>Use as</th>
                            </tr>
                          </thead>
                          <tbody>
                            {available.map((e) => (
                              <tr key={e.id}>
                                <td>
                                  <strong>{e.name}</strong>
                                  <small>
                                    {e.id.slice(0, 8)} · {e.engine_version}
                                  </small>
                                </td>
                                <td>{configLabel(e.config)}</td>
                                <td>{e.config.k}</td>
                                <td>{score(e.metrics.ndcg)}</td>
                                <td>
                                  {e.scored_queries} / {e.excluded_queries}
                                </td>
                                <td>
                                  <button
                                    className="text-button"
                                    onClick={() => {
                                      setBaselineId(e.id);
                                      setPage("Comparison");
                                    }}
                                  >
                                    Baseline
                                  </button>
                                  <button
                                    className="text-button"
                                    disabled={
                                      e.id === baselineId ||
                                      (!!baseline &&
                                        e.config.k !== baseline.config.k)
                                    }
                                    onClick={() => {
                                      setCandidateId(e.id);
                                      setPage("Comparison");
                                    }}
                                  >
                                    Candidate
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <Empty title="No experiments yet">
                        Run an unnormalized baseline, then a candidate using the
                        same K.
                      </Empty>
                    )}
                  </section>
                </>
              )}

              {needsComparison && (
                <>
                  {comparisonControls}
                  {comparisonLoading ? (
                    <Loading text="Pairing query results and computing bootstrap intervals…" />
                  ) : !comparison ? (
                    <Empty title="Choose a baseline and a candidate">
                      Run two experiments on the same dataset with the same K,
                      or load the synthetic demo.
                    </Empty>
                  ) : (
                    <>
                      {page === "Comparison" && (
                        <>
                          <div className="section-heading">
                            <div>
                              <h2>A better average isn’t the whole story.</h2>
                              <p>
                                Macro-averaged over{" "}
                                {comparison.baseline.scored_queries} labeled
                                queries · {comparison.baseline.excluded_queries}{" "}
                                excluded · K={comparison.baseline.config.k}
                              </p>
                            </div>
                            <Badge tone="teal">Measured locally</Badge>
                          </div>
                          <MetricCards comparison={comparison} />
                          <div className="comparison-insights">
                            <section className="panel changes-panel">
                              <div className="panel-title">
                                <h2>Query-level outcomes</h2>
                                <Badge>
                                  NDCG@{comparison.baseline.config.k}
                                </Badge>
                              </div>
                              <div
                                className="outcome-bar"
                                aria-label="Query outcome distribution"
                              >
                                {(
                                  [
                                    "improved",
                                    "unchanged",
                                    "regressed",
                                    "excluded",
                                  ] as const
                                ).map((s) => (
                                  <span
                                    key={s}
                                    className={s}
                                    style={{ flex: comparison.counts[s] }}
                                    title={`${s}: ${comparison.counts[s]}`}
                                  />
                                ))}
                              </div>
                              <div className="outcome-stats">
                                {(
                                  [
                                    "improved",
                                    "unchanged",
                                    "regressed",
                                    "excluded",
                                  ] as const
                                ).map((s) => (
                                  <div key={s}>
                                    <strong
                                      className={
                                        s === "regressed"
                                          ? "negative"
                                          : s === "improved"
                                            ? "positive"
                                            : ""
                                      }
                                    >
                                      {comparison.counts[s]}
                                    </strong>
                                    <span>{s}</span>
                                  </div>
                                ))}
                              </div>
                              <button
                                className="button secondary"
                                onClick={() => navigate("Failure Explorer")}
                              >
                                <Search size={16} />
                                Inspect query evidence
                              </button>
                            </section>
                            <section className="panel uncertainty-panel">
                              <div className="panel-title">
                                <h2>What the evidence can say</h2>
                                <CircleHelp size={19} />
                              </div>
                              <p>{comparison.summary.ndcg.bootstrap.caution}</p>
                              <p>
                                Intervals use 2,000 paired query resamples with
                                seed 42. Gains and regressions reflect this
                                dataset; they do not establish production
                                readiness.
                              </p>
                              <div className="notice amber">
                                {activeDataset?.source
                                  .toLowerCase()
                                  .includes("synthetic")
                                  ? "Synthetic demonstration data. Use representative, independently labeled queries for release decisions."
                                  : "Confirm relevance-label coverage and query independence before interpreting uncertainty."}
                              </div>
                            </section>
                          </div>
                          <section className="panel">
                            <div className="panel-title">
                              <h2>Run configuration</h2>
                              <Badge>Reproducible</Badge>
                            </div>
                            <div className="table-wrap">
                              <table>
                                <thead>
                                  <tr>
                                    <th>Parameter</th>
                                    <th>Baseline</th>
                                    <th>Candidate</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {(
                                    Object.keys(
                                      defaultConfig,
                                    ) as (keyof Config)[]
                                  ).map((key) => (
                                    <tr key={key}>
                                      <td>{key.replaceAll("_", " ")}</td>
                                      <td>{comparison.baseline.config[key]}</td>
                                      <td
                                        className={
                                          comparison.baseline.config[key] !==
                                          comparison.candidate.config[key]
                                            ? "positive"
                                            : ""
                                        }
                                      >
                                        {comparison.candidate.config[key]}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            <p className="hash">
                              Dataset SHA-256 {activeDataset?.hash}
                            </p>
                          </section>
                        </>
                      )}
                      {page === "Failure Explorer" &&
                        (dataset ? (
                          <FailureExplorer
                            key={`${baselineId}:${candidateId}`}
                            comparison={comparison}
                            dataset={dataset}
                            onJudge={(row) => {
                              setJudgeQuery(row.query_id);
                              setPage("Generation Review");
                            }}
                          />
                        ) : (
                          <Loading />
                        ))}
                      {page === "Generation Review" && (
                        <JudgePanel
                          key={`${baselineId}:${candidateId}`}
                          comparison={comparison}
                          initialQuery={judgeQuery}
                          run={run}
                          busy={busy}
                        />
                      )}
                      {page === "Reports" && (
                        <div className="two-column">
                          <section className="panel report-panel">
                            <FileText size={32} />
                            <h2>The evidence, ready to share.</h2>
                            <p>
                              Export the selected comparison with genuine
                              results, uncertainty, diagnostic limitations, and
                              actionable recommendations.
                            </p>
                            <div className="report-downloads">
                              <a
                                href={reportUrl(
                                  baselineId,
                                  candidateId,
                                  "markdown",
                                )}
                                className="button primary"
                                download
                              >
                                <ArrowDownToLine size={17} />
                                Download Markdown report
                              </a>
                              <a
                                href={reportUrl(
                                  baselineId,
                                  candidateId,
                                  "json",
                                )}
                                className="button secondary"
                                download
                              >
                                <ArrowDownToLine size={17} />
                                Download reproducibility JSON
                              </a>
                            </div>
                            <p className="notice amber">
                              JSON exports contain your full dataset, supplied
                              answers and any model/human judgments. Review the
                              contents before sharing.
                            </p>
                          </section>
                          <section className="panel">
                            <h2>Included in your report</h2>
                            <ul className="check-list">
                              {[
                                "Dataset provenance, immutable hash and full source records (JSON)",
                                "Both experiment configurations and engine version",
                                "Aggregate metrics and per-query ranking evidence",
                                "Paired bootstrap intervals, seed and sample count",
                                "Observed regressions, limitations and recommendations",
                                "Recorded LLM judgments and separate human reviews (JSON)",
                              ].map((s) => (
                                <li key={s}>
                                  <Check size={17} />
                                  {s}
                                </li>
                              ))}
                            </ul>
                            <hr />
                            <h3>Current result</h3>
                            <p>
                              {comparison.counts.improved} improved ·{" "}
                              {comparison.counts.regressed} regressed ·{" "}
                              {comparison.counts.unchanged} unchanged
                            </p>
                            <p>
                              NDCG@{comparison.baseline.config.k} delta:{" "}
                              <strong>
                                {delta(comparison.summary.ndcg.delta)}
                              </strong>
                            </p>
                            <p className="muted">
                              Release recommendation: investigate regressions
                              and validate on a representative held-out set.
                            </p>
                          </section>
                        </div>
                      )}
                    </>
                  )}
                </>
              )}

              {page === "RAG Playground" &&
                (!datasetId ? (
                  <Empty title="A corpus is needed">
                    Import a dataset or load the Arabic demo.
                  </Empty>
                ) : (
                  <div className="two-column">
                    <section className="panel">
                      <div className="panel-title">
                        <h2>Ask your local corpus</h2>
                        <Badge>Supporting demo</Badge>
                      </div>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          void run(async () => {
                            setPlayResult(null);
                            setPlayResult(
                              await api("/playground", {
                                dataset_id: datasetId,
                                question: playQuestion,
                                config: playConfig,
                                generate,
                              }),
                            );
                          });
                        }}
                      >
                        <label>
                          Your question
                          <textarea
                            dir="auto"
                            required
                            maxLength={2000}
                            value={playQuestion}
                            onChange={(e) => {
                              setPlayQuestion(e.target.value);
                              setPlayResult(null);
                            }}
                          />
                        </label>
                        <ConfigFields
                          value={playConfig}
                          onChange={(value) => {
                            setPlayConfig(value);
                            setPlayResult(null);
                          }}
                        />
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={generate}
                            onChange={(e) => setGenerate(e.target.checked)}
                          />
                          Generate an answer with the configured local LLM
                        </label>
                        <button className="button primary" disabled={busy}>
                          <Play size={16} />
                          {generate
                            ? "Retrieve & generate"
                            : "Retrieve passages"}
                        </button>
                      </form>
                      <hr />
                      <div className="panel-title">
                        <h3>Optional inference</h3>
                        <button
                          className="text-button"
                          disabled={busy}
                          onClick={() =>
                            void run(async () =>
                              setInference(await api("/inference")),
                            )
                          }
                        >
                          Check local connection
                        </button>
                      </div>
                      {inference ? (
                        <p
                          className={
                            inference.connected && inference.model_available
                              ? "positive"
                              : "muted"
                          }
                        >
                          {inference.connected
                            ? `${inference.config?.provider} connected · ${inference.config?.model} ${inference.model_available ? "available" : "not installed"}`
                            : "No configured local model connection. Retrieval remains fully functional."}
                        </p>
                      ) : (
                        <p className="muted">
                          No model needed for retrieval. Configure Ollama or an
                          OpenAI-compatible loopback server in .env to enable
                          generation and judging.
                        </p>
                      )}
                    </section>
                    <section className="panel">
                      <h2>Retrieved evidence</h2>
                      {!playResult ? (
                        <Empty title="Explore the retrieval path">
                          Run a query to see ranked passages and optional
                          grounded generation.
                        </Empty>
                      ) : (
                        <>
                          {playResult.generation && (
                            <div className="generated-answer">
                              <Badge tone="amber">
                                Generated · {playResult.generation.config.model}{" "}
                                · unverified
                              </Badge>
                              <p className="arabic" dir="auto">
                                {playResult.generation.raw}
                              </p>
                            </div>
                          )}
                          {!playResult.passages.length && (
                            <Empty title="No matching passages">
                              Try another spelling or normalization
                              configuration.
                            </Empty>
                          )}
                          {playResult.passages.map((p) => (
                            <article className="passage" key={p.doc_id}>
                              <div className="passage-top">
                                <span className="rank">#{p.rank}</span>
                                <code>{p.doc_id}</code>
                              </div>
                              <p dir="auto" className="arabic">
                                {p.text}
                              </p>
                              <small>BM25 score {p.score.toFixed(4)}</small>
                            </article>
                          ))}
                        </>
                      )}
                    </section>
                  </div>
                ))}
            </>
          )}
          <footer className="main-footer">
            <span>
              <ShieldCheck size={14} />
              Local-first evaluation · No telemetry
            </span>
            <span>Scores are evidence, not a release verdict.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
