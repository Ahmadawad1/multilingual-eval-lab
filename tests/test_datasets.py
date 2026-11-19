import csv
import io
import json

import pytest
from pydantic import ValidationError

from backend.datasets import dataset_hash, parse_dataset
from backend.schemas import Dataset, ImportRequest


def test_three_import_formats_preserve_arabic_and_metadata(tiny_data):
    canonical = parse_dataset(
        ImportRequest(format="json", content="\ufeff" + json.dumps(tiny_data))
    )
    assert canonical.queries[0].question == "اداره"
    records = [{"type": "document", **d} for d in tiny_data["documents"]] + [
        {"type": "query", **q} for q in tiny_data["queries"]
    ]
    jsonl = "\n".join(json.dumps(r) for r in records)
    result = parse_dataset(ImportRequest(format="jsonl", content=jsonl, name="Test"))
    assert result == canonical
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=["type", "id", "text", "question", "expected_answer", "qrels"]
    )
    writer.writeheader()
    for record in records:
        writer.writerow({k: json.dumps(v) if isinstance(v, dict) else v for k, v in record.items()})
    assert (
        parse_dataset(ImportRequest(format="csv", content=buffer.getvalue(), name="Test"))
        == canonical
    )
    assert dataset_hash(canonical) == dataset_hash(result)
    result.queries[0].qrels["d1"] = 2
    assert dataset_hash(canonical) != dataset_hash(result)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-doc",
        "duplicate-query",
        "unknown-doc",
        "grade",
        "string-grade",
        "empty-text",
        "extra-field",
    ],
)
def test_invalid_data_rejected(tiny_data, mutation):
    if mutation == "duplicate-doc":
        tiny_data["documents"].append(tiny_data["documents"][0])
    elif mutation == "duplicate-query":
        tiny_data["queries"].append(tiny_data["queries"][0])
    elif mutation == "unknown-doc":
        tiny_data["queries"][0]["qrels"]["missing"] = 1
    elif mutation == "grade":
        tiny_data["queries"][0]["qrels"]["d1"] = 4
    elif mutation == "string-grade":
        tiny_data["queries"][0]["qrels"]["d1"] = "3"
    elif mutation == "empty-text":
        tiny_data["documents"][0]["text"] = "   "
    else:
        tiny_data["surprise"] = True
    with pytest.raises(ValidationError):
        Dataset.model_validate(tiny_data)


def test_invalid_records_and_json():
    for fmt, content in [
        ("json", "{"),
        ("jsonl", "[]"),
        ("jsonl", '{"type":"bad"}'),
        ("csv", "id,text\na,hello"),
    ]:
        with pytest.raises(ValueError):
            parse_dataset(ImportRequest(format=fmt, content=content))
