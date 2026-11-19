import math

import numpy as np

METRICS = ("recall", "precision", "mrr", "ndcg")


def retrieval_metrics(ranking: list[str], qrels: dict[str, int], k: int) -> dict | None:
    """All metrics are truncated at k. Unjudged documents count as nonrelevant.

    Queries with no positive judgments are excluded rather than assigned fake zeros.
    """
    if k < 1 or len(ranking) != len(set(ranking)):
        raise ValueError("k must be positive and rankings must contain unique IDs")
    relevant = {doc_id for doc_id, grade in qrels.items() if grade > 0}
    if not relevant:
        return None
    hits = [int(doc_id in relevant) for doc_id in ranking[:k]]
    dcg = sum(
        (2 ** qrels.get(doc_id, 0) - 1) / math.log2(i + 2) for i, doc_id in enumerate(ranking[:k])
    )
    ideal = sum(
        (2**grade - 1) / math.log2(i + 2)
        for i, grade in enumerate(sorted(qrels.values(), reverse=True)[:k])
    )
    return {
        "recall": sum(hits) / len(relevant),
        "precision": sum(hits) / k,
        "mrr": next((1 / (i + 1) for i, hit in enumerate(hits) if hit), 0),
        "ndcg": dcg / ideal,
    }


def aggregate(rows: list[dict]) -> dict:
    scored = [row["metrics"] for row in rows if row["metrics"] is not None]
    return {
        key: sum(row[key] for row in scored) / len(scored) if scored else None for key in METRICS
    }


def paired_bootstrap(deltas: list[float], seed: int = 42, samples: int = 2000) -> dict:
    """Percentile paired query bootstrap; small samples intentionally have no CI."""
    n = len(deltas)
    result = {
        "n": n,
        "seed": seed,
        "resamples": samples,
        "confidence": 0.95,
        "method": "paired query percentile bootstrap",
        "interval": None,
    }
    if n < 5:
        return {**result, "caution": "Fewer than 5 scored queries; interval withheld."}
    values = np.asarray(deltas, dtype=float)
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, n, size=(samples, n))].mean(axis=1)
    interval = np.quantile(means, [0.025, 0.975]).tolist()
    return {
        **result,
        "interval": interval,
        "caution": "Exploratory, unadjusted intervals assume independent representative queries. "
        "Small, synthetic, repeated or correlated queries cannot establish release quality."
        + (" Degenerate interval: no observed variation." if interval[0] == interval[1] else ""),
    }
