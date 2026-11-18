"""内存 BM25 关键词索引，pickle 落盘。"""

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
    db_chunk_id: int = 0  # 权威主键 = knowledge_chunks.id（0 = 尚未入库）


def _tokenize(text: str) -> list[str]:
    """简易分词：按空白切，中文再逐字切。"""
    import re
    # 按空白切分，中文逐字拆开以提升召回
    tokens: list[str] = []
    for word in text.split():
        # 中文串拆成单字，提升召回
        if re.search(r'[一-鿿]', word):
            tokens.extend(re.findall(r'[一-鿿]|[^一-鿿]+', word))
        else:
            tokens.append(word.lower())
    return [t for t in tokens if t.strip()]


class Bm25Store:
    """内存 BM25 关键词索引。"""

    def __init__(self) -> None:
        self._docs: list[Bm25Doc] = []
        self._index: BM25Okapi | None = None
        self._corpus: list[list[str]] = []

    def build(self, docs: list[Bm25Doc]) -> None:
        """用文档列表构建 BM25 索引。"""
        self._docs = docs
        self._corpus = [_tokenize(d.content) for d in docs]
        if self._corpus:
            self._index = BM25Okapi(self._corpus)

    def search(self, query: str, top_k: int = 10) -> list[tuple[Bm25Doc, float]]:
        """检索 top_k，分数按本次最大值归一化。"""
        if not self._index or not self._docs:
            return []

        tokens = _tokenize(query)
        scores = self._index.get_scores(tokens)

        # 按分数降序取 top_k
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top = indexed[:top_k]

        # 分数归一化到 [0, 1]
        max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0

        return [(self._docs[i], score / max_score) for i, score in top if score > 0]

    def save(self, path: str) -> None:
        """索引落盘。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"docs": self._docs, "corpus": self._corpus}, f)

    def load(self, path: str) -> None:
        """从磁盘加载索引。"""
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


# 单例
bm25_store = Bm25Store()
