"""Recompute deterministic retrieval from a JSON report without a server or model."""

import argparse
import json
from pathlib import Path

from . import ENGINE_VERSION
from .datasets import dataset_hash
from .experiments import compare, run_experiment
from .schemas import Dataset, ExperimentRequest


def verify_bundle(bundle: dict) -> dict:
    dataset = bundle["dataset"]
    digest = dataset_hash(Dataset.model_validate(dataset["data"]))
    if dataset["hash"] != digest:
        raise ValueError("Dataset hash does not match report content")
    results = {}
    runs = []
    for variant in ("baseline", "candidate"):
        saved = bundle["comparison"][variant]
        if saved["dataset_hash"] != digest or saved["engine_version"] != ENGINE_VERSION:
            raise ValueError("Dataset or engine version mismatch; use the recorded engine version")
        replayed = run_experiment(
            dataset,
            ExperimentRequest(dataset_id=dataset["id"], name=saved["name"], config=saved["config"]),
        )
        if replayed["metrics"] != saved["metrics"] or replayed["rows"] != saved["rows"]:
            raise ValueError(f"{variant} results differ from the saved run")
        results[variant] = {"verified": True, "metrics": replayed["metrics"]}
        runs.append(replayed)
    comparison = compare(runs[0], runs[1])
    for field in ("summary", "counts"):
        if comparison[field] != bundle["comparison"][field]:
            raise ValueError(f"Comparison {field} differs from the saved report")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Reproducibility JSON downloaded from Reports")
    args = parser.parse_args()
    try:
        if args.report.stat().st_size > 100_000_000:
            parser.error("Report exceeds 100 MB safety limit")
        result = verify_bundle(json.loads(args.report.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"Verification failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
