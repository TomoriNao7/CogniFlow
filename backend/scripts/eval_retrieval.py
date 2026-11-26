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

P3-C-1 Multi-Query 实验（同样只动本脚本）：
    multiquery_union:N ：原 query + N 个 LLM 改写变体各走向量检索，按「被几个变体命中」投票合并
    multiquery_rrf:N   ：同上，但用 RRF 名次融合
    为什么必须先测再决定：Multi-Query 增强的是**召回**，而当前四桶 Hit@5 已到 1.0，
    真瓶颈在排序精度；若测出来无差异，结论就是「测过并否决」，不写进简历。

P3-C-3 Query Rewrite 实验（同样只动本脚本，需要 --multiturn 加载多轮评估集）：
    qr:none    ：基线对照，不改写，直接拿当前轮问句检索
    qr:concat  ：零成本，把历史各轮问句与当前问句拼接成自包含问句
    qr:llm     ：让 LLM 依据历史把当前问句改写成自包含问句
    三档都走同一套 weighted 融合检索，所以差异只来自「查询改写」，不来自检索。
    为什么必须在多轮集上测：单轮集的每条问句本就自足，改写器只会原样返回，
    必然测出「无差异」，那是尺子量不到，不是 QR 没用。QR 治的是指代/省略/换主体。

P3-A 三个消融实验（只动本脚本，不碰线上代码）：
    1. 权重扫描   weighted:0.1 / 0.2 / 0.3 / 0.5 —— 找 bm25_weight 的最优点。
                  weighted:0.0 在排序上恒等于 vector，故不单列，直接用 vector 列当 w=0 的锚。
    2. RRF k 扫描 rrf:10 / 60 / 100 —— 确认 RRF 的「hit5 高、hit1 低」不是参数没调好。
    3. 精排消融   weighted:0.3+rerank —— 宽召回 WIDE_K 条 → 精排 → 截断 RECALL_K 条；
                  对照 weighted:0.3（不精排），差值即精排收益。

关于精排消融的口径（必须说清楚，否则数字会被误读）：
    本机 conda 环境**没有装 FlagEmbedding / torch**，`Reranker.rerank()` 会走
    `_score_rerank` 降级分支（按分排序 + 同源扣 0.03 + 位置衰减 0.01）。
    所以「+rerank」测的是**降级精排**的实际效果，不是 bge-reranker-v2-m3 交叉编码器的效果。
    要测真交叉编码器需先 `pip install FlagEmbedding torch`（约 2~3GB）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
import time
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
# 多轮评估集（C-2）：测 Query Rewrite 必须用它，单轮集的问句本就自足，测不出改写效果
MULTITURN_PATH = EVAL_DIR / "queries_multiturn.jsonl"

# 检索召回条数（四路统一，取这个数再算 Hit@5/MRR@10 等）
RECALL_K = 10

# 精排前先宽召回这么多条，精排后再截断回 RECALL_K
# 现在的线上是「融合后取 top-5 → 精排」，精排只能救回已经进前 5 的，顺序是倒的
WIDE_K = 20

# RRF 常数（默认值，实验里可覆盖）
RRF_K = 60

# 五桶
BUCKETS = ["单品属性", "促销与券", "政策条款", "售后流程", "跨实体规则"]

# 难度分层：easy 组已饱和，只有 hard 组能区分策略优劣，必须分开报
DIFFICULTIES = ["easy", "hard"]

# P3-A 默认跑的实验组：两组基线 + 权重扫描 + RRF k 扫描 + 精排消融
DEFAULT_STRATEGIES = [
    "bm25",
    "vector",
    "weighted:0.1",
    "weighted:0.2",
    "weighted:0.3",  # 当前线上取值
    "weighted:0.5",
    "rrf:10",
    "rrf:60",  # 当前 RRF 常数
    "rrf:100",
    "weighted:0.3+rerank",  # 宽召回 → 精排 → 截断
]


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


def load_multiturn_queries() -> list[dict]:
    """读取多轮评估集（C-2），字段校验与单轮集一致。

    多轮集比单轮集多了 `group` / `turn` / `history` / `answer_scope` /
    `depends_on`，Query Rewrite 用 `history` 改写当前问句，用 `answer_scope`
    判断这条 query 是否本就依赖前序轮次。
    """
    if not MULTITURN_PATH.exists():
        sys.exit(f"多轮评估集不存在：{MULTITURN_PATH}")
    qs = []
    with open(MULTITURN_PATH, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            q = json.loads(line)
            assert q.get("query"), f"第 {i} 行缺 query"
            assert q.get("relevant"), f"第 {i} 行缺 relevant"
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


# 查询向量缓存：同一条 query 会跑过十个策略，每次都重新算 embedding 就是十倍的网络调用
# （DashScope 单次 200~500ms，不缓存的话一轮要十几分钟）。向量与策略无关，缓存是安全的。
_QUERY_VEC_CACHE: dict[str, list[float]] = {}


def _query_vector(query: str) -> list[float]:
    """取查询向量，命中缓存直接返回。"""
    if query not in _QUERY_VEC_CACHE:
        _QUERY_VEC_CACHE[query] = embedder.embed_query(query)
    return _QUERY_VEC_CACHE[query]


async def vector_search(query: str, k: int = RECALL_K) -> list[tuple[int, float]]:
    hits = await vector_store.search(_query_vector(query), top_k=k)
    return [(int(h["entity"]["db_chunk_id"]), h["distance"]) for h in hits]


def _weighted_fusion(
    bm25: list[tuple[int, float]],
    vec: list[tuple[int, float]],
    bm25_weight: float | None = None,
) -> list[tuple[int, float]]:
    """加权融合，按 db_chunk_id 对齐（绕开线上 _fusion 的 chunk_id 不一致 bug）。

    两路权重互补（和为 1），权重扫描才是可比的插值：
    bm25_weight=0 时排序恒等于纯向量，=1 时恒等于纯 BM25。
    """
    w = settings.bm25_weight if bm25_weight is None else bm25_weight
    vw = 1.0 - w
    scores: dict[int, float] = {}
    for cid, s in bm25:
        scores[cid] = scores.get(cid, 0.0) + w * s
    for cid, s in vec:
        scores[cid] = scores.get(cid, 0.0) + vw * s
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _rrf_fusion(
    bm25: list[tuple[int, float]],
    vec: list[tuple[int, float]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """RRF 名次融合。rank 从 0 起。k 越小，靠前名次的权重越集中。"""
    scores: dict[int, float] = {}
    for rank, (cid, _) in enumerate(bm25):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    for rank, (cid, _) in enumerate(vec):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── Multi-Query（P3-C-1）────────────────────────────────────────────────────

# 变体缓存：同一条 query 会跑过多个 Multi-Query 策略（union/rrf × N），
# 不缓存的话每跑一个策略都要重新调 LLM，一轮评估的调用次数会翻好几倍。
_MQ_VARIANT_CACHE: dict[tuple[str, int], list[str]] = {}

# 累计成本：LLM 调用次数与总耗时，跑完要报，否则不知道这路便宜不便宜
_MQ_COST: dict[str, float] = {"calls": 0, "ms": 0.0}


async def _gen_variants(query: str, n: int) -> list[str]:
    """让 LLM 把一条问题改写成 n 个语义相同、措辞不同的问句。

    Multi-Query 治的是「用户措辞和文档措辞对不上」，
    所以要的是**换个说法**，不是补充条件、不是拆解问题。
    生成失败（网络/JSON 不合规）时返回空列表，退化为原 query 单路检索。
    """
    key = (query, n)
    if key in _MQ_VARIANT_CACHE:
        return _MQ_VARIANT_CACHE[key]

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    prompt = (
        f"把下面的电商客服问题改写成 {n} 个语义完全相同的问句，"
        "只换说法、不增加条件、不拆解、不解释，每条不超过 30 字。\n"
        '只输出 JSON：{"variants": ["...", "..."]}\n\n'
        f"问题：{query}"
    )
    t0 = time.time()
    try:
        resp = await client.chat.completions.create(
            model=settings.intent_model or settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            extra_body=settings.thinking_extra(False),
        )
        _MQ_COST["calls"] += 1
        _MQ_COST["ms"] += (time.time() - t0) * 1000
        raw = (resp.choices[0].message.content or "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        variants = [str(v).strip() for v in data.get("variants", []) if str(v).strip()]
    except Exception as exc:  # 变体生成失败不该让整轮评估崩掉
        print(f"[mq] 变体生成失败，退化为单路：{type(exc).__name__}: {exc}")
        variants = []

    variants = variants[:n]
    _MQ_VARIANT_CACHE[key] = variants
    return variants


async def _multiquery_search(
    query: str, n: int, mode: str, k: int = RECALL_K,
) -> list[tuple[int, float]]:
    """原问题 + n 个变体各自走向量检索，然后合并成一个排序。

    union：按「被几个变体命中」投票，票数相同再比最佳名次。
    rrf  ：把每个变体当成一条并列的召回通道，走名次融合。
    """
    variants = await _gen_variants(query, n)
    lists = [await vector_search(query, k=k)]
    for v in variants:
        lists.append(await vector_search(v, k=k))

    if mode == "rrf":
        scores: dict[int, float] = {}
        for lst in lists:
            for rank, (cid, _) in enumerate(lst):
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    votes: dict[int, int] = {}
    best_rank: dict[int, int] = {}
    for lst in lists:
        for rank, (cid, _) in enumerate(lst):
            votes[cid] = votes.get(cid, 0) + 1
            best_rank[cid] = min(best_rank.get(cid, 10**9), rank)
    ordered = sorted(votes, key=lambda cid: (-votes[cid], best_rank[cid]))
    return [(cid, float(votes[cid])) for cid in ordered]


# ── Query Rewrite（P3-C-3）──────────────────────────────────────────────────

# 改写缓存：同一条 (history, query, 档位) 只改写一次，多档策略共用结果
_QR_CACHE: dict[tuple[tuple[str, ...], str, str], tuple[str, float, int]] = {}

# 累计成本：LLM 调用次数与耗时，用来算「额外 P95 延迟」这条上线判据
_QR_COST: dict[str, float] = {"calls": 0.0, "ms": 0.0}


async def _rewrite_query(
    history: list[str], query: str, mode: str
) -> tuple[str, float, int]:
    """把多轮对话的当前问句改写成自包含的检索问句。

    三档：
        none   ：不改写，原样返回（基线对照）
        concat ：把历史各轮问句拼在当前问句前面，零成本、零调用
        llm    ：让 LLM 依据历史把当前问句改写成一句自包含问句

    返回 (改写后的问句, 本次耗时 ms, 是否触发 LLM 调用 0/1)。
    LLM 失败时降级回原 query，不让评估崩掉（这也是上线要求的降级路径）。
    """
    if mode == "none":
        return query, 0.0, 0

    if mode == "concat":
        # 拼接会把历史问句完整带进检索查询：零成本，但也会引入噪声，必须实测
        t0 = time.time()
        rewritten = " ".join(p for p in [*history, query] if p)
        return rewritten or query, (time.time() - t0) * 1000, 0

    if mode == "llm":
        key = (tuple(history), query, mode)
        if key in _QR_CACHE:
            return _QR_CACHE[key]

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
        context = "\n".join(f"用户：{h}" for h in history) if history else "（无历史对话）"
        prompt = (
            "你是电商客服的检索查询改写器。根据对话历史，把当前用户的问题改写成一句"
            "自包含、可直接用于检索的问句。\n"
            "要求：补齐历史里出现过的实体与指代，保持原问题意图，不要回答，不要解释。\n"
            "只输出改写后的问句本身，不超过 40 字。\n\n"
            f"对话历史：\n{context}\n\n当前问题：{query}"
        )
        t0 = time.time()
        try:
            resp = await client.chat.completions.create(
                model=settings.intent_model or settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                extra_body=settings.thinking_extra(False),
            )
            rewritten = (resp.choices[0].message.content or "").strip()
            calls = 1
        except Exception as exc:  # 改写失败不该让整轮评估崩掉
            print(f"[qr] 改写失败，降级为原 query：{type(exc).__name__}: {exc}")
            rewritten, calls = "", 0

        elapsed = (time.time() - t0) * 1000
        if not rewritten:
            rewritten = query  # 降级：至少保证检索仍能跑
        out = (rewritten, elapsed, calls)
        _QR_CACHE[key] = out
        _QR_COST["calls"] += calls
        _QR_COST["ms"] += elapsed
        return out

    raise ValueError(f"未知改写档位：{mode}")


def _parse_strategy(spec: str) -> tuple[str, float | str | None, str | None]:
    """解析策略名：'weighted:0.3+xrerank' → ('weighted', 0.3, 'cross')。

    语法：`<name>[:<param>][+rerank|+xrerank]`
      - weighted 的 param 是 bm25_weight
      - rrf 的 param 是 k
      - multiquery_union / multiquery_rrf 的 param 是变体个数 N（缺省 3）
      - qr 的 param 是改写档位 none / concat / llm（非数字，按字符串解析）
      - `+rerank`  走线上降级精排（同源多样性惩罚，脚本内复刻）
      - `+xrerank` 走真 cross-encoder（bge-reranker-v2-m3，需装 FlagEmbedding）
    """
    rerank_mode: str | None = None
    for suffix, mode in (("+xrerank", "cross"), ("+rerank", "fallback")):
        if spec.endswith(suffix):
            rerank_mode = mode
            spec = spec[: -len(suffix)]
            break
    name, _, param = spec.partition(":")
    if not param:
        return name, None, rerank_mode
    try:
        return name, float(param), rerank_mode
    except ValueError:
        # qr:concat 这类非数字参数按字符串原样返回
        return name, param, rerank_mode


def _fallback_rerank(
    ranked: list[tuple[int, float]],
    meta: dict[int, dict],
) -> list[tuple[int, float]]:
    """复刻 `Reranker._score_rerank` 的降级精排逻辑。

    本机没装 FlagEmbedding，线上跑的就是这一支，所以消融必须测它：
    按分降序 → 位置衰减 0.01 → 同源文档累进扣 0.03 → 重排。

    注意：位置衰减是单调的，不会改变顺序；真正会重排的只有「同源惩罚」——
    所以这一支的本质是**提升来源多样性**，不是提升语义相关性。
    """
    ordered = sorted(ranked, key=lambda x: x[1], reverse=True)
    seen: dict[str, int] = {}
    out: list[tuple[int, float]] = []
    for i, (cid, score) in enumerate(ordered):
        src = meta.get(cid, {}).get("source_document", "")
        penalty = seen.get(src, 0) * 0.03
        out.append((cid, round(max(0.0, score - i * 0.01 - penalty), 4)))
        seen[src] = seen.get(src, 0) + 1
    return sorted(out, key=lambda x: x[1], reverse=True)


_RERANKER = None


def _get_reranker():
    """复用同一个 Reranker 实例：交叉编码器加载要几秒，不能每条 query 重建。"""
    global _RERANKER
    if _RERANKER is None:
        from app.rag.reranker import Reranker
        _RERANKER = Reranker()
    return _RERANKER


async def _cross_rerank(
    query: str,
    ranked: list[tuple[int, float]],
    meta: dict[int, dict],
) -> list[tuple[int, float]]:
    """用真 cross-encoder 精排：tuple 列表与 RetrievalResult 互转。"""
    from app.rag.retriever import RetrievalResult

    reranker = _get_reranker()
    results = [
        RetrievalResult(
            chunk_id=str(cid),
            content=meta.get(cid, {}).get("content", ""),
            score=float(score),
            source_document=meta.get(cid, {}).get("source_document", ""),
            db_chunk_id=cid,
        )
        for cid, score in ranked
    ]
    reranked = await reranker.rerank(query, results)
    return [(r.db_chunk_id, r.score) for r in reranked]


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


async def eval_strategy(
    spec: str, queries: list[dict], meta: dict[int, dict], wide_k: int | None = None,
) -> dict:
    """对一组 query 跑指定策略，返回指标汇总。

    spec 语法见 `_parse_strategy`：`weighted:0.3` / `rrf:60` / `weighted:0.3+rerank`。
    所有策略最终都截断到 RECALL_K 条，保证指标口径一致。
    wide_k 覆盖精排前的宽召回条数：CPU 跑交叉编码器时按 token 数线性变慢，需要能调小。
    """
    name, param, rerank_mode = _parse_strategy(spec)
    # 走精排时先宽召回，精排后统一截断回 RECALL_K
    k = (wide_k or WIDE_K) if rerank_mode else RECALL_K

    per_q = []
    # Query Rewrite 的累计统计（改写成本与调用次数，用于算额外延迟判据）
    qr_stats = {"n": 0, "calls": 0, "ms": 0.0}
    for q in queries:
        # 相关 chunk 已在 resolve_qrels 阶段解析成 db_chunk_id
        relevant_db = set(q["relevant_db"])
        query = q["query"]
        # 只有 qr 策略会改写；其余策略原样使用当前问句
        rewritten, qr_ms, qr_calls = query, 0.0, 0

        if name == "bm25":
            ranked = bm25_search(query, k=k)
        elif name == "vector":
            ranked = await vector_search(query, k=k)
        elif name == "weighted":
            b = bm25_search(query, k=k)
            v = await vector_search(query, k=k)
            ranked = _weighted_fusion(b, v, param)
        elif name == "rrf":
            b = bm25_search(query, k=k)
            v = await vector_search(query, k=k)
            ranked = _rrf_fusion(b, v, int(param) if param is not None else RRF_K)
        elif name in ("multiquery_union", "multiquery_rrf"):
            # param 是变体个数 N；单路检索内部已按 k 取够，无需再融合 BM25
            n = int(param) if param is not None else 3
            mode = "rrf" if name.endswith("_rrf") else "union"
            ranked = await _multiquery_search(query, n, mode, k=k)
        elif name == "qr":
            # 查询改写：改写后仍走 weighted 融合，与基线的差异只来自查询本身
            mode = str(param) if param is not None else "none"
            rewritten, qr_ms, qr_calls = await _rewrite_query(
                q.get("history", []), query, mode
            )
            qr_stats["calls"] += qr_calls
            qr_stats["ms"] += qr_ms
            qr_stats["n"] += 1
            b = bm25_search(rewritten, k=k)
            v = await vector_search(rewritten, k=k)
            ranked = _weighted_fusion(b, v, None)
        else:
            raise ValueError(f"未知策略：{spec}")

        if rerank_mode == "fallback":
            ranked = _fallback_rerank(ranked, meta)
        elif rerank_mode == "cross":
            ranked = await _cross_rerank(query, ranked, meta)
        ranked = ranked[:RECALL_K]

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
            # Query Rewrite 明细：改写后的问句与本次改写耗时 / LLM 调用次数
            "rewritten_query": rewritten,
            "qr_ms": qr_ms,
            "qr_calls": qr_calls,
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

    return {
        "strategy": spec,
        "total": total,
        "by_bucket": by_bucket,
        "by_difficulty": by_difficulty,
        "multi": multi,
        "per_query": per_q,
        # Query Rewrite 统计：改写的 query 条数、LLM 调用次数、累计耗时
        "qr_stats": qr_stats,
    }


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
    # 列宽按最长策略名自适应，否则 weighted:0.1 这类名字会把表头挤成一坨
    cw = max(12, max(len(n) for n in names) + 2)
    lw = 12  # 行标签列宽

    header = f"{'指标':<{lw}}" + "".join(f"{n:>{cw}}" for n in names)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))
    for metric in ["hit1", "hit3", "hit5", "mrr10", "ndcg5", "recall5", "allrecall5"]:
        row = f"{metric:<{lw}}"
        for r in results:
            row += f"{r['total'][metric]:>{cw}.4f}"
        print(row)
    print("=" * len(header))

    # 分桶 Hit@5
    print("\n分桶 Hit@5：")
    for b in BUCKETS:
        row = f"  {b:<{lw - 2}}"
        for r in results:
            cell = r["by_bucket"].get(b)
            row += f"{(cell['hit5'] if cell else 0.0):>{cw}.4f}"
        print(row)

    # 多跳口径：只有标注 ≥2 个相关 chunk 的 query，才能看出「证据有没有凑齐」
    keys = ["overall"] + [f"bucket:{b}" for b in BUCKETS]
    keys = [k for k in keys if k in results[0]["multi"]]
    if keys:
        print("\n多跳口径（仅标注 ≥2 个相关 chunk 的 query）：")
        for metric in ["n", "hit5", "recall5", "allrecall5"]:
            for k in keys:
                row = f"  {k + '.' + metric:<{lw + 14}}"
                for r in results:
                    cell = r["multi"].get(k)
                    if cell is None:
                        row += f"{'—':>{cw}}"
                    elif metric == "n":
                        row += f"{cell['n']:>{cw}d}"
                    else:
                        row += f"{cell[metric]:>{cw}.4f}"
                print(row)


def _print_verdict(results: list[dict]) -> None:
    """P3-A 结论汇总：每个指标挑出最优策略，并给出与最差者的极差。

    表格能看出「谁高谁低」，但看不出「这个差距值不值得换」——
    极差就是判断依据：极差小于 1 条 query 的占比（1/83 ≈ 0.012）时，差异不可信。
    """
    print("\n" + "=" * 72)
    print("P3-A 结论：各指标最优策略")
    print("=" * 72)

    metrics = [
        ("单跳 Hit@1", "hit1"),
        ("MRR@10", "mrr10"),
        ("nDCG@5", "ndcg5"),
        ("Hit@5", "hit5"),
        ("recall@5", "recall5"),
        ("allrecall@5（全体）", "allrecall5"),
    ]
    for label, metric in metrics:
        best = max(results, key=lambda r: r["total"][metric])
        worst = min(r["total"][metric] for r in results)
        print(
            f"  {label:<22}{best['strategy']:<22}"
            f"{best['total'][metric]:.4f}   (极差 {best['total'][metric] - worst:+.4f})"
        )

    # 多跳子集：只有标注 ≥2 个相关 chunk 的 query 才有区分度
    multi = [
        (r["strategy"], r["multi"]["overall"]["allrecall5"])
        for r in results
        if "overall" in r["multi"]
    ]
    if multi:
        best_s, best_v = max(multi, key=lambda x: x[1])
        print(f"  {'allrecall@5（多跳子集）':<22}{best_s:<22}{best_v:.4f}")


def _print_qr_verdict(results: list[dict]) -> None:
    """P3-C-3 判据：Query Rewrite 相对 `qr:none` 基线的逐条对比。

    报四个数：
        changed_ratio —— 改写改变了 top-5 检索结果的 query 比例
                        （接近 0 说明改写根本没生效，谈不上收益）
        improved/worsened —— hit@1 相对基线的逐条升降条数
        p95_ms —— 改写本身的额外延迟（concat 应≈0，llm 才真正付费）

    上线判据（三条同时满足）：improved − worsened ≥ 4 条、额外 P95 < 300ms、
    失败能降级回原 query。任一不满足就记「已测并否决」，不写进简历。
    """
    qr = [r for r in results if r["strategy"].startswith("qr:")]
    base = next((r for r in qr if r["strategy"] == "qr:none"), None)
    if not qr or base is None:
        return

    b_by = {q["query"]: q for q in base["per_query"]}
    print("\n" + "=" * 72)
    print("P3-C-3 判据：Query Rewrite vs qr:none")
    print("=" * 72)
    print(
        f"  {'策略':<14}{'改写改变率':>12}{'hit@1 改善':>12}"
        f"{'hit@1 恶化':>12}{'额外 P95 ms':>14}"
    )
    for r in qr:
        if r["strategy"] == "qr:none":
            continue
        o_by = {q["query"]: q for q in r["per_query"]}
        changed = improved = worsened = 0
        for key, bq in b_by.items():
            oq = o_by.get(key)
            if oq is None:
                continue
            if bq["ranked"] != oq["ranked"]:
                changed += 1
            if oq["hit1"] > bq["hit1"]:
                improved += 1
            elif oq["hit1"] < bq["hit1"]:
                worsened += 1
        ms = sorted(oq["qr_ms"] for oq in r["per_query"] if oq["qr_ms"] > 0)
        p95 = ms[int(len(ms) * 0.95) - 1] if ms else 0.0
        calls = r["qr_stats"]["calls"]
        avg = (r["qr_stats"]["ms"] / calls) if calls else 0.0
        print(
            f"  {r['strategy']:<14}{changed / len(b_by):>12.3f}"
            f"{improved:>12d}{worsened:>12d}{p95:>14.0f}"
        )
        print(f"  {'':<14}LLM 调用 {calls} 次，平均 {avg:.0f} ms/次")


async def main() -> None:
    parser = argparse.ArgumentParser(description="四路检索基线跑分 + P3-A 消融实验")
    parser.add_argument(
        "--strategy", default=None,
        help="只跑指定策略，逗号分隔；如 weighted:0.1,rrf:60,weighted:0.3+rerank",
    )
    parser.add_argument("--json", action="store_true", help="输出完整 JSON")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="只跑前 N 条 query（多跳题优先保留）；交叉编码器在 CPU 上很慢时用来缩小样本",
    )
    parser.add_argument(
        "--wide-k", type=int, default=None,
        help="精排前宽召回条数，默认 20；CPU 环境下建议降到 5~10",
    )
    parser.add_argument(
        "--bucket", default=None,
        help="只跑指定分桶（如 单品属性）；配合 --limit 做分层抽样",
    )
    parser.add_argument(
        "--bm25-tokenizer", default=None,
        help="覆盖 BM25 分词器：char（单字）/ jieba（词典）/ bigram（二元组）",
    )
    parser.add_argument(
        "--multiturn", action="store_true",
        help="改用多轮评估集 queries_multiturn.jsonl，测 Query Rewrite 必须用它",
    )
    args = parser.parse_args()

    queries = load_multiturn_queries() if args.multiturn else load_queries()
    src = "多轮评估集" if args.multiturn else "单轮评估集"
    rows = await load_chunk_rows()
    queries, skipped = resolve_qrels(queries, rows)
    print(f"[eval] {src}：{src}{len(queries)} 条，索引中 {len(rows)} 个 chunk，标注解析后 {len(queries)} 条 query 有效\n")

    if args.bucket:
        queries = [q for q in queries if q.get("bucket") == args.bucket]
        print(f"[eval] --bucket 生效：{args.bucket}，{len(queries)} 条\n")

    if args.limit and args.limit < len(queries):
        # 多跳题（标注 ≥2 个相关 chunk）优先，其余按原顺序补齐：多跳是最需要精排的信号
        multi_first = sorted(queries, key=lambda q: len(q["relevant_db"]) < 2)
        queries = multi_first[: args.limit]
        print(f"[eval] --limit 生效：随机取 {len(queries)} 条（多跳优先）\n")

    # 精排降级分支要读 source_document 做同源惩罚，先把 id → 元数据建好
    meta = {r["db_chunk_id"]: r for r in rows}

    # 关键：eval 是独立进程，不会走 FastAPI lifespan，BM25 单例是空的，
    # 必须显式从 pickle 加载，否则 bm25_store.is_ready=False → _bm25_search 直接返回空 → BM25 全 0 分
    from app.rag.ingestion import BM25_INDEX_PATH
    if not bm25_store.is_ready:
        bm25_store.load(BM25_INDEX_PATH)
        print(f"[eval] 已加载 BM25 索引：{len(bm25_store)} docs\n")

    # 分词器实验：只读原文，重建语料与倒排，不需要重新入库
    if args.bm25_tokenizer:
        bm25_store.set_tokenizer(args.bm25_tokenizer)
    print(f"[eval] BM25 分词器：{bm25_store.tokenizer}（{len(bm25_store)} 条语料）\n")

    if args.strategy:
        strategies = [s.strip() for s in args.strategy.split(",") if s.strip()]
    else:
        strategies = list(DEFAULT_STRATEGIES)

    results = []
    for spec in strategies:
        r = await eval_strategy(spec, queries, meta, wide_k=args.wide_k)
        results.append(r)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_table(results)
        _print_verdict(results)
        _print_qr_verdict(results)
        note = f"[eval] 统计口径：{src} {len(queries)} 条有效 query"
        if skipped:
            note += f"（已剔除 {skipped} 条标注无法解析）"
        print(f"\n{note}")
        if _MQ_COST["calls"]:
            avg = _MQ_COST["ms"] / _MQ_COST["calls"]
            cached = len(_MQ_VARIANT_CACHE)
            print(
                f"[eval] Multi-Query 成本：LLM 调用 {int(_MQ_COST['calls'])} 次，"
                f"平均 {avg:.0f} ms/次，缓存 {cached} 条 query 的变体"
                f"（命中缓存的策略不重复计费）"
            )
        if _QR_COST["calls"]:
            avg = _QR_COST["ms"] / _QR_COST["calls"]
            print(
                f"[eval] Query Rewrite 成本：LLM 调用 {int(_QR_COST['calls'])} 次，"
                f"平均 {avg:.0f} ms/次，缓存 {len(_QR_CACHE)} 条改写结果"
                f"（命中缓存的策略不重复计费）"
            )


if __name__ == "__main__":
    asyncio.run(main())
