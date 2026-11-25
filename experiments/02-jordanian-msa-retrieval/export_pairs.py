"""Export paired Hit@5 for BM25 or dense runs and optionally compare both engines."""

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


def fetch(path):
    with urlopen("http://127.0.0.1:8000/api/eval/" + path, timeout=30) as response:
        return json.load(response)


def summarize(run, bundle):
    variant = run["variant"]
    engine = variant.get("engine", "knowhub")
    if run["status"] != "done" or engine not in {"bm25", "knowhub"}:
        raise ValueError("Select a completed Local BM25 or Indexed search run.")
    if variant.get("level", "document") != "document":
        raise ValueError("Use document level so both engines score the same passage IDs.")
    if engine == "knowhub" and variant.get("hybrid", True):
        raise ValueError("Turn Hybrid (RRF) off for a dense-only comparison.")
    if run["dataset_hash"] != bundle["current_hash"]:
        raise ValueError("Dataset changed since scoring. Rerun against the intended version.")
    if run["k"] != 5 or run["variant"]["fetch"] < 5:
        raise ValueError("Run at cutoff K = 5.")
    groups = defaultdict(dict)
    by_id = {item["id"]: item for item in bundle["items"]}
    selected = {
        item["id"]
        for item in bundle["items"]
        if run["split"] == "all" or item["split"] == run["split"]
    }
    if selected != {row["item_id"] for row in run["results"]}:
        raise ValueError("Some queries were skipped. Check every pair has positive qrels.")
    for row in run["results"]:
        if row["error"]:
            raise ValueError(f"Query failed: {row['item_id']}")
        meta = by_id[row["item_id"]]["metadata"]
        pair, form = meta.get("pair_id"), meta.get("form")
        if not pair or form not in {"msa", "jo"} or form in groups[pair]:
            raise ValueError(f"Invalid pair metadata on {row['item_id']}")
        groups[pair][form] = row
    pairs = []
    for pair, versions in sorted(groups.items()):
        if set(versions) != {"msa", "jo"}:
            raise ValueError(f"Incomplete pair {pair}")
        labels = versions["msa"]["relevant_units"]
        if labels != versions["jo"]["relevant_units"] or not any(labels.values()):
            raise ValueError(f"Check shared positive qrels for {pair}")
        record = {"pair_id": pair}
        for form, row in versions.items():
            rank = next(
                (r["rank"] for r in row["ranked"][:5] if labels.get(r["doc_id"], 0) > 0), None
            )
            record.update(
                {
                    form + "_query": row["query"],
                    form + "_rank": rank,
                    form + "_hit": int(rank is not None),
                }
            )
        msa, jo = record["msa_hit"], record["jo_hit"]
        record["outcome"] = {
            (1, 1): "both",
            (1, 0): "msa_only",
            (0, 1): "jo_only",
            (0, 0): "neither",
        }[msa, jo]
        pairs.append(record)
    n = len(pairs)
    if not n:
        raise ValueError("No pairs to score.")
    diffs = [r["jo_hit"] - r["msa_hit"] for r in pairs]
    rng = random.Random(42)
    draws = sorted(100 * sum(rng.choices(diffs, k=n)) / n for _ in range(5000))
    counts = Counter(r["outcome"] for r in pairs)
    summary = {
        "pairs": n,
        "msa_hit_at_5": sum(r["msa_hit"] for r in pairs) / n,
        "jo_hit_at_5": sum(r["jo_hit"] for r in pairs) / n,
        "jo_minus_msa_pp": 100 * sum(diffs) / n,
        "paired_bootstrap_95_pp": [draws[124], draws[4874]],
        "bootstrap_seed": 42,
        "resamples": 5000,
        "outcomes": {k: counts[k] for k in ("both", "msa_only", "jo_only", "neither")},
        "dataset_hash": run["dataset_hash"],
        "config": {"k": run["k"], **run["variant"]},
        "engine_version": run["engine_version"],
        "run_id": run["id"],
    }
    return pairs, summary


def compare_engines(bm25, dense, bundle):
    if bm25["variant"].get("engine") != "bm25":
        raise ValueError("The positional run must be BM25 when using --dense-run.")
    if dense["variant"].get("engine", "knowhub") != "knowhub":
        raise ValueError("--dense-run must refer to Indexed search with Hybrid off.")
    for key in ("dataset_id", "dataset_version", "dataset_hash", "split", "k"):
        if bm25[key] != dense[key]:
            raise ValueError(f"Runs differ in {key}; compare the same dataset version and split.")
    for key in ("corpus_index", "query_normalization", "fetch", "min_score"):
        if bm25["variant"].get(key) != dense["variant"].get(key):
            raise ValueError(f"Runs differ in {key}; hold retrieval controls fixed.")
    b_pairs, b_summary = summarize(bm25, bundle)
    d_pairs, d_summary = summarize(dense, bundle)
    if [p["pair_id"] for p in b_pairs] != [p["pair_id"] for p in d_pairs]:
        raise ValueError("Runs contain different intent pairs.")
    b_rows = {r["item_id"]: r for r in bm25["results"]}
    for row in dense["results"]:
        other = b_rows[row["item_id"]]
        if any(row[k] != other[k] for k in ("query", "query_sent", "relevant_units")):
            raise ValueError("Query text or relevance labels changed between engines.")
    effects = {"dense_gain_msa_pp": [], "dense_gain_jo_pp": [], "gap_change_pp": []}
    for b, d in zip(b_pairs, d_pairs, strict=True):
        msa = d["msa_hit"] - b["msa_hit"]
        jo = d["jo_hit"] - b["jo_hit"]
        effects["dense_gain_msa_pp"].append(msa)
        effects["dense_gain_jo_pp"].append(jo)
        effects["gap_change_pp"].append(jo - msa)
    contrasts = {}
    for name, values in effects.items():
        rng = random.Random(42)
        n = len(values)
        draws = sorted(100 * sum(rng.choices(values, k=n)) / n for _ in range(5000))
        contrasts[name] = {
            "estimate": 100 * sum(values) / n,
            "paired_bootstrap_95_pp": [draws[124], draws[4874]],
        }
    return {
        "bm25": b_summary,
        "dense": d_summary,
        "contrasts": contrasts,
        "interpretation": "Positive gap_change means the JO-minus-MSA gap moved upward; "
        "inspect all four rates before claiming a smaller dialect deficit.",
        "bootstrap_seed": 42,
        "resamples": 5000,
        "status": "exploratory; intervals are not adjusted for multiple contrasts",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Run ID from the result page")
    parser.add_argument("output", type=Path, help="New output directory")
    parser.add_argument(
        "--dense-run", help="Dense run ID to compare against the positional BM25 run"
    )
    args = parser.parse_args()
    run = fetch("runs/" + quote(args.run, safe=""))
    bundle = fetch(f"datasets/{run['dataset_id']}/versions/{run['dataset_version']}")
    pairs, summary = summarize(run, bundle)
    extra = []
    if args.dense_run:
        dense = fetch("runs/" + quote(args.dense_run, safe=""))
        comparison = compare_engines(run, dense, bundle)
        extra = [("dense-run", dense), ("engine-comparison", comparison)]
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in [("run", run), ("summary", summary), *extra]:
        (args.output / (name + ".json")).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    with (args.output / "pairs.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=pairs[0])
        writer.writeheader()
        writer.writerows(pairs)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
