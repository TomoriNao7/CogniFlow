"""混合检索器：BM25 关键词 + pgvector 语义，加权融合。"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.rag.embedder import embedder
from app.rag.vector_store import vector_store
from app.rag.bm25_store import bm25_store


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    score: float
    source_document: str = ""
    db_chunk_id: int = 0
    document_id: int = 0


class HybridRetriever:
    """混合检索：BM25 关键词 + 向量语义，加权融合。"""

    def __init__(
        self,
        bm25_weight: float | None = None,
        vector_weight: float | None = None,
        top_k: int | None = None,
    ) -> None:
        self.bm25_weight = bm25_weight if bm25_weight is not None else settings.bm25_weight
        self.vector_weight = vector_weight if vector_weight is not None else settings.vector_weight
        self.top_k = top_k if top_k is not None else settings.retrieval_top_k

    async def retrieve(self, query: str) -> list[RetrievalResult]:
        """混合检索：BM25 + 向量语义，加权融合。"""
        bm25_results = await self._bm25_search(query)
        vector_results = await self._vector_search(query)
        return self._fusion(bm25_results, vector_results)

    async def _bm25_search(self, query: str) -> list[RetrievalResult]:
        """内存索引上的 BM25 关键词检索。"""
        if not bm25_store.is_ready:
            return []
        hits = bm25_store.search(query, top_k=self.top_k * 2)
        return [
            RetrievalResult(
                chunk_id=doc.chunk_id,
                content=doc.content,
                score=score,
                source_document=doc.source_document,
                db_chunk_id=doc.db_chunk_id,
            )
            for doc, score in hits
        ]

    async def _vector_search(self, query: str) -> list[RetrievalResult]:
        """通过 pgvector 做向量语义检索。"""
        qv = embedder.embed_query(query)
        hits = await vector_store.search(qv, top_k=self.top_k * 2)
        return [
            RetrievalResult(
                chunk_id=h["entity"].get("chunk_id", ""),
                content=h["entity"].get("content", ""),
                score=h["distance"],  # cosine 相似度：1 = 完全匹配
                source_document=h["entity"].get("source_document", ""),
                db_chunk_id=int(h["entity"].get("db_chunk_id", 0) or 0),
                document_id=int(h["entity"].get("document_id", 0) or 0),
            )
            for h in hits
        ]

    def _fusion(
        self,
        bm25: list[RetrievalResult],
        vector: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """BM25 与向量结果的加权融合（RRF-like 打分）。"""
        contents: dict[str, tuple[str, str, int, int]] = {}
        scores: dict[str, float] = {}

        for r in bm25:
            scores[r.chunk_id] = self.bm25_weight * r.score
            contents[r.chunk_id] = (r.content, r.source_document, r.db_chunk_id, r.document_id)

        for r in vector:
            current = scores.get(r.chunk_id, 0.0)
            scores[r.chunk_id] = current + self.vector_weight * r.score
            if r.chunk_id not in contents:
                contents[r.chunk_id] = (r.content, r.source_document, r.db_chunk_id, r.document_id)

        sorted_ids = sorted(scores, key=lambda k: scores[k], reverse=True)[: self.top_k]
        return [
            RetrievalResult(
                chunk_id=cid,
                content=contents[cid][0],
                score=round(scores[cid], 4),
                source_document=contents[cid][1],
                db_chunk_id=contents[cid][2],
                document_id=contents[cid][3],
            )
            for cid in sorted_ids
        ]
