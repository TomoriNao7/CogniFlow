"""In-memory BM25 keyword index with pickle persistence."""

from __future__ import annotations

import os
import pickle
from dataclasses import dataclass

from rank_bm25 import BM25Okapi


@dataclass
class Bm25Doc:
    chunk_id: str
    content: str
    source_document: str
    heading: str
    chunk_index: int


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer — splits on whitespace and CJK character boundaries."""
    import re
    # Split on whitespace, and also separate CJK chars for partial matching
    tokens: list[str] = []
    for word in text.split():
        # Split CJK runs into individual characters for recall
        if re.search(r'[一-鿿]', word):
            tokens.extend(re.findall(r'[一-鿿]|[^一-鿿]+', word))
        else:
            tokens.append(word.lower())
    return [t for t in tokens if t.strip()]


class Bm25Store:
    """In-memory BM25 keyword search index."""

    def __init__(self) -> None:
        self._docs: list[Bm25Doc] = []
        self._index: BM25Okapi | None = None
        self._corpus: list[list[str]] = []

    def build(self, docs: list[Bm25Doc]) -> None:
        """Build BM25 index from documents."""
        self._docs = docs
        self._corpus = [_tokenize(d.content) for d in docs]
        if self._corpus:
            self._index = BM25Okapi(self._corpus)

    def search(self, query: str, top_k: int = 10) -> list[tuple[Bm25Doc, float]]:
        """Search and return top_k docs with normalized scores."""
        if not self._index or not self._docs:
            return []

        tokens = _tokenize(query)
        scores = self._index.get_scores(tokens)

        # Get top_k indices sorted by score descending
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top = indexed[:top_k]

        # Normalize scores to [0, 1]
        max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0

        return [(self._docs[i], score / max_score) for i, score in top if score > 0]

    def save(self, path: str) -> None:
        """Persist index to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"docs": self._docs, "corpus": self._corpus}, f)

    def load(self, path: str) -> None:
        """Load index from disk."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"BM25 index not found: {path}")
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._docs = data["docs"]
        self._corpus = data["corpus"]
        if self._corpus:
            self._index = BM25Okapi(self._corpus)

    @property
    def is_ready(self) -> bool:
        return self._index is not None and len(self._docs) > 0

    def __len__(self) -> int:
        return len(self._docs)


# Singleton
bm25_store = Bm25Store()
