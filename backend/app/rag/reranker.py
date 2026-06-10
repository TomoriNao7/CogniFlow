"""Cross-encoder reranker. Uses bge-reranker-v2-m3 when available, falls back to score-based ranking."""

from __future__ import annotations

from app.rag.retriever import RetrievalResult
from app.config import settings


class Reranker:
    """Re-ranks retrieval results by relevance.

    Priority:
      1. bge-reranker-v2-m3 via FlagEmbedding (if installed and GPU available)
      2. Score-based fallback with duplication-aware weighting
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model
        self._reranker = None

    def _try_load_flag(self) -> None:
        """Lazy load FlagEmbedding reranker if available."""
        if self._reranker is not None:
            return
        try:
            from FlagEmbedding import FlagReranker
            self._reranker = FlagReranker(
                self.model_name,
                use_fp16=True,
                device=settings.reranker_device,
            )
        except ImportError:
            self._reranker = False  # mark as unavailable
        except Exception:
            self._reranker = False

    async def rerank(
        self, query: str, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Re-rank results by cross-encoder or score-based fallback."""
        if not results:
            return results

        self._try_load_flag()

        if self._reranker and self._reranker is not False:
            return self._flag_rerank(query, results)
        return self._score_rerank(results)

    def _flag_rerank(
        self, query: str, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Use FlagEmbedding cross-encoder for re-ranking."""
        pairs = [[query, r.content] for r in results]
        scores = self._reranker.compute_score(pairs, normalize=True)

        if isinstance(scores, float):
            scores = [scores]

        for r, s in zip(results, scores):
            r.score = round(float(s), 4)

        return sorted(results, key=lambda r: r.score, reverse=True)

    def _score_rerank(
        self, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Fallback score-based re-ranking with diversity boost.

        Slightly penalizes duplicate content from the same source document
        to favor diverse results across different knowledge sources.
        """
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        seen_sources: dict[str, int] = {}
        for i, r in enumerate(sorted_results):
            src = r.source_document
            penalty = seen_sources.get(src, 0) * 0.03
            r.score = round(max(0.0, r.score - i * 0.01 - penalty), 4)
            seen_sources[src] = seen_sources.get(src, 0) + 1

        return sorted(sorted_results, key=lambda r: r.score, reverse=True)
