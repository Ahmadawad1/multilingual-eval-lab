"""Export a paired top-five comparison from a saved Brainwave Eval BM25 run."""
import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen


def fetch(path):
    with urlopen("http://127.0.0.1:8000/api/" + path, timeout=30) as response:
        return json.load(response)


def summarize(run):
    if run["config"]["k"] != 5:
        raise ValueError("Run at cutoff K = 5.")
    groups = defaultdict(dict)
    for row in run["rows"]:
        meta = row["metadata"]
        pair, form = meta.get("pair_id"), meta.get("form")
        if not pair or form not in {"msa", "jo"} or form in groups[pair]:
            raise ValueError(f"Invalid pair metadata on {row['query_id']}")
        groups[pair][form] = row
    pairs = []
    for pair, versions in sorted(groups.items()):
        if set(versions) != {"msa", "jo"}:
            raise ValueError(f"Incomplete pair {pair}")
        labels = versions["msa"]["qrels"]
        if labels != versions["jo"]["qrels"] or not any(labels.values()):
            raise ValueError(f"Check shared positive qrels for {pair}")
        record = {"pair_id": pair}
        for form, row in versions.items():
            rank = next((r["rank"] for r in row["ranking"] if labels.get(r["doc_id"], 0) > 0), None)
            record.update({form + "_query": row["question"], form + "_rank": rank,
                           form + "_hit": int(rank is not None)})
        msa, jo = record["msa_hit"], record["jo_hit"]
        record["outcome"] = {(1, 1): "both", (1, 0): "msa_only", (0, 1): "jo_only",
                             (0, 0): "neither"}[msa, jo]
        pairs.append(record)
    n = len(pairs)
    if not n:
        raise ValueError("No pairs to score.")
    diffs = [r["jo_hit"] - r["msa_hit"] for r in pairs]
    rng = random.Random(42)
    draws = sorted(100 * sum(rng.choices(diffs, k=n)) / n for _ in range(5000))
    counts = Counter(r["outcome"] for r in pairs)
    summary = {"pairs": n, "msa_hit_at_5": sum(r["msa_hit"] for r in pairs) / n,
               "jo_hit_at_5": sum(r["jo_hit"] for r in pairs) / n,
               "jo_minus_msa_pp": 100 * sum(diffs) / n,
               "paired_bootstrap_95_pp": [draws[124], draws[4874]],
               "bootstrap_seed": 42, "resamples": 5000,
               "outcomes": {k: counts[k] for k in ("both", "msa_only", "jo_only", "neither")},
               "dataset_hash": run["dataset_hash"], "config": run["config"],
               "engine_version": run["engine_version"], "run_id": run["id"]}
    return pairs, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Exact unique experiment name or run UUID")
    parser.add_argument("output", type=Path, help="New output directory")
    args = parser.parse_args()
    runs = [r for r in fetch("experiments") if args.run in (r["id"], r["name"])]
    if len(runs) != 1:
        raise SystemExit("Use a unique run name or the UUID from /api/experiments.")
    run = fetch("experiments/" + runs[0]["id"])
    pairs, summary = summarize(run)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in [("run", run), ("summary", summary)]:
        (args.output / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with (args.output / "pairs.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=pairs[0])
        writer.writeheader()
        writer.writerows(pairs)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
