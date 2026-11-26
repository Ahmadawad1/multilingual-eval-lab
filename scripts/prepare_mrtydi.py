"""Download a pinned Arabic training shard and create a small reviewed-pair draft.

Run: uv run --with pyarrow python -m scripts.prepare_mrtydi
Generated data stays in ignored data/; no model or rewriting is performed.
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

import httpx

REVISION = "22131bd5c4fa7d2e818716d02115c3ecf4f6b5bd"
URL = f"https://huggingface.co/datasets/castorini/mr-tydi/resolve/{REVISION}/arabic/train/0000.parquet"


def prepare(rows, count=50, seed=42):
    eligible = [r for r in rows if r["query"].strip() and r["positive_passages"]]
    eligible.sort(key=lambda r: str(r["query_id"]))
    if not 1 <= count <= min(500, len(eligible)):
        raise ValueError("Choose between 1 and 500 available questions")
    selected = random.Random(seed).sample(eligible, count)
    docs, queries, worksheet = {}, [], []
    for number, row in enumerate(selected, 1):
        pair_id = f"mrtydi-{number:03d}"
        qrels = {}
        for passage in row["positive_passages"] + row.get("negative_passages", []):
            doc_id = "mrtydi-" + passage["docid"].replace("#", "-p")
            if not passage["text"].strip():
                raise ValueError(f"Missing passage text: {doc_id}")
            document = {
                "id": doc_id,
                "text": passage["text"],
                "title": passage["title"],
                "metadata": {
                    "source_article": passage["docid"].split("#")[0],
                    "original_doc_id": passage["docid"],
                },
            }
            if doc_id in docs and docs[doc_id] != document:
                raise ValueError(f"Conflicting passage: {doc_id}")
            docs[doc_id] = document
        # Sampled BM25 negatives are distractors, not new human nonrelevance labels.
        for passage in row["positive_passages"]:
            qrels["mrtydi-" + passage["docid"].replace("#", "-p")] = 1
        sources = sorted({p["docid"].split("#")[0] for p in row["positive_passages"]})
        if len(sources) != 1:
            raise ValueError("Multiple source articles require explicit grouping review")
        metadata = {
            "pair_id": pair_id,
            "source_article": "mrtydi:" + sources[0],
            "source_query_id": str(row["query_id"]),
            "source_split": "train",
            "source_revision": REVISION,
            "pair_reviewed": False,
            "reviewer": "",
            "msa_register_review_required": True,
        }
        for form in ("msa", "jo"):
            queries.append(
                {
                    "id": pair_id + "_" + form,
                    "question": row["query"],
                    "qrels": qrels.copy(),
                    "metadata": {
                        **metadata,
                        "form": form,
                        "authorship": "original" if form == "msa" else "unwritten_copy",
                    },
                }
            )
        worksheet.append(
            {
                "pair_id": pair_id,
                "question_msa": row["query"],
                "question_jo": "",
                "reviewer": "",
                "review_notes": "",
            }
        )
    bundle = {
        "name": f"Mr TyDi Arabic paired pilot {count} seed {seed}",
        "language": "ar",
        "source": f"castorini/mr-tydi Arabic train; revision {REVISION}",
        "description": "Reduced-corpus pilot, not full benchmark. JO rows initially copy the "
        "source and MUST be replaced and human-reviewed. Confirm source questions are MSA. "
        "Corpus is union of selected positive and sampled negative passages; labels incomplete.",
        "documents": list(docs.values()),
        "queries": queries,
    }
    return bundle, worksheet


def main():
    import pyarrow.parquet as pq

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/mrtydi-ar-pilot"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = args.output / "arabic-train.parquet"
    if not raw.exists():
        partial = raw.with_suffix(".partial")
        with httpx.stream("GET", URL, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with partial.open("wb") as stream:
                for chunk in response.iter_bytes():
                    stream.write(chunk)
        partial.replace(raw)
    rows = pq.read_table(raw).to_pylist()
    bundle, worksheet = prepare(rows, args.count, args.seed)
    # Validate using the exact Golden Sets import path, without creating runtime datasets.
    from agent_hub.eval.lab.imports import parse_bundle
    from backend.schemas import ImportRequest

    content = json.dumps(bundle, ensure_ascii=False, indent=2)
    parse_bundle(ImportRequest(format="json", content=content))
    if len(json.dumps({"format": "json", "content": content}).encode()) > 11_000_000:
        raise ValueError("Import exceeds safe request size; reduce --count")
    (args.output / "import-paired-draft.json").write_text(content, encoding="utf-8")
    (args.output / "questions-only.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in worksheet), encoding="utf-8"
    )
    manifest = {
        "source_url": URL,
        "revision": REVISION,
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "seed": args.seed,
        "source_rows": len(rows),
        "selected_pairs": args.count,
        "passages": len(bundle["documents"]),
        "selected_query_ids": [q["metadata"]["source_query_id"] for q in bundle["queries"][::2]],
        "import_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "scope": "Reduced-corpus pilot; question pairs require human authorship and review",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(args.output.resolve()), **manifest}, indent=2))


if __name__ == "__main__":
    main()
