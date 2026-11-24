"""检索一致性闸门：比对线上 HybridRetriever 与评估脚本的融合结果。

为什么需要它：评估脚本为了做消融，自己实现了一份融合逻辑；线上另有
一份。如果两边结果不同，那么所有检索实验的结论都不能搬到线上——测的
不是同一个东西。本脚本对评估集逐条比对两边的 db_chunk_id 序列，只要
有一条不一致就 exit 1，后续实验不得基于它出结论。

用法（在 backend 目录下）：
    python scripts/check_retriever_parity.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

import eval_retrieval as er  # noqa: E402
from app.rag.bm25_store import bm25_store  # noqa: E402
from app.rag.ingestion import BM25_INDEX_PATH  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402


async def main() -> int:
    # 评估脚本是独立进程，不走 FastAPI 的 lifespan，BM25 索引要手动加载
    if not bm25_store.is_ready:
        bm25_store.load(BM25_INDEX_PATH)
        print(f"[parity] 已加载 BM25 索引：{len(bm25_store)} docs")

    queries = er.load_queries()
    rows = await er.load_chunk_rows()
    queries, skipped = er.resolve_qrels(queries, rows)
    print(f"[parity] 有效 query {len(queries)} 条（剔除 {skipped} 条标注失效）")
    if not queries:
        print("[parity] 没有有效 query，先跑 dump_chunks.py 与重标")
        return 1

    retriever = HybridRetriever()
    print(
        f"[parity] 线上参数：bm25_weight={retriever.bm25_weight} "
        f"vector_weight={retriever.vector_weight} top_k={retriever.top_k}"
    )

    mismatches: list[tuple[str, list[int], list[int]]] = []
    for q in queries:
        prod = await retriever.retrieve(q["query"])
        prod_ids = [r.db_chunk_id for r in prod]

        bm25 = er.bm25_search(q["query"], er.RECALL_K)
        vec = await er.vector_search(q["query"], er.RECALL_K)
        fused = er._weighted_fusion(bm25, vec)[: retriever.top_k]
        eval_ids = [cid for cid, _ in fused]

        if prod_ids != eval_ids:
            mismatches.append((q["query"], prod_ids, eval_ids))

    if mismatches:
        print(f"[parity] 不一致 {len(mismatches)}/{len(queries)} 条")
        for query, prod_ids, eval_ids in mismatches[:5]:
            print(f"  query: {query}")
            print(f"    线上: {prod_ids}")
            print(f"    评估: {eval_ids}")
        return 1

    print(f"[parity] 全部一致：{len(queries)} 条 query 的 top-{retriever.top_k} 序列逐位相同")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
