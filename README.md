# Brainwave Eval

Open [Golden Sets](http://127.0.0.1:8000/evaluation/dataset) for the standalone Brainwave evaluation workspace. The sidebar follows the reference lab through Golden Sets, Retrieval, Arabic Norm, Experiments, Stats Lab, Generation, Judge Lab, and Release Gate. A dataset version moves through Collect, Ask, Index, Judge, Gate, and Freeze. Both the built frontend and its API run on loopback without a login.

From the repo root on Windows:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

The service helper uses Docker Desktop and the sibling Brainwave checkout's evaluation configuration, installed Know Hub modules, and cached Ollama models. It runs a separate Compose project named `brainwave-eval-local` and binds Know Hub and Ollama to loopback. If these services are already available on the standard local ports (3002, 50052, 11434), start the app directly. For a first run, import the built-in English or Arabic golden set, open its Index tab, build the raw index, then open Retrieval and run a golden question. Arabic Norm can run BM25 using `examples/diagnostic-bundle.json` without Docker. Its optional dense experiment requires `uv sync --extra rerank` and the chosen encoder revision already in your local model cache.

Generation uses the official RAGAS metrics for faithfulness, answer relevancy, context precision, context recall and answer correctness. Windows setup installs the RAGAS extra. Start local Ollama with the configured judge model and install `nomic-embed-text` for relevancy and correctness. Each measurement saves its model responses. Undefined or failed measurements stay unscored. Generation comparisons require matching judge fingerprints, including the RAGAS version. For answerable, non-abstained items, the lab treats RAGAS answer correctness ≥ 0.75 as a pass. This is a local decision threshold and needs validation on your data. In Judge Lab → Validate, run RAGAS faithfulness against human grounding labels. The grounding check passes when every extracted claim is supported. Retrieval with qrels still runs without a model.

Golden Sets, runs, and release exports live in `data/evaluation`. The former workspace has been retired. Its SQLite data remains available through the legacy APIs for export. A JSON dataset returned in the `data` field of `GET /api/datasets/{id}` can be saved and imported under Golden Sets. Earlier runs remain in their original store.

## Run the Jordanian and MSA paired study

For an accessible Mr. TyDi Arabic pilot, run `uv run --with pyarrow python -m scripts.prepare_mrtydi` from the repository root. This downloads a pinned Arabic training shard and writes a seeded 50-question draft with shared passages to `data/mrtydi-ar-pilot/import-paired-draft.json`. Import this file through Golden Sets → Import labeled dataset (not the WANA adapter). `questions-only.jsonl` contains only opaque pair IDs, source questions and blank rewriting/review fields; use this file for passage-blind Jordanian authorship. Save edits in a separate file because rerunning preparation regenerates the outputs.

In Paired language study, replace each JO copy with a human-written or human-reviewed Jordanian equivalent; confirm that the original question is MSA, review qrels and record the reviewer. All pairs start unreviewed. The pilot searches the union of the sample's positive and BM25-sampled negative passages, not the full benchmark corpus; missing labels require review. `manifest.json` records source revision, hashes and selected query IDs. WANA's official downloads were returning 403 when checked on 26 November 2026, and its repository is archived.

Open [Paired language study](http://127.0.0.1:8000/evaluation/experiments/paired) from Retrieval Experiments. Follow **Data → Design → Run → Report**:

1. Import a labeled dataset or preview a Jordanian TyDi QA-WANA JSONL/JSON subset (below 11 MB). Review the generated candidate labels, write an equivalent MSA question and record the reviewer for each pair.
2. Assign source-connected dev/holdout splits and freeze the version. Both forms share labels and stay together; linked articles and passages cannot cross splits.
3. Start local Ollama and install `bge-m3` (or supported `nomic-embed-text`). Select the installed model, write the hypothesis and rationale, and choose the primary contrast, effect threshold, cutoff and confidence level. Save and register the protocol.
4. Run the four BM25/dense × MSA/Jordanian conditions on dev, then the registered holdout. Prior evaluated material requires an exploratory rerun reason. Failures remain in the history.
5. Inspect four-cell Hit@k, paired contrasts, source-cluster bootstrap intervals and ranked passages. Export the complete ZIP with protocol, data, model/index identity, all attempts and CSV results.

This workflow talks directly to loopback Ollama; Know Hub is not required. Both engines rank the same full passages. No silent truncation or automatic weight download is performed. Real dense execution requires a running local embedding model; automated tests use test doubles and do not establish GPU performance. The bounds are 500 pairs and 10,000 passages, with one active paired job.

Verify an exported archive with `uv run python scripts/replay_paired.py path/to/experiment.zip`. Replay checks checksums and recomputes point estimates from saved rankings; it does not rerun inference or validate bootstrap assumptions. The updated Word learning guide is in `experiments/02-jordanian-msa-retrieval/Golden Sets Experiment Guide.docx`.

## Import judgments and run local BM25

In **Golden Sets**, choose **Import labeled dataset** to import a JSON bundle with `documents`, `queries` and a `qrels` map per query. The importer also accepts the mixed-row JSONL and CSV formats in `examples/`. JSON bundles carry their language. For JSONL and CSV, set the language in the New dataset panel first. A complete import creates a new draft with all queries in the dev split.

To add or update labels on an existing draft, open **Ask → Items → Import qrels** and select a UTF-8 file. Use three columns (query ID, document ID, grade) or four TREC columns (query ID, iteration, document ID, grade). Grades range from 0 to 3. Grade 0 records a judged nonrelevant document. The file must reference queries and documents already present in the draft. Import updates the grades listed in the file and keeps the other judgments.

Open **Retrieval → Probe**, expand the configuration, and choose **Local BM25**. Then use **Score** to evaluate the dev split. Local BM25 builds its index in memory and uses the corpus document IDs for scoring. See the [Jordanian Arabic experiment guide](experiments/02-jordanian-msa-retrieval/Golden%20Sets%20Experiment%20Guide.docx) for a paired benchmark walkthrough.

## Legacy API reference

The commands and API examples below document the original SQLite backend and supporting components.


A local-first evaluation lab for measuring, comparing and diagnosing multilingual retrieval and RAG quality, starting with Arabic. Built for AI engineering teams investigating regressions before release. The B2B commercial hypothesis is unvalidated; this is a working prototype, not a validated benchmark or production SaaS.

**Dataset → Baseline → Experiment → Evaluation → Comparison → Failure diagnosis → Report**

No API key, subscription, GPU, model download or cloud account is needed for the core workflow. Runtime uses your own machine; installation needs internet for free packages, and optional models require a one-time download. Ordinary hardware/electricity costs are outside the zero-service-cost claim. No telemetry, remote fonts or hosted assets.

## Quick start — Windows 11

Prerequisites: Python 3.11+ (uv can provision Python), [uv](https://docs.astral.sh/uv/getting-started/installation/), and [Node.js](https://nodejs.org/) 22.12+ or 24 LTS. Verified here with uv 0.11.7, Python 3.12.13 and Node 24.14.0. A modern CPU and a few GB of available RAM suffice for the tiny demo; no large-corpus performance claim is made. The target 32 GB laptop has ample room for the deterministic demo.

From the repository root in PowerShell:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Open [Golden Sets](http://127.0.0.1:8000/evaluation/dataset) and follow the import workflow above. Stop the server with Ctrl+C.

If your environment does not permit PowerShell scripts, run the equivalent commands individually without changing your execution policy:

```powershell
uv sync --frozen
npm --prefix eval-ui ci
npm --prefix eval-ui run build
uv run --frozen --no-sync uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The last command does not load `.env`; set environment variables explicitly or use `start.ps1`. Copy `.env.example` to `.env` only if changing storage or optional inference settings. Do not expose this server publicly: it intentionally has no authentication or multi-user permissions.

### Development

Run `.\scripts\start.ps1 -Reload` for the backend. In another terminal, run `npm --prefix frontend run dev` and open [http://127.0.0.1:5173](http://127.0.0.1:5173). Vite proxies `/api` to port 8000. Production uses a single FastAPI process serving the compiled frontend; rebuild after frontend edits. Browser origins are restricted to loopback on 8000 and 5173.

## Five-minute customer demonstration

1. **Overview:** load the synthetic Arabic demo; explain that all results are computed locally.
2. **Comparison:** compare `BM25 · none` to `BM25 · aggressive`. Review Recall@5, Precision@5, MRR@5 and NDCG@5, macro-averaged over scored queries.
3. **Failure Explorer:** inspect the four NDCG regressions. In `q-entity-hiba`, aggressive normalization merges **هبة** and **هبه**, allowing a nonrelevant equal-score passage to rank first. Inspect both passage texts and grades. Similar traps cover Hamza and Alef Maqsura.
4. **Experiment Lab:** run conservative query and corpus normalization at K=5; compare it with the baseline. Try query-only normalization to expose a token-alignment failure.
5. **RAG Playground:** retrieve `اجراءات السفر` with aggressive normalization. No model is needed.
6. **Reports:** export Markdown and the JSON reproducibility bundle. Synthetic gains are not proof of customer value or production readiness.

To seed from the CLI while the app runs: `uv run python scripts/seed_demo.py`.

The tiny demo intentionally isolates spelling effects with short queries. Its names are fictional. It is authored for this repository under Apache-2.0, not a representative Arabic benchmark. Metric values are computed at execution time, never supplied as fixture scores.

## Dataset import

Upload or paste UTF-8 JSON, JSONL or CSV in Dataset Lab. Download the complete demo JSON through the UI or [the local demo endpoint](http://127.0.0.1:8000/api/demo/dataset). Small JSONL and CSV fixtures are in [`examples/`](examples/).

```json
{
  "name": "Arabic support evaluation",
  "language": "ar",
  "description": "Author-labeled support questions",
  "source": "Synthetic example; replace with actual provenance",
  "documents": [
    {"id": "d1", "title": "الدعم", "text": "الدعم متاح صباحا.", "metadata": {}}
  ],
  "queries": [
    {
      "id": "q1",
      "question": "الدعم",
      "expected_answer": "الدعم متاح صباحا.",
      "qrels": {"d1": 3},
      "metadata": {"category": "support"}
    }
  ]
}
```

- JSON uses its embedded name/language/provenance. JSONL/CSV use the import form's name/language; provenance defaults to user-supplied and unverified.
- JSONL: one object per line, with `type: "document"` or `type: "query"` and the matching fields above.
- CSV: `type,id,text,title,question,expected_answer,qrels,metadata`. Leave the other record type's cells empty. Encode `qrels` and `metadata` as quoted JSON objects.
- IDs are unique within documents or queries. Every judgment must reference an existing document. Grades are integers 0–3. Metadata is arbitrary JSON. Unexpected schema fields are rejected to catch typos.
- Grade **> 0** means relevant; grade 0 is explicitly nonrelevant. Unjudged documents count as nonrelevant for metrics and display as “Unjudged.” Incomplete judgments can bias scores.
- Queries without positive judgments are **excluded**, counted separately, and displayed without metrics. An entirely unscored run has null aggregate metrics.
- Limits: 10 MB upload UI, 12 MB actual HTTP body, 10,000 documents, 1,000 queries, 20,000 characters per passage/question, 8 million corpus characters. These are safety ceilings, not throughput guarantees.

Datasets are immutable snapshots keyed by SHA-256 over canonical validated JSON, including metadata, row order and provenance. Editing data means importing a new version. Identical imports are reused. Data remains in `data/lab.sqlite3` unless you export it yourself.

## Retrieval and metric semantics

BM25 indexes **document text only**, not titles. Tokenization uses Unicode word characters and Arabic combining marks. All modes apply NFC and case-folding. Query terms are deduplicated. No stemming, stopword removal, dense retrieval, reranking or morphological analysis is implemented. Only positive lexical matches are returned; no fabricated zero-score padding. Ties break by document ID in lexical order.

| Policy | Transformations |
|---|---|
| None | NFC + case-folding; preserves Arabic marks and letters |
| Conservative | Also removes Arabic diacritics/Quranic annotation marks and Tatweel |
| Aggressive | Also folds أ/إ/آ/ٱ → ا, ى → ي, ة → ه |

Standalone ء and Hamza on ؤ/ئ are preserved. Aggressive folding is deliberately lossy, not universally correct Arabic normalization. Query and corpus policies are independently configurable.

- **Recall@K:** retrieved relevant documents / all positively labeled documents.
- **Precision@K:** relevant documents in the first K / K, even when fewer than K matches exist.
- **MRR@K:** reciprocal rank of the first relevant result within K, or zero. Results beyond K are not measured.
- **NDCG@K:** DCG uses `(2^grade − 1) / log2(rank + 1)`, divided by ideal DCG from all supplied labels at K.

Aggregates are arithmetic means over scored queries. Outcome labels use NDCG delta; sorting supports any metric. NDCG can regress while recall remains unchanged.

Comparisons require distinct runs, identical dataset hashes, identical K and the same engine version. Paired bootstrap resamples **query deltas** 2,000 times with seed 42; percentile intervals are 95%, exploratory and unadjusted. Intervals are withheld below five scored queries. Constant deltas produce a degenerate interval warning. Query independence and representativeness cannot be inferred automatically. Correlated, repeated, synthetic or selected queries do not support generalization. No automatic significance badge or release gate is provided.

## Optional local inference

**Core evaluation requires none of this.** Initial inspection found an RTX 5070 Laptop GPU with about 8 GB VRAM, no Ollama/vLLM/llama.cpp executable on PATH, and no listener on the common 11434, 8000, 8080, 1234 or 5000 inference ports. No weights were installed during implementation. GPU inference performance and memory fit have not been measured here.

### Ollama

After installing [Ollama for Windows](https://ollama.com/download/windows):

```powershell
ollama serve
# In another terminal, if the model is not installed:
ollama pull qwen3:4b
```

Reuse the existing service if Ollama is already running. Defaults in `.env.example`:

```dotenv
LOCAL_LLM_PROVIDER=ollama
LOCAL_LLM_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=qwen3:4b
```

Restart the app after changing settings. Use **Check local connection** in RAG Playground; enable generation for answers with passage IDs. In **Generation Review**, choose a query with an expected answer and paste the answer to evaluate.

[Ollama's Qwen3 4B package](https://ollama.com/library/qwen3:4b) lists Q4_K_M quantization and a roughly 2.5 GB artifact. It is a reasonable starting candidate, **not a verified VRAM or latency guarantee**: runtime and KV cache also consume memory. The upstream [Qwen3-4B model card](https://huggingface.co/Qwen/Qwen3-4B) carries Apache-2.0. Keep context short and run one model request at a time; larger models/concurrent GPU workloads can exhaust 8 GB VRAM.

### Existing OpenAI-compatible local endpoints

Reuse a local llama.cpp, LM Studio or vLLM server supporting `/v1/models` and `/v1/chat/completions`:

```dotenv
LOCAL_LLM_PROVIDER=openai
LOCAL_LLM_URL=http://127.0.0.1:8080/v1
LOCAL_LLM_MODEL=the-exact-id-returned-by-models
```

Use your installed server's port/model ID. vLLM installation is out of scope; do not assume arbitrary CUDA builds support this GPU. Only HTTP loopback hosts are accepted. Proxies/redirects are disabled and no API key is sent. Configure the server itself for local inference: a loopback proxy does not prove that its upstream is local.

- Temperature 0, seed 42, up to 1,024 generated tokens, a 120-second request timeout and one simultaneous inference. Ollama uses 4,096 context tokens and non-thinking mode. Compatible servers use their configured context limits and may not honor seed identically.
- Payloads over 16,000 characters are rejected, not silently trimmed by this app. This is a size guard, **not a tokenizer-based context guarantee**. The server may reject/truncate oversized token contexts; keep inputs short.
- Correctness, faithfulness and relevance use explicit 0–4 rubrics in [`backend/inference.py`](backend/inference.py). This MVP requires an expected answer for judging.
- Evidence records include exact prompts, submitted answer, retrieved context, configuration, advertised model ID/digest (when available), raw output and rubric version. Invalid JSON/schema output retains raw evidence with no accepted scores.
- Human scores/notes are separate append-only records. No calibrated judge or inter-rater agreement analysis is claimed. Models can hallucinate, exhibit bias or follow malicious passage instructions.
- Both adapters are tested using mocked responses. No live local model result is claimed.

[BGE-M3](https://huggingface.co/BAAI/bge-m3) is a multilingual embedding candidate with an MIT model-card license. Embeddings/reranking are deferred until lexical failure modes and customer need are validated; hardware fit remains to be measured.

API references: [Ollama chat](https://docs.ollama.com/api/chat), [vLLM compatibility](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/), [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).

## Reports and replay

**Markdown** includes metric summaries, intervals, regressed query IDs, configuration, limitations and recommendations. **JSON** additionally contains the full dataset, rankings, per-query records, environment versions, optional model judgments and human reviews. Review exports before sharing: they contain supplied data and model endpoint configuration.

Recompute a downloaded bundle with the same locked engine:

```powershell
uv run python -m backend.replay C:\path\to\evaluation.json
```

The command verifies the dataset hash, re-runs both retrieval configurations, and compares per-query evidence and aggregate scores. Mismatches exit nonzero. It verifies deterministic retrieval, not model reproducibility or human labels. Timing, IDs and timestamps are intentionally not compared. Inference is never replayed automatically.

## Architecture

```text
frontend/src/             React + TypeScript + Vite + Tailwind CSS
  App.tsx                workspace, import, experiments, comparison, reports, playground
  FailureExplorer.tsx    paired rankings, relevance labels, hypotheses and filters
  JudgePanel.tsx         model judgments and independent human reviews
  components.tsx         shared semantic controls and metric cards
backend/
  schemas.py             validated dataset and API models
  datasets.py            JSON/JSONL/CSV parsing and hashes
  normalization.py       explicit Arabic policies and diagnostic hypotheses
  retrieval.py           CPU BM25 inverted index with stable tie-breaking
  metrics.py             metric formulas and NumPy paired bootstrap
  experiments.py         reproducible execution and compatible comparison
  storage.py             immutable JSON records in local SQLite
  inference.py           loopback adapters and versioned rubrics
  reporting.py           JSON evidence bundle and Markdown report
  replay.py              deterministic report verification CLI
  demo.py                authored synthetic source data, no stored scores
  main.py                bounded API, origin/host guards, static UI serving
scripts/                 Windows setup/start/check, demo seeding
tests/                   correctness and integration checks
examples/                small synthetic CSV/JSONL imports
data/                    ignored SQLite files, created at runtime
```

One process; no microservices, vector database or hosted runtime. Bounded synchronous experiments are serialized in-process. SQLite keeps full snapshots/results as JSON for inspectability, not high-volume analytics. The UI uses system fonts, native semantic form controls, light/dark themes, responsive navigation and automatic RTL direction for Arabic content. English interface chrome; full Arabic localization is deferred.

## Checks

```powershell
.\scripts\check.ps1
# Individual commands:
uv run --frozen pytest -q
uv run --frozen ruff check backend tests scripts
uv run --frozen ruff format --check backend tests scripts
npm --prefix frontend run format:check
npm --prefix frontend run build
# Apply formatting:
uv run ruff format backend tests scripts
npm --prefix frontend run format
```

Tests cover hand-calculated metrics/BM25, truncated MRR, empty rankings, missing labels, graded NDCG, Arabic edge cases, asymmetric normalization, entity collisions, all import formats, restart persistence, comparison guards, loopback restrictions, body limits, mocked inference, invalid judge output, human reviews and replay/tampering. GitHub CI uses the same checks without a model or paid API. Browser QA is separate, not an automated regression suite. The current upstream Starlette TestClient emits an httpx deprecation warning; tests still run and the warning is not suppressed.

## Known boundaries

- No authentication, billing, tenancy, distributed jobs, cancellation, dataset editing/deletion, production ingestion or persistent playground history. This is a localhost engineering lab.
- Imports/experiments use memory; accumulated runs can grow SQLite without quota or cleanup. Back up `data/` while the app is stopped. Runtime files are ignored by Git.
- No GPU benchmark, model provisioning, causal proof, power analysis, multiplicity correction or production release gate.
- Model tags may change. Ollama digests are recorded when available; compatible endpoints may expose only a mutable ID. Temperature zero does not guarantee cross-runtime reproducibility.
- Validate with representative Arabic corpora and labeled customer failures before expanding feature count.

The default branch remains `master`. Follow [`AGENTS.md`](AGENTS.md) and Conventional Commits. Code and authored demos are Apache-2.0; imported data and downloaded models retain their own licenses. Never commit customer data, credentials, weights or generated reports.


## Brainwave identity and optional RAGAS

Brainwave Eval has an original cyan/violet visual treatment inspired by the Brainwave reference: translucent panels, orbital motion, gradient accents and staggered entrances. The supplied Arabic-brain PNG appears only in the top-left product logo. No source code or private data was copied from the reference. Ambient motion has a pause toggle and respects reduced-motion preferences; light/dark modes remain available.

Enable RAGAS: `uv sync --extra ragas`, then restart the server. Run its integration tests with `uv run --extra ragas pytest -q`. Standard setup stays model-free; syncing without the extra can remove optional packages.

Generation Review offers RAGAS faithfulness (0–1) separately from the existing custom rubric (0–4). The real RAGAS collections scorer extracts claims and verifies them against retrieved passages using the existing loopback-only transport. No embeddings or reference answer are required. All prompts, schemas, outputs, model identity and package version are saved in JSON reports. Undefined results and invalid verdicts are unscored, never zero. Human review remains a separate 0–4 assessment. Telemetry is disabled before import. RAGAS English instructions have language-preservation guidance; Arabic reliability still needs human calibration. Two sequential local calls may each take up to 120 seconds. No live GPU judging is claimed.
