"""Hybrid retriever: BM25 keyword + Milvus vector semantic, weighted fusion."""

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


class HybridRetriever:
    """Hybrid retrieval combining BM25 keyword + vector semantic search."""

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
        """Hybrid retrieval: BM25 + vector semantic, weighted fusion."""
        bm25_results = await self._bm25_search(query)
        vector_results = await self._vector_search(query)
        return self._fusion(bm25_results, vector_results)

    async def _bm25_search(self, query: str) -> list[RetrievalResult]:
        """BM25 keyword search over in-memory index."""
        if not bm25_store.is_ready:
            return []
        hits = bm25_store.search(query, top_k=self.top_k * 2)
        return [
            RetrievalResult(
                chunk_id=doc.chunk_id,
                content=doc.content,
                score=score,
                source_document=doc.source_document,
            )
            for doc, score in hits
        ]

    async def _vector_search(self, query: str) -> list[RetrievalResult]:
        """Vector semantic search via Milvus Lite."""
        if not vector_store.is_ready:
            return []
        qv = embedder.embed_query(query)
        hits = vector_store.search(qv, top_k=self.top_k * 2)
        return [
            RetrievalResult(
                chunk_id=h["entity"].get("chunk_id", ""),
                content=h["entity"].get("content", ""),
                score=h["distance"],  # COSINE: 1 = perfect match
                source_document=h["entity"].get("source_document", ""),
            )
            for h in hits
        ]

    def _fusion(
        self,
        bm25: list[RetrievalResult],
        vector: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Weighted fusion of BM25 and vector results using RRF-like scoring."""
        contents: dict[str, tuple[str, str]] = {}
        scores: dict[str, float] = {}

        for r in bm25:
            scores[r.chunk_id] = self.bm25_weight * r.score
            contents[r.chunk_id] = (r.content, r.source_document)

        for r in vector:
            current = scores.get(r.chunk_id, 0.0)
            scores[r.chunk_id] = current + self.vector_weight * r.score
            if r.chunk_id not in contents:
                contents[r.chunk_id] = (r.content, r.source_document)

        sorted_ids = sorted(scores, key=lambda k: scores[k], reverse=True)[: self.top_k]
        return [
            RetrievalResult(
                chunk_id=cid,
                content=contents[cid][0],
                score=round(scores[cid], 4),
                source_document=contents[cid][1],
            )
            for cid in sorted_ids
        ]
