import json

from .metrics import METRICS

LIMITATIONS = [
    "BM25 is lexical retrieval without stemming, embeddings or reranking; titles are not indexed.",
    "Unjudged passages count as nonrelevant. Queries without positive labels are excluded.",
    "Recall, precision, reciprocal rank and NDCG are all truncated at the configured K.",
    "Bootstrap intervals are exploratory and unadjusted for multiple comparisons; queries must be "
    "independent and representative. Synthetic examples cannot validate a release.",
    "Normalization failure causes are hypotheses, not automatic causal determinations.",
    "LLM judgments are optional, uncalibrated and vulnerable to bias and prompt injection; "
    "human reviews are stored separately. Generation quality is not measured by retrieval metrics.",
]


def report_bundle(comparison: dict, dataset: dict, judgments: list, reviews: list) -> dict:
    ids = {comparison["baseline"]["id"], comparison["candidate"]["id"]}
    relevant_judgments = [j for j in judgments if j["experiment_id"] in ids]
    judgment_ids = {j["id"] for j in relevant_judgments}
    regressions = comparison["counts"]["regressed"]
    return {
        "schema_version": 1,
        "comparison": comparison,
        "dataset": dataset,
        "judgments": relevant_judgments,
        "human_reviews": [r for r in reviews if r["judgment_id"] in judgment_ids],
        "limitations": LIMITATIONS,
        "recommendations": [
            f"Review the {regressions} observed NDCG regressions and confirm relevance labels.",
            "Check named-entity collisions before enabling aggressive normalization.",
            "Validate on a representative held-out dataset before making a release decision.",
        ],
    }


def markdown_report(bundle: dict) -> str:
    comparison = bundle["comparison"]
    base, cand = comparison["baseline"], comparison["candidate"]

    # Escape user-authored text that could change Markdown structure.
    def safe(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = [
        "# Multilingual Eval Lab — evaluation report",
        "",
        f"Baseline: {safe(base['name'])} ({base['id']})",
        "",
        f"Candidate: {safe(cand['name'])} ({cand['id']})",
        "",
        f"Dataset: {safe(bundle['dataset']['data']['name'])}",
        "",
        f"Provenance: {safe(bundle['dataset']['data']['source'])}",
        "",
        f"SHA-256: `{base['dataset_hash']}` · Engine: `{base['engine_version']}`",
        "",
        f"Scored queries: {base['scored_queries']}; excluded: {base['excluded_queries']}.",
        "",
        "| Metric | Baseline | Candidate | Delta | 95% paired bootstrap CI |",
        "|---|---:|---:|---:|---|",
    ]
    for metric in METRICS:
        item = comparison["summary"][metric]
        fmt = lambda x: "N/A" if x is None else f"{x:.4f}"  # noqa: E731
        lines.append(
            f"| {metric.upper()}@{base['config']['k']} | {fmt(item['baseline'])} | "
            f"{fmt(item['candidate'])} | {fmt(item['delta'])} | "
            f"{item['bootstrap']['interval'] or 'Withheld'} |"
        )
    lines += [
        "",
        "## Measured NDCG changes",
        "",
        json.dumps(comparison["counts"]),
        "",
        "## Regressed queries",
        "",
    ]
    for row in comparison["rows"]:
        if row["status"] == "regressed":
            lines.append(
                f"- {safe(row['query_id'])}: {safe(row['question'])}; "
                f"NDCG delta {row['deltas']['ndcg']:.4f}."
            )
    if not comparison["counts"]["regressed"]:
        lines.append("No observed NDCG regressions in this comparison.")
    lines += [
        "",
        "## Reproducibility",
        "",
        "```json",
        json.dumps(
            {
                "baseline": base["config"],
                "candidate": cand["config"],
                "environment": base["environment"],
                "bootstrap": comparison["summary"]["ndcg"]["bootstrap"],
            },
            indent=2,
        ),
        "```",
        "",
        "Download the JSON bundle for the full dataset, rankings and judgments.",
        "",
        "## Limitations",
        "",
    ]
    lines += [f"- {item}" for item in bundle["limitations"]]
    lines += ["", "## Recommendations", ""]
    lines += [f"- {item}" for item in bundle["recommendations"]]
    return "\n".join(lines) + "\n"
