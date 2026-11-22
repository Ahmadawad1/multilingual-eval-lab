from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
Mode = Literal["none", "conservative", "aggressive"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Document(StrictModel):
    id: Identifier
    text: Text
    title: str = Field(default="", max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Query(StrictModel):
    id: Identifier
    question: Text
    expected_answer: str = Field(default="", max_length=20000)
    qrels: dict[Identifier, Annotated[int, Field(strict=True, ge=0, le=3)]]
    metadata: dict[str, Any] = Field(default_factory=dict)


class Dataset(StrictModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    language: str = Field(default="ar", min_length=2, max_length=35)
    description: str = Field(default="", max_length=2000)
    source: str = Field(default="User supplied; provenance unverified", max_length=1000)
    documents: list[Document] = Field(min_length=1, max_length=10000)
    queries: list[Query] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_references(self):
        doc_ids = {doc.id for doc in self.documents}
        if len(doc_ids) != len(self.documents):
            raise ValueError("Document IDs must be unique")
        if len({q.id for q in self.queries}) != len(self.queries):
            raise ValueError("Query IDs must be unique")
        for query in self.queries:
            missing = set(query.qrels) - doc_ids
            if missing:
                raise ValueError(f"Query {query.id}: unknown document IDs {sorted(missing)[:5]}")
        if sum(len(d.text) for d in self.documents) > 8_000_000:
            raise ValueError("Corpus must contain at most 8 million characters")
        return self


class RetrievalConfig(StrictModel):
    query_normalization: Mode = "none"
    corpus_normalization: Mode = "none"
    k: int = Field(default=5, ge=1, le=50)
    k1: float = Field(default=1.5, ge=0.1, le=3)
    b: float = Field(default=0.75, ge=0, le=1)


class ExperimentRequest(StrictModel):
    dataset_id: Identifier
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    config: RetrievalConfig = Field(default_factory=RetrievalConfig)


class ImportRequest(StrictModel):
    format: Literal["json", "jsonl", "csv"]
    content: str = Field(max_length=10_000_000)
    name: str = Field(default="Imported dataset", max_length=120)
    language: str = Field(default="ar", min_length=2, max_length=35)


class PlaygroundRequest(StrictModel):
    dataset_id: Identifier
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
    config: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generate: bool = False


class JudgeRequest(StrictModel):
    engine: Literal["rubric", "ragas"] = "rubric"
    experiment_id: Identifier
    query_id: Identifier
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)]


class ReviewRequest(StrictModel):
    correctness: int = Field(ge=0, le=4)
    faithfulness: int = Field(ge=0, le=4)
    relevance: int = Field(ge=0, le=4)
    notes: str = Field(min_length=1, max_length=4000)
