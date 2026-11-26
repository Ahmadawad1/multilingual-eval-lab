import json

from agent_hub.eval.lab.imports import parse_bundle
from backend.schemas import ImportRequest
from scripts.prepare_mrtydi import prepare


def test_pilot_preserves_labels_and_isolates_rewrite_input():
    rows = [
        {
            "query_id": "9",
            "query": "ما تكلفة التجديد؟",
            "positive_passages": [{"docid": "1#0", "title": "Title", "text": "Answer"}],
            "negative_passages": [{"docid": "2#0", "title": "Other", "text": "Distractor"}],
        }
    ]
    bundle, worksheet = prepare(rows, count=1)
    assert len(bundle["documents"]) == 2
    a, b = bundle["queries"]
    assert a["qrels"] == b["qrels"] == {"mrtydi-1-p0": 1}
    assert not a["metadata"]["pair_reviewed"]
    assert not b["metadata"]["pair_reviewed"]
    assert a["question"] == b["question"]  # Explicit unfinished copy, no invented dialect.
    assert b["metadata"]["authorship"] == "unwritten_copy"
    assert set(worksheet[0]) == {
        "pair_id",
        "question_msa",
        "question_jo",
        "reviewer",
        "review_notes",
    }
    assert worksheet[0]["question_jo"] == ""
    assert prepare(rows, count=1) == (bundle, worksheet)
    _, documents, items = parse_bundle(ImportRequest(format="json", content=json.dumps(bundle)))
    assert len(documents) == 2
    assert len(items) == 2
