"""Conversion of labeled bundles and benchmark qrels into Golden Sets."""

from collections import defaultdict

from backend.datasets import parse_dataset
from backend.schemas import ImportRequest

from .models import CorpusDoc, GoldenItem


def parse_bundle(request: ImportRequest):
    dataset = parse_dataset(request)
    docs = [
        CorpusDoc(doc_id=d.id, body=d.text, lang=dataset.language, source=dataset.source)
        for d in dataset.documents
    ]
    items = [
        GoldenItem(
            id=q.id,
            query=q.question,
            lang=dataset.language,
            ground_truth=q.expected_answer,
            relevant={d: grade for d, grade in q.qrels.items() if grade > 0},
            judged_nonrelevant=[d for d, grade in q.qrels.items() if grade == 0],
            split="dev",
            origin="imported",
            metadata=q.metadata,
        )
        for q in dataset.queries
    ]
    return dataset, docs, items


def parse_qrels(text: str) -> dict[str, dict[str, int]]:
    """Read TREC four-column or three-column whitespace-separated judgments."""
    labels = defaultdict(dict)
    for number, line in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if fields in (["query-id", "corpus-id", "score"], ["qid", "docid", "relevance"]):
            continue
        if len(fields) not in (3, 4) or fields[-1] not in {"0", "1", "2", "3"}:
            raise ValueError(f"Qrels line {number}: expected query ID, document ID and grade 0–3")
        query_id, doc_id, grade_text = fields[0], fields[-2], fields[-1]
        grade = int(grade_text)
        if doc_id in labels[query_id] and labels[query_id][doc_id] != grade:
            raise ValueError(f"Qrels line {number}: conflicting grades for {query_id} / {doc_id}")
        labels[query_id][doc_id] = grade
    if not labels:
        raise ValueError("The qrels file contains no judgments")
    return dict(labels)
