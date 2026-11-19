# Multilingual Eval Lab — agent instructions

## Project Context
- Repository: `Ahmadawad1/multilingual-eval-lab`; default branch is `master`.
- Help AI engineering teams measure multilingual retrieval and RAG quality, compare runs, and diagnose regressions. The Arabic B2B demand hypothesis is unvalidated.
- Arabic-first, multilingual-ready. MVP: dataset import, BM25, normalization, deterministic metrics, paired comparisons, failure inspection, optional local generation/judging, reports.
- Exclude cloud hosting, paid APIs, authentication, billing, embedding pipelines, and distributed jobs. All runtime operation must be local and free.

## Technology and Architecture
- Bootstrap state: repository began with README and Apache-2.0 license only. Update this section as modules land.
- Target stack: React/TypeScript/Vite frontend, Python/FastAPI backend, SQLite metadata and local filesystem, CPU BM25. No model is required.
- Keep datasets, normalization/retrieval, metrics, experiments, persistence, inference and reporting in focused backend modules. UI calls a same-origin `/api`.
- Pipeline: validated immutable dataset → versioned configuration → ranked passages → per-query metrics → paired comparison → diagnosis/report.
- Optional inference accepts only loopback Ollama or OpenAI-compatible endpoints; record configuration, model identity, rubric, raw judgments and human reviews.
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
- Commands will be documented here as executable entrypoints are added; do not present unimplemented commands as available.
