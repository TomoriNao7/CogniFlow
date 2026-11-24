"""混合检索器：BM25 关键词 + pgvector 语义，加权融合。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import settings
from app.rag.embedder import embedder
from app.rag.vector_store import vector_store
from app.rag.bm25_store import bm25_store

logger = logging.getLogger(__name__)


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
        """两路并发检索后融合。

        并发有意义：BM25 是内存里的 CPU 活，向量侧要等数据库往返，两者
        互不依赖。但注意 embedder.embed_query 是同步阻塞调用，必须丢进
        线程池，否则它会占住事件循环，并发退化成串行。
        """
        bm25_results, vector_results = await asyncio.gather(
            self._bm25_search(query),
            self._vector_search(query),
        )
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
        # embed_query 是同步的 HTTP 调用，丢线程池避免阻塞事件循环
        qv = await asyncio.to_thread(embedder.embed_query, query)
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
        """两路结果的加权融合，按数据库主键对齐。

        必须用 db_chunk_id（整数）而不是 chunk_id（字符串）：BM25 侧形如
        "pre_sales / 商品目录#chunk0"，向量侧形如 "313"，两者永远对不上，
        按 chunk_id 合并等于没有合并，只是把两路分数摆在一起比大小。
        """
        scores: dict[int, float] = {}
        meta: dict[int, RetrievalResult] = {}
        dropped = 0

        for results, weight in (
            (bm25, self.bm25_weight),
            (vector, self.vector_weight),
        ):
            for r in results:
                cid = r.db_chunk_id
                if cid <= 0:
                    dropped += 1
                    continue
                scores[cid] = scores.get(cid, 0.0) + weight * r.score
                meta.setdefault(cid, r)

        if dropped:
            logger.warning("融合丢弃 %d 条缺少 db_chunk_id 的结果，索引可能未回填主键", dropped)

        ordered = sorted(scores, key=lambda k: scores[k], reverse=True)[: self.top_k]
        return [
            RetrievalResult(
                chunk_id=meta[cid].chunk_id,
                content=meta[cid].content,
                score=round(scores[cid], 4),
                source_document=meta[cid].source_document,
                db_chunk_id=cid,
                document_id=meta[cid].document_id,
            )
            for cid in ordered
        ]
