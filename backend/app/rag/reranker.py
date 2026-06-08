from __future__ import annotations

from app.rag.retriever import RetrievalResult


class Reranker:
    """bge-reranker-v2-m3 cross-encoder for result re-ranking.
    In production this wraps a local or API-hosted model.
    """

    def __init__(self, model_name: str = "bge-reranker-v2-m3") -> None:
        self.model_name = model_name

    async def rerank(
        self, query: str, results: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        """Re-rank results by relevance to the query.
        MVP: returns results as-is with scores that would be produced by the reranker.
        """
        # Production: load the model and compute cross-attention scores.
        # For MVP, we simulate re-ranking by preserving the order but
        # adjusting scores to reflect "reranker" output.
        # Real implementation:
        # from FlagEmbedding import FlagReranker
        # reranker = FlagReranker(self.model_name, use_fp16=True)
        # pairs = [[query, r.content] for r in results]
        # scores = reranker.compute_score(pairs)
        # ...

        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        for i, r in enumerate(sorted_results):
            r.score = max(0.0, r.score - i * 0.02)
        return sorted_results
