import math
from collections import Counter, defaultdict

from .normalization import tokenize
from .schemas import Document, RetrievalConfig


class BM25:
    """Okapi BM25 with positive IDF, unique query terms, stable ID tie-breaking."""

    def __init__(self, documents: list[Document], config: RetrievalConfig):
        self.config = config
        self.documents = {doc.id: doc for doc in documents}
        self.lengths = {}
        self.postings = defaultdict(dict)
        for doc in documents:
            tokens = tokenize(doc.text, config.corpus_normalization)
            self.lengths[doc.id] = len(tokens)
            for token, count in Counter(tokens).items():
                self.postings[token][doc.id] = count
        self.average_length = sum(self.lengths.values()) / len(documents) or 1

    def search(self, question: str) -> list[dict]:
        scores = defaultdict(float)
        config = self.config
        for term in sorted(set(tokenize(question, config.query_normalization))):
            postings = self.postings.get(term, {})
            idf = math.log(1 + (len(self.documents) - len(postings) + 0.5) / (len(postings) + 0.5))
            for doc_id, tf in postings.items():
                norm = 1 - config.b + config.b * self.lengths[doc_id] / self.average_length
                scores[doc_id] += idf * tf * (config.k1 + 1) / (tf + config.k1 * norm)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[: config.k]
        return [
            {"doc_id": doc_id, "score": score, "rank": rank}
            for rank, (doc_id, score) in enumerate(ranked, start=1)
        ]
