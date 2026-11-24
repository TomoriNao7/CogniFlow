"""Cross-encoder 精排：开启时用 bge-reranker-v2-m3，否则不改变顺序。"""

from __future__ import annotations

import logging

from app.config import settings
from app.rag.retriever import RetrievalResult

logger = logging.getLogger(__name__)


class Reranker:
    """对检索结果按相关性精排。

    三种状态，`mode` 会如实报告是哪一种：
      - off      ：开关关闭，原序返回（默认）
      - cross    ：cross-encoder 真实打分
      - fallback ：加载或推理失败，退化为分数 + 同源多样性

    默认关闭的原因：83 条全量实测，交叉编码器用 5 条 hit@1 换 4 条
    allrecall@5，而下游只读 top-5，性价比为负；CPU 上还要 24s/query。
    """

    # 进程内共享已加载的模型：三个 agent 各建一个实例，
    # 不共享的话会把 2GB 权重重复加载三遍。
    _shared_model = None
    _shared_error: str | None = None
    _shared_tried = False

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model
        self._reranker = None
        self.load_error: str | None = None

    @property
    def is_available(self) -> bool:
        """是否真的加载上了 cross-encoder（而不是降级分支）。"""
        self._try_load_flag()
        return bool(self._reranker)

    @property
    def mode(self) -> str:
        """当前实际生效的方式：off / cross / fallback。

        链路里必须能回答「这次到底精排了没有」——之前 trace 记的是配置
        里的模型名，配置写着 bge-reranker，实际跑的是降级分支。
        """
        if not settings.reranker_enabled:
            return "off"
        self._try_load_flag()
        return "cross" if self._reranker else "fallback"

    def _try_load_flag(self) -> None:
        """按需加载 FlagEmbedding reranker，失败则记录原因后降级。"""
        cls = type(self)
        if cls._shared_tried:
            self._reranker = cls._shared_model
            self.load_error = cls._shared_error
            return
        cls._shared_tried = True

        device = settings.reranker_device
        # fp16 只在 GPU 上有意义：CPU 上大量算子没有半精度实现，强行开会报错
        use_fp16 = device != "cpu"
        try:
            from FlagEmbedding import FlagReranker

            model = FlagReranker(
                self.model_name,
                use_fp16=use_fp16,
                device=device,
            )
            cls._shared_model = model
            self._reranker = model
            logger.info(
                "reranker 已加载：%s（device=%s, fp16=%s）",
                self.model_name, device, use_fp16,
            )
        except ImportError as exc:
            cls._shared_error = f"FlagEmbedding 未安装：{exc}"
            self.load_error = cls._shared_error
            logger.warning("reranker 降级：%s", self.load_error)
        except Exception as exc:
            cls._shared_error = f"{type(exc).__name__}: {exc}"
            self.load_error = cls._shared_error
            logger.warning("reranker 加载失败，已降级：%s", self.load_error)

    async def rerank(
        self, query: str, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """精排：开关关掉时原序返回，否则 cross-encoder 优先、降级兜底。"""
        if not results:
            return results

        # 关闭时不动排序：融合结果已按分数降序，保持原样即「不精排」
        if not settings.reranker_enabled:
            return results

        self._try_load_flag()

        if self._reranker:
            try:
                return self._flag_rerank(query, results)
            except Exception as exc:
                logger.warning(
                    "reranker 推理失败，本次降级：%s: %s",
                    type(exc).__name__, exc,
                )
        return self._score_rerank(results)

    def _flag_rerank(
        self, query: str, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """用 FlagEmbedding cross-encoder 精排。"""
        pairs = [[query, r.content] for r in results]
        scores = self._reranker.compute_score(pairs, normalize=True)

        if isinstance(scores, (int, float)):
            scores = [scores]

        for r, s in zip(results, scores):
            r.score = round(float(s), 4)

        return sorted(results, key=lambda r: r.score, reverse=True)

    def _score_rerank(
        self, results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """fallback：按 score 排序，并对同源重复内容做多样性惩罚。

        位置衰减是单调的、不会改变顺序；真正会重排的只有同源惩罚。
        注意它会打散同一文档的多个 chunk，而多跳问题恰恰需要这些
        chunk 同时留在 top-k 里。
        """
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        seen_sources: dict[str, int] = {}
        for i, r in enumerate(sorted_results):
            src = r.source_document
            penalty = seen_sources.get(src, 0) * 0.03
            r.score = round(max(0.0, r.score - i * 0.01 - penalty), 4)
            seen_sources[src] = seen_sources.get(src, 0) + 1

        return sorted(sorted_results, key=lambda r: r.score, reverse=True)
