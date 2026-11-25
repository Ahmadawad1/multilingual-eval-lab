# Brainwave Eval — agent instructions

## Project Context
- Repository: `Ahmadawad1/multilingual-eval-lab`; default branch is `master`.
- Help AI engineering teams measure multilingual retrieval and RAG quality, compare runs, and diagnose regressions. The Arabic B2B demand hypothesis is unvalidated.
- Arabic-first, multilingual-ready. MVP: dataset import, BM25, normalization, deterministic metrics, paired comparisons, failure inspection, optional local generation/judging, reports.
- Exclude cloud hosting, paid APIs, authentication, billing, embedding pipelines, and distributed jobs. All runtime operation must be local and free.

## Technology and Architecture
- Stack: React/TypeScript/Vite + Tailwind CSS frontend; Python/FastAPI backend; SQLite JSON snapshots on the local filesystem; CPU BM25 and NumPy bootstrap. No model is required.
- `frontend/src/`: App workspace, FailureExplorer, JudgePanel and shared controls/styles. Native semantic forms keep dependencies small. English chrome, Arabic RTL content, light/dark modes.
- `backend/`: schemas/datasets validate imports; normalization/retrieval implement BM25; metrics/experiments score and compare; storage persists; inference adapts local models; reporting exports; replay verifies bundles; main serves API + built frontend.
- `tests/` covers correctness/integration; `examples/` contains synthetic import files; `scripts/` contains Windows helpers; ignored `data/` holds SQLite. UI calls same-origin `/api`; Vite proxies during development.
- Pipeline: validated immutable dataset → versioned configuration → ranked passages → per-query metrics → paired comparison → diagnosis/report.
- Optional inference accepts only loopback Ollama or OpenAI-compatible endpoints; record configuration, model identity, rubric, raw judgments and human reviews. No local model was installed during implementation; do not claim GPU inference was tested.
- Trade-off: bounded synchronous local experiments keep operations simple; avoid premature services and abstractions.

## Engineering Principles
- Prefer simplicity, correctness, maintainability and focused independently testable modules; reuse existing conventions/components.
- Preserve existing work and backward compatibility where practical. Use clear naming and actionable errors.
- Never invent metrics, evaluation evidence, benchmark performance, or test outcomes.
- Never commit secrets, weights, caches, private data, or generated runtime artifacts.

## Git and Commit Standards
- Use Conventional Commits: `type(scope): short imperative description`.
- Allowed lowercase types: feat, fix, refactor, test, docs, chore, perf, build, ci.
- Examples: `feat(datasets): add JSONL import`; `fix(retrieval): preserve Arabic entities`; `test(metrics): cover empty rankings`.
- Keep commits focused; run relevant checks before committing. Avoid vague messages and unrelated changes.
- Do not force-push, rewrite shared history, or change the default branch without approval.

## Testing and Evaluation Integrity
- Verify metrics against hand-computed results, including empty results, graded labels and cutoff behavior.
- Test Arabic diacritics, Tatweel, Hamza, Alef Maqsura, Taa Marbuta and entity collisions.
- Record dataset hashes, full configurations, engine version, seeds and model identity for reproducibility.
- Label diagnoses as hypotheses. Confidence intervals do not establish generalization; never claim significance without evidence.
- LLM judgments are uncalibrated until compared against human labels. Keep human assessments separate.

## Development Workflow for AI Agents
1. Read this file and inspect relevant code.
2. Implement the smallest useful slice, following existing conventions.
3. Add meaningful tests for changes and run appropriate checks; do not hide failures.
4. Update documentation and these instructions when architecture/commands change.
5. Commit verified changes using Conventional Commits.
6. Summarize functionality, checks and remaining limitations honestly.

## Useful Project Commands
- Setup: `.\scripts\setup.ps1` or `uv sync --frozen`, `npm --prefix eval-ui ci`, `npm --prefix eval-ui run build`.
- Start: `.\scripts\start.ps1` (loads supported `.env` keys) → http://127.0.0.1:8000; Ctrl+C stops it.
- Backend dev: `.\scripts\start.ps1 -Reload`; frontend dev in another terminal: `npm --prefix frontend run dev` → port 5173.
- Optional inference after installing Ollama: `ollama serve`, then `ollama pull qwen3:4b` in a separate terminal; reuse an already running service. No model required for tests.
- Seed running API: `uv run python scripts/seed_demo.py`; or choose Load Arabic demo in UI.
- Tests: `uv run --frozen pytest -q`; full checks: `.\scripts\check.ps1`.
- Python lint/format: `uv run ruff check backend tests scripts`; `uv run ruff format backend tests scripts`.
- Frontend type check: `npm --prefix frontend run check`; formatting: `npm --prefix frontend run format` (or `format:check`); build: `npm --prefix frontend run build`.
- Verify exported JSON: `uv run python -m backend.replay path/to/evaluation.json`.
- Keep `uv.lock` and `frontend/package-lock.json` committed. Preserve localhost defaults and 12 MB request limits.

- Product name: Brainwave Eval; repository/package name remains multilingual-eval-lab.
- Visual identity: `EvidenceOrbit.tsx` and `identity.css`; user-provided logo in `frontend/public/brainwave-logo.png`, used only in the top-left brand. Keep reduced-motion and pause controls. Reference Brainwave for inspiration without copying code or private assets.
- RAGAS for generation (installed by Windows setup): `uv sync --extra ragas`; test with `uv run --extra ragas pytest -q`. `ragas_evaluation.py` uses official collections for faithfulness, answer relevancy, context precision, context recall and answer correctness via loopback transport, with telemetry disabled before import. Keep 0–1 scores distinct from retrieval metrics and 0–4 rubric/human labels. Preserve failed traces and null scores. No Arabic calibration claim.

## Standalone Brainwave Eval Lab
- The primary UI lives in `eval-ui/` and opens at `/evaluation/dataset`. Copying the local Brainwave Evaluation pages and their supporting code was explicitly requested. Keep the scope to Eval Lab and omit account screens.
- The reference evaluation engine is in `agent_hub/eval/` and runs under the same guarded FastAPI process at `/api/eval`. It stores its own artifacts in `data/evaluation/`. Serve Golden Sets as the sole evaluation UI. Keep the legacy SQLite APIs available for export and migration.
- Build the new client with `npm --prefix eval-ui ci` and `npm --prefix eval-ui run build`. Setup builds the Eval Lab client. Use `python scripts/start_eval_services.py` for the local Know Hub and Ollama dependencies from the sibling reference checkout. No Docker service needs public host ports.
- Run `uv run --extra ragas pytest -q` for the combined suites. Local model checks establish connectivity and call behavior only.
