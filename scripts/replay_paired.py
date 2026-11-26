"""Verify a paired experiment ZIP's checksums and Hit@k evidence without inference."""

import argparse
import hashlib
import json
import math
import zipfile


def verify(path):
    with zipfile.ZipFile(path) as archive:
        checksums = json.loads(archive.read("checksums.json"))
        for name, expected in checksums.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f"Checksum mismatch: {name}")
        study = json.loads(archive.read("protocol.json"))
        dataset = json.loads(archive.read("dataset.json"))
        if study["dataset_hash"] != dataset["current_hash"]:
            raise ValueError("Dataset identity mismatch")
        items = {i["id"]: i for i in dataset["items"]}
        docs = {d["doc_id"] for d in dataset["corpus"]}
        verified = 0
        cells = ["bm25_msa", "bm25_jo", "dense_msa", "dense_jo"]
        for name in sorted(checksums):
            if not name.startswith("runs/"):
                continue
            run = json.loads(archive.read(name))
            if run["status"] != "done":
                continue
            if run["dataset_hash"] != study["dataset_hash"] or not run["rows"]:
                raise ValueError("Invalid completed run")
            seen = set()
            totals = dict.fromkeys(cells, 0)
            for row in run["rows"]:
                if row["pair_id"] in seen:
                    raise ValueError("Duplicate pair")
                seen.add(row["pair_id"])
                for cell in cells:
                    result = row[cell]
                    item = items[result["query_id"]]
                    if (
                        item["query"] != result["query"]
                        or item["relevant"] != row["qrels"]
                        or item["split"] != run["split"]
                    ):
                        raise ValueError("Query, split or qrels changed")
                    ranked = result["ranked"]
                    if len(ranked) > study["k"] or len({r["doc_id"] for r in ranked}) != len(
                        ranked
                    ):
                        raise ValueError("Invalid ranking length or duplicate passage")
                    for rank, hit in enumerate(ranked, 1):
                        if hit["rank"] != rank or hit["doc_id"] not in docs:
                            raise ValueError("Invalid rank or passage ID")
                    first = next(
                        (r["rank"] for r in ranked if row["qrels"].get(r["doc_id"], 0)), None
                    )
                    if result["rank"] != first or result["hit"] != int(first is not None):
                        raise ValueError("Hit or first relevant rank does not match qrels")
                    totals[cell] += result["hit"]
            means = {c: value / len(seen) for c, value in totals.items()}
            means.update(
                bm25_gap=means["bm25_jo"] - means["bm25_msa"],
                dense_gap=means["dense_jo"] - means["dense_msa"],
                jo_gain=means["dense_jo"] - means["bm25_jo"],
                msa_gain=means["dense_msa"] - means["bm25_msa"],
            )
            means["gap_change"] = means["dense_gap"] - means["bm25_gap"]
            for key, mean in means.items():
                if not math.isclose(mean, run["report"]["metrics"][key]["mean"], abs_tol=1e-10):
                    raise ValueError(f"Incorrect aggregate: {key}")
            verified += 1
        return {
            "verified_completed_runs": verified,
            "scope": "Checksums, rankings, labels and point estimates; no inference replay",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    print(json.dumps(verify(parser.parse_args().archive), indent=2))
