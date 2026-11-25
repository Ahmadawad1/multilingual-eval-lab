"""Export a paired top-five comparison from a saved Brainwave Eval BM25 run."""

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
    if run["status"] != "done" or run["variant"].get("engine") != "bm25":
        raise ValueError("Select a completed Local BM25 run.")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Run ID from the result page")
    parser.add_argument("output", type=Path, help="New output directory")
    args = parser.parse_args()
    run = fetch("runs/" + quote(args.run, safe=""))
    bundle = fetch(f"datasets/{run['dataset_id']}/versions/{run['dataset_version']}")
    pairs, summary = summarize(run, bundle)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in [("run", run), ("summary", summary)]:
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
