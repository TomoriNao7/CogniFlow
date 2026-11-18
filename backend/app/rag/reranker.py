"""Cross-encoder 精排：能用 bge-reranker-v2-m3 就用，否则退化为按 score 排序。"""

from __future__ import annotations

from app.rag.retriever import RetrievalResult
from app.config import settings


class Reranker:
    """对检索结果按相关性精排。

    优先级：
      1. FlagEmbedding 的 bge-reranker-v2-m3（已安装且有 GPU 时）
      2. fallback：按 score 排序，并做重复内容加权
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model
        self._reranker = None

    def _try_load_flag(self) -> None:
        """按需加载 FlagEmbedding reranker，装不上就跳过。"""
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
            self._reranker = False  # 标记为不可用
        except Exception:
            self._reranker = False

    async def rerank(
        self, query: str, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """精排：优先 cross-encoder，否则走 score fallback。"""
        if not results:
            return results

        self._try_load_flag()

        if self._reranker and self._reranker is not False:
            return self._flag_rerank(query, results)
        return self._score_rerank(results)

    def _flag_rerank(
        self, query: str, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """用 FlagEmbedding cross-encoder 精排。"""
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
        """fallback：按 score 排序，并对重复内容做多样性加权。

        同一源文档的重复内容小幅扣分，让结果更多样。
        """
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        seen_sources: dict[str, int] = {}
        for i, r in enumerate(sorted_results):
            src = r.source_document
            penalty = seen_sources.get(src, 0) * 0.03
            r.score = round(max(0.0, r.score - i * 0.01 - penalty), 4)
            seen_sources[src] = seen_sources.get(src, 0) + 1

        return sorted(sorted_results, key=lambda r: r.score, reverse=True)
