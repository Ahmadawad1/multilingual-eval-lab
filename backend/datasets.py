import csv
import hashlib
import io
import json

from .schemas import Dataset, ImportRequest


def canonical_json(value) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def dataset_hash(dataset: Dataset) -> str:
    return hashlib.sha256(canonical_json(dataset.model_dump()).encode("utf-8")).hexdigest()


def parse_dataset(request: ImportRequest) -> Dataset:
    content = request.content.lstrip("\ufeff")
    if request.format == "json":
        return Dataset.model_validate(json.loads(content))
    rows = (
        [json.loads(line) for line in content.splitlines() if line.strip()]
        if request.format == "jsonl"
        else list(csv.DictReader(io.StringIO(content)))
    )
    documents, queries = [], []
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Row {index} must be an object")
        row = {key: value for key, value in raw.items() if value != "" and value is not None}
        kind = row.pop("type", None)
        if kind not in {"document", "query"}:
            raise ValueError(f"Row {index}: type must be document or query")
        for field in ("qrels", "metadata"):
            if field in row and isinstance(row[field], str):
                row[field] = json.loads(row[field])
        if kind == "document":
            documents.append(row)
        else:
            queries.append(row)
    return Dataset(
        name=request.name, language=request.language, documents=documents, queries=queries
    )
