#!/usr/bin/env python3
"""四路检索基线跑分。

用法：
    cd backend
    python scripts/eval_retrieval.py                 # 跑全部四路 + 输出指标表
    python scripts/eval_retrieval.py --strategy rrf  # 只跑一路（bm25/vector/weighted/rrf）

前置条件：
    1. 已跑 ingest 写入数据
    2. eval/queries.jsonl 评估集已就绪（人工标注过相关 chunk）

评估集 queries.jsonl 每行一条：
    {
      "query": "iPhone 15 Pro 多少钱",
      "bucket": "单品属性",              # 五桶之一
      "difficulty": "easy",               # easy / hard，缺省 easy
      "relevant": [                        # 人工标注的相关 chunk
        {"doc": "pre_sales / 商品目录完整版", "anchor": "### iPhone 15 Pro Max"}
      ]
    }

标注不绑 chunk 序号，而用「文档 + 锚点行」：序号会随切分策略重排，
锚点行只要还在文档里，标注就一直有效（A/B 两组共用同一份评估集的前提）。

指标：
    Hit@k    ：前 k 条里是否命中 ≥1 个相关 chunk（按 query 求均值）
    MRR@k    ：首个相关 chunk 的倒数名次的均值
    nDCG@k   ：二值 gain 的折损累计增益（相关=1，不相关=0）
    recall@5 ：top-5 覆盖了「相关 chunk 总数」的多少比例（部分分）
    allrecall@5：top-5 是否覆盖了**全部**相关 chunk（多跳问题凑齐证据才算 1）

关于 allrecall@5 为什么必须单独报：
    Hit@5 对多跳问题太宽松 —— 一条 query 标了 2 个相关 chunk，命中 1 个就算满分，
    于是「证据有没有凑齐」被完全掩盖。多跳口径只在标注 ≥2 个相关 chunk 的
    query 上统计，单相关 chunk 的 query 上 allrecall 恒等于 Hit@5，混进来只会稀释信号。

四路策略：
    bm25     ：纯 BM25 关键词
    vector   ：纯 pgvector 余弦
    weighted ：加权融合（0.3*bm25 + 0.7*vector），按 db_chunk_id 对齐（绕开线上 _fusion 的 chunk_id 不一致 bug）
    rrf      ：RRF(k=60) 名次融合，只看名次不看分数
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
from collections import defaultdict
from pathlib import Path

# 确保 backend/ 在 sys.path 上
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text as sql_text

from app.config import settings
from app.models.engine import async_session_factory
from app.rag.embedder import embedder
from app.rag.vector_store import vector_store
from app.rag.bm25_store import bm25_store

EVAL_DIR = Path(__file__).parent.parent / "eval"
QUERIES_PATH = EVAL_DIR / "queries.jsonl"

# 检索召回条数（四路统一，取这个数再算 Hit@5/MRR@10 等）
RECALL_K = 10

# RRF 常数
RRF_K = 60

# 五桶
BUCKETS = ["单品属性", "促销与券", "政策条款", "售后流程", "跨实体规则"]

# 难度分层：easy 组已饱和，只有 hard 组能区分策略优劣，必须分开报
DIFFICULTIES = ["easy", "hard"]


# ── 数据加载 ───────────────────────────────────────────────────────────────────


def load_queries() -> list[dict]:
    """读取评估集，校验字段。"""
    if not QUERIES_PATH.exists():
        sys.exit(f"评估集不存在：{QUERIES_PATH}\n先跑 dump_chunks.py，再按模板写 queries.jsonl")
    qs = []
    with open(QUERIES_PATH, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            q = json.loads(line)
            assert q.get("query"), f"第 {i} 行缺 query"
            assert q.get("relevant"), f"第 {i} 行缺 relevant"
            # 旧格式没有 difficulty 字段，默认按 easy 处理
            q.setdefault("difficulty", "easy")
            qs.append(q)
    return qs


async def load_chunk_rows() -> list[dict]:
    """从 PG 直接读全部 chunk 的 id / 来源文档 / 正文。

    标注解析要用正文做锚点匹配，所以不能只读 dump 文件里的 120 字预览。
    """
    stmt = sql_text(
        "SELECT id, source_document, content FROM knowledge_chunks "
        "WHERE source_document IS NOT NULL"
    )
    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).fetchall()
    return [
        {
            "db_chunk_id": r.id,
            "source_document": r.source_document,
            "content": r.content or "",
        }
        for r in rows
    ]


def resolve_qrels(
    queries: list[dict], rows: list[dict]
) -> tuple[list[dict], int]:
    """把「文档 + 锚点行」标注解析成 db_chunk_id，返回 (有效 query, 被剔除条数)。

    标注**不绑 chunk 序号**：`source_document#chunkN` 里的 N 会随切分策略重排，
    一改切分旧标注就集体失效（表现为全 0 分，看起来像检索崩了）。
    改用「文档 + 锚点行」——只要那一行还在这篇文档的某个 chunk 里，标注就依然成立。

    锚点用整行精确匹配（`line.strip() == anchor`），不用子串包含，
    否则 `### iPhone 15` 会误命中 `### iPhone 15 Pro Max` 所在的 chunk。
    """
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_doc[r["source_document"]].append(r)

    valid: list[dict] = []
    skipped = 0
    problems: list[str] = []

    for q in queries:
        ids: list[int] = []
        ok = True
        for ref in q["relevant"]:
            doc, anchor = ref["doc"], ref["anchor"]
            cands = [
                r
                for r in by_doc.get(doc, [])
                if anchor in {ln.strip() for ln in r["content"].splitlines()}
            ]
            if len(cands) == 1:
                ids.append(cands[0]["db_chunk_id"])
            elif not cands:
                problems.append(f"锚点未命中：{doc} | {anchor}")
                ok = False
            else:
                problems.append(
                    f"锚点命中 {len(cands)} 个 chunk（歧义，需换更具体的锚点）：{doc} | {anchor}"
                )
                ok = False

        if ok and ids:
            valid.append({**q, "relevant_db": sorted(set(ids))})
        else:
            skipped += 1

    if skipped:
        print(f"[eval] ⚠ 已剔除 {skipped}/{len(queries)} 条标注无法解析的 query")
        for p in problems[:8]:
            print(f"[eval]   {p}")
        if not valid:
            sys.exit(
                "[eval] 全部 query 的相关 chunk 都无法解析 —— 不是检索效果差，是标注与索引不匹配。\n"
                "[eval] 检查锚点行是否仍存在于对应文档（切分/文档改名都会导致失效）"
            )
    return valid, skipped


# ── 四路检索（都返回 [(db_chunk_id, score)]，按分降序）────────────────────────


def bm25_search(query: str, k: int = RECALL_K) -> list[tuple[int, float]]:
    hits = bm25_store.search(query, top_k=k)
    return [(doc.db_chunk_id, score) for doc, score in hits]


async def vector_search(query: str, k: int = RECALL_K) -> list[tuple[int, float]]:
    qv = embedder.embed_query(query)
    hits = await vector_store.search(qv, top_k=k)
    return [(int(h["entity"]["db_chunk_id"]), h["distance"]) for h in hits]


def _weighted_fusion(bm25: list[tuple[int, float]], vec: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """加权融合，按 db_chunk_id 对齐（绕开线上 _fusion 的 chunk_id 不一致 bug）。"""
    scores: dict[int, float] = {}
    for cid, s in bm25:
        scores[cid] = scores.get(cid, 0.0) + settings.bm25_weight * s
    for cid, s in vec:
        scores[cid] = scores.get(cid, 0.0) + settings.vector_weight * s
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _rrf_fusion(bm25: list[tuple[int, float]], vec: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """RRF(k=60) 名次融合。rank 从 0 起。"""
    scores: dict[int, float] = {}
    for rank, (cid, _) in enumerate(bm25):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, (cid, _) in enumerate(vec):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── 指标 ───────────────────────────────────────────────────────────────────────


def hit_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    return 1.0 if any(cid in relevant for cid in ranked[:k]) else 0.0


def mrr(ranked: list[int], relevant: set[int], k: int = RECALL_K) -> float:
    for i, cid in enumerate(ranked[:k], 1):
        if cid in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    """二值 gain：相关=1，不相关=0。理想 DCG = 前 min(k, |relevant|) 位都是 1。"""
    gains = [1.0 if cid in relevant else 0.0 for cid in ranked[:k]]
    dcg = sum(g / _log2(i + 2) for i, g in enumerate(gains))  # i+2 因为 rank 从 0 起、位置从 1 起
    ideal_n = min(k, len(relevant))
    ideal_dcg = sum(1.0 / _log2(i + 1) for i in range(1, ideal_n + 1))
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def _log2(x: int) -> float:
    import math
    return math.log2(x)


def recall_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    """部分召回率：top-k 覆盖了「相关 chunk 总数」的多少比例。

    多跳问题用它看「差几块」——all-recall 只知道没凑齐，recall 知道凑了几成。
    """
    if not relevant:
        return 0.0
    got = sum(1 for cid in ranked[:k] if cid in relevant)
    return got / len(relevant)


def all_recall_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    """全命中率：只有 top-k 覆盖了**全部**相关 chunk 才算 1。

    为什么必须单独有这个指标：Hit@k 对多跳问题太宽松 ——
    一条 query 标了 2 个相关 chunk，命中 1 个就算满分，
    于是「证据是否凑齐」这个真正决定答案对错的问题被完全掩盖。
    """
    if not relevant:
        return 0.0
    return 1.0 if relevant.issubset(set(ranked[:k])) else 0.0


# ── 单策略评估 ─────────────────────────────────────────────────────────────────


async def eval_strategy(name: str, queries: list[dict]) -> dict:
    """对一组 query 跑指定策略，返回指标汇总。"""
    per_q = []
    for q in queries:
        # 相关 chunk 已在 resolve_qrels 阶段解析成 db_chunk_id
        relevant_db = set(q["relevant_db"])
        if name == "bm25":
            ranked = bm25_search(q["query"])
        elif name == "vector":
            ranked = await vector_search(q["query"])
        elif name == "weighted":
            b = bm25_search(q["query"])
            v = await vector_search(q["query"])
            ranked = _weighted_fusion(b, v)
        elif name == "rrf":
            b = bm25_search(q["query"])
            v = await vector_search(q["query"])
            ranked = _rrf_fusion(b, v)
        else:
            raise ValueError(name)

        ids = [cid for cid, _ in ranked]
        per_q.append({
            "query": q["query"],
            "bucket": q["bucket"],
            "difficulty": q["difficulty"],
            "relevant_db": sorted(relevant_db),
            "nrel": len(relevant_db),
            "ranked": ids,
            "hit1": hit_at_k(ids, relevant_db, 1),
            "hit3": hit_at_k(ids, relevant_db, 3),
            "hit5": hit_at_k(ids, relevant_db, 5),
            "mrr10": mrr(ids, relevant_db, 10),
            "ndcg5": ndcg_at_k(ids, relevant_db, 5),
            "recall5": recall_at_k(ids, relevant_db, 5),
            "allrecall5": all_recall_at_k(ids, relevant_db, 5),
        })

    # 总体指标
    n = len(per_q)
    total = {
        "hit1": sum(x["hit1"] for x in per_q) / n,
        "hit3": sum(x["hit3"] for x in per_q) / n,
        "hit5": sum(x["hit5"] for x in per_q) / n,
        "mrr10": sum(x["mrr10"] for x in per_q) / n,
        "ndcg5": sum(x["ndcg5"] for x in per_q) / n,
        "recall5": sum(x["recall5"] for x in per_q) / n,
        "allrecall5": sum(x["allrecall5"] for x in per_q) / n,
    }

    # 多跳口径：只在「标注 ≥2 个相关 chunk」的 query 上算
    multi: dict[str, dict] = {}
    for label, key, values in (
        ("overall", None, [None]),
        ("bucket", "bucket", BUCKETS),
        ("difficulty", "difficulty", DIFFICULTIES),
    ):
        for v in values:
            g = _multi_stats(per_q, key, v)
            if g:
                multi[f"{label}:{v}" if v else label] = g

    by_bucket = {}
    for b in BUCKETS:
        g = _group(per_q, "bucket", b)
        if g:
            by_bucket[b] = g

    # 难度分层：easy 组已饱和，diff 只在 hard 组看得出来
    by_difficulty = {}
    for d in DIFFICULTIES:
        g = _group(per_q, "difficulty", d)
        if g:
            by_difficulty[d] = g

    return {"strategy": name, "total": total, "by_bucket": by_bucket,
            "by_difficulty": by_difficulty, "multi": multi, "per_query": per_q}


def _multi_stats(per_q: list[dict], key: str | None = None, value: str | None = None) -> dict | None:
    """只在「标注 ≥2 个相关 chunk」的 query 上算多跳指标。

    为什么要过滤：单相关 chunk 的 query 上 all-recall 恒等于 hit@5，
    混进来只会把多跳信号稀释掉 —— 而这正是当前唯一有区分度的信号。
    """
    qs = [x for x in per_q if x["nrel"] >= 2]
    if key:
        qs = [x for x in qs if x[key] == value]
    if not qs:
        return None
    m = len(qs)
    return {
        "n": m,
        "hit5": sum(x["hit5"] for x in qs) / m,
        "recall5": sum(x["recall5"] for x in qs) / m,
        "allrecall5": sum(x["allrecall5"] for x in qs) / m,
    }


def _group(per_q: list[dict], key: str, value: str) -> dict | None:
    """按字段分组算 hit5 / mrr10 / ndcg5，组内为空返回 None。"""
    qs = [x for x in per_q if x[key] == value]
    if not qs:
        return None
    m = len(qs)
    return {
        "n": m,
        "hit1": sum(x["hit1"] for x in qs) / m,
        "hit5": sum(x["hit5"] for x in qs) / m,
        "mrr10": sum(x["mrr10"] for x in qs) / m,
        "ndcg5": sum(x["ndcg5"] for x in qs) / m,
        "recall5": sum(x["recall5"] for x in qs) / m,
        "allrecall5": sum(x["allrecall5"] for x in qs) / m,
    }


# ── 主流程 ─────────────────────────────────────────────────────────────────────


def _print_table(results: list[dict]) -> None:
    names = [r["strategy"] for r in results]
    header = f"{'指标':<10}" + "".join(f"{n:>12}" for n in names)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))
    for metric in ["hit1", "hit3", "hit5", "mrr10", "ndcg5", "recall5", "allrecall5"]:
        row = f"{metric:<10}"
        for r in results:
            row += f"{r['total'][metric]:>12.4f}"
        print(row)
    print("=" * len(header))

    # 分桶 Hit@5
    print("\n分桶 Hit@5：")
    for b in BUCKETS:
        row = f"  {b:<12}"
        for r in results:
            cell = r["by_bucket"].get(b)
            row += f"{(cell['hit5'] if cell else 0.0):>12.4f}"
        print(row)

    # 多跳口径：只有标注 ≥2 个相关 chunk 的 query，才能看出「证据有没有凑齐」
    keys = ["overall"] + [f"bucket:{b}" for b in BUCKETS]
    keys = [k for k in keys if k in results[0]["multi"]]
    if keys:
        print("\n多跳口径（仅标注 ≥2 个相关 chunk 的 query）：")
        for metric in ["n", "hit5", "recall5", "allrecall5"]:
            for k in keys:
                row = f"  {k + '.' + metric:<26}"
                for r in results:
                    cell = r["multi"].get(k)
                    if cell is None:
                        row += f"{'—':>12}"
                    elif metric == "n":
                        row += f"{cell['n']:>12d}"
                    else:
                        row += f"{cell[metric]:>12.4f}"
                print(row)


async def main() -> None:
    parser = argparse.ArgumentParser(description="四路检索基线跑分")
    parser.add_argument("--strategy", choices=["bm25", "vector", "weighted", "rrf"],
                        default=None, help="只跑一路")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON")
    args = parser.parse_args()

    queries = load_queries()
    rows = await load_chunk_rows()
    queries, skipped = resolve_qrels(queries, rows)
    print(f"[eval] 索引中 {len(rows)} 个 chunk，标注解析后 {len(queries)} 条 query 有效\n")

    # 关键：eval 是独立进程，不会走 FastAPI lifespan，BM25 单例是空的，
    # 必须显式从 pickle 加载，否则 bm25_store.is_ready=False → _bm25_search 直接返回空 → BM25 全 0 分
    from app.rag.ingestion import BM25_INDEX_PATH
    if not bm25_store.is_ready:
        bm25_store.load(BM25_INDEX_PATH)
        print(f"[eval] 已加载 BM25 索引：{len(bm25_store)} docs\n")

    strategies = [args.strategy] if args.strategy else ["bm25", "vector", "weighted", "rrf"]

    results = []
    for name in strategies:
        r = await eval_strategy(name, queries)
        results.append(r)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_table(results)
        note = f"[eval] 统计口径：{len(queries)} 条有效 query"
        if skipped:
            note += f"（已剔除 {skipped} 条标注无法解析）"
        print(f"\n{note}")


if __name__ == "__main__":
    asyncio.run(main())
