import platform
import time
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np

from . import ENGINE_VERSION
from .metrics import METRICS, aggregate, paired_bootstrap, retrieval_metrics
from .normalization import diagnostic_hypotheses, normalize
from .retrieval import BM25
from .schemas import Dataset, ExperimentRequest


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def run_experiment(dataset_record: dict, request: ExperimentRequest) -> dict:
    started = time.perf_counter()
    dataset = Dataset.model_validate(dataset_record["data"])
    index = BM25(dataset.documents, request.config)
    rows = []
    docs = {d.id: d for d in dataset.documents}
    for query in dataset.queries:
        ranking = index.search(query.question)
        rows.append(
            {
                "query_id": query.id,
                "question": query.question,
                "normalized_question": normalize(
                    query.question, request.config.query_normalization
                ),
                "expected_answer": query.expected_answer,
                "qrels": query.qrels,
                "metadata": query.metadata,
                "ranking": ranking,
                "metrics": retrieval_metrics(
                    [r["doc_id"] for r in ranking], query.qrels, request.config.k
                ),
                "hypotheses": diagnostic_hypotheses(
                    query.question,
                    " ".join(docs[d].text for d, g in query.qrels.items() if g),
                    request.config.model_dump(),
                ),
            }
        )
    return {
        "id": str(uuid4()),
        "name": request.name,
        "dataset_id": dataset_record["id"],
        "dataset_hash": dataset_record["hash"],
        "config": request.config.model_dump(),
        "engine_version": ENGINE_VERSION,
        "created_at": timestamp(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "metrics": aggregate(rows),
        "scored_queries": sum(r["metrics"] is not None for r in rows),
        "excluded_queries": sum(r["metrics"] is None for r in rows),
        "rows": rows,
    }


def compare(baseline: dict, candidate: dict) -> dict:
    if baseline["id"] == candidate["id"]:
        raise ValueError("Choose two different experiments")
    if baseline["dataset_hash"] != candidate["dataset_hash"]:
        raise ValueError("Comparisons require the same immutable dataset version")
    if baseline["config"]["k"] != candidate["config"]["k"]:
        raise ValueError("Comparisons require the same K cutoff")
    if baseline["engine_version"] != candidate["engine_version"]:
        raise ValueError("Comparisons require the same metric engine version")
    candidates = {r["query_id"]: r for r in candidate["rows"]}
    rows = []
    for base in baseline["rows"]:
        cand = candidates[base["query_id"]]
        deltas = (
            {m: cand["metrics"][m] - base["metrics"][m] for m in METRICS}
            if base["metrics"] is not None and cand["metrics"] is not None
            else None
        )
        status = (
            "excluded"
            if deltas is None
            else (
                "regressed"
                if deltas["ndcg"] < -1e-12
                else "improved"
                if deltas["ndcg"] > 1e-12
                else "unchanged"
            )
        )
        rows.append(
            {
                "query_id": base["query_id"],
                "question": base["question"],
                "baseline": base,
                "candidate": cand,
                "deltas": deltas,
                "status": status,
            }
        )
    summary = {}
    for metric in METRICS:
        deltas = [r["deltas"][metric] for r in rows if r["deltas"] is not None]
        summary[metric] = {
            "baseline": baseline["metrics"][metric],
            "candidate": candidate["metrics"][metric],
            "delta": sum(deltas) / len(deltas) if deltas else None,
            "bootstrap": paired_bootstrap(deltas),
        }
    return {
        "baseline": baseline,
        "candidate": candidate,
        "summary": summary,
        "counts": {
            s: sum(r["status"] == s for r in rows)
            for s in ("improved", "regressed", "unchanged", "excluded")
        },
        "rows": rows,
    }
