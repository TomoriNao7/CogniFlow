from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    score: float
    source_document: str = ""


class HybridRetriever:
    """Hybrid retrieval: BM25 keyword + vector semantic, weighted fusion."""

    def __init__(
        self,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        top_k: int = 5,
    ) -> None:
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.top_k = top_k

    async def retrieve(self, query: str) -> list[RetrievalResult]:
        """Run hybrid retrieval. In production this queries Milvus + BM25 index.
        For MVP we return mock results to demonstrate the pipeline.
        """
        bm25_results = await self._bm25_search(query)
        vector_results = await self._vector_search(query)
        return self._fusion(bm25_results, vector_results)

    async def _bm25_search(self, query: str) -> list[RetrievalResult]:
        """Mock BM25 keyword search. Replace with actual BM25 index in production."""
        # Production: query PostgreSQL full-text search or Elasticsearch
        return _mock_knowledge(query, "bm25")

    async def _vector_search(self, query: str) -> list[RetrievalResult]:
        """Vector semantic search via Milvus."""
        # Production: embed query → Milvus.search()
        return _mock_knowledge(query, "vector")

    def _fusion(
        self, bm25: list[RetrievalResult], vector: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        """Weighted fusion of BM25 and vector results."""
        scores: dict[str, float] = {}
        contents: dict[str, tuple[str, str]] = {}

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
                score=scores[cid],
                source_document=contents[cid][1],
            )
            for cid in sorted_ids
        ]


def _mock_knowledge(query: str, source: str) -> list[RetrievalResult]:
    """Mock knowledge base for demonstration. Replace with real retrieval."""
    base_score = 0.85 if source == "vector" else 0.72
    mock_docs = [
        ("prod_001", "iPhone 15 Pro 256GB 黑色，售价 8999 元，支持 24 期免息分期。配备 A17 Pro 芯片和 48MP 三摄系统。", "商品目录"),
        ("prod_002", "AirPods Pro 2 代，售价 1899 元，主动降噪，支持 USB-C 充电。", "商品目录"),
        ("promo_001", "618 年中大促：全场满 300 减 50，新人注册送 100 元优惠券，会员享双倍积分。", "促销规则"),
        ("promo_002", "PLUS 会员专享：每月 8 号会员日，全场 95 折，部分商品可叠加店铺优惠券。", "会员政策"),
        ("stock_001", "iPhone 15 Pro 黑色 256GB 全国各仓均有现货，预计 1-2 天送达。512GB 版本北京仓缺货。", "库存信息"),
    ]

    results: list[RetrievalResult] = []
    for i, (cid, content, doc) in enumerate(mock_docs):
        # Simple relevance simulation
        score = base_score - i * 0.08
        results.append(
            RetrievalResult(chunk_id=cid, content=content, score=score, source_document=doc)
        )
    return results
