"""对比两路检索「串行」与「并发」的耗时，量化 P3-B 步骤 4 的收益。

做法：同一批 query，分别按「先 BM25 再向量」和「asyncio.gather」跑一遍，
取 P50 / P95。注意这是本机 CPU + 本地 PG 的数字，线上会受网络影响更大。
"""

from __future__ import annotations

import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cogniflow"
)

from app.rag.bm25_store import bm25_store  # noqa: E402
from app.rag.ingestion import BM25_INDEX_PATH  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402

QUERIES = [
    "iPhone 15 Pro 多少钱",
    "AirPods Pro 2 支持主动降噪吗",
    "手机激活后还能退货吗",
    "PLUS 会员的 95 折能和优惠券叠加吗",
    "退款多久能到账",
    "保价期限是多久",
    "机械键盘 K8 Pro 支持 Mac 吗",
    "以旧换新怎么估价",
    "预售定金能退吗",
    "发票内容能写办公用品吗",
]


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))
    return ordered[idx]


async def serial(r: HybridRetriever, q: str) -> None:
    await r._bm25_search(q)
    await r._vector_search(q)


async def concurrent(r: HybridRetriever, q: str) -> None:
    await asyncio.gather(r._bm25_search(q), r._vector_search(q))


async def main() -> None:
    if not bm25_store.is_ready:
        bm25_store.load(BM25_INDEX_PATH)
    r = HybridRetriever()

    # 预热：首次会建连接池、加载模型
    await concurrent(r, QUERIES[0])

    serial_ms: list[float] = []
    concurrent_ms: list[float] = []
    for round_idx in range(2):
        for q in QUERIES:
            t0 = time.monotonic()
            await serial(r, q)
            serial_ms.append((time.monotonic() - t0) * 1000)

            t0 = time.monotonic()
            await concurrent(r, q)
            concurrent_ms.append((time.monotonic() - t0) * 1000)

    print(f"样本 {len(serial_ms)} 次（{len(QUERIES)} 条 query × 2 轮）")
    print(f"串行  P50 {pct(serial_ms, 0.50):7.1f}ms  P95 {pct(serial_ms, 0.95):7.1f}ms  均值 {statistics.mean(serial_ms):7.1f}ms")
    print(f"并发  P50 {pct(concurrent_ms, 0.50):7.1f}ms  P95 {pct(concurrent_ms, 0.95):7.1f}ms  均值 {statistics.mean(concurrent_ms):7.1f}ms")
    gain = statistics.mean(serial_ms) - statistics.mean(concurrent_ms)
    print(f"收益  均值省 {gain:.1f}ms（{gain / statistics.mean(serial_ms) * 100:.0f}%）")


if __name__ == "__main__":
    asyncio.run(main())
