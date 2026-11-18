#!/usr/bin/env python3
"""导出知识库 chunk 清单，供人工标注评估集。

用法：
    cd backend
    python scripts/dump_chunks.py            # 导出到 eval/chunks_dump.jsonl
    python scripts/dump_chunks.py --limit 5  # 只看前 5 条预览

输出每条 chunk 的：
  - stable_id     稳定键（source_document#chunkN），rebuild 后不变，人工可读
  - db_chunk_id   PG 自增主键（跑分时对齐 BM25 与向量两侧用）
  - document      文档标题 / 类型
  - chunk_index   在文档内的序号
  - content_preview 内容前 120 字（用于写问题 + 判断答案）

前置条件：先跑 `python scripts/ingest.py --rebuild` 把数据写进 PostgreSQL。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path

# 确保 backend/ 在 sys.path 上
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.models.engine import async_session_factory

# 输出目录与文件
EVAL_DIR = Path(__file__).parent.parent / "eval"
OUT_PATH = EVAL_DIR / "chunks_dump.jsonl"


async def dump_chunks(limit: int | None = None) -> list[dict]:
    """从 PG 读出全部 chunk，返回带稳定键的记录列表。"""
    sql = """
        SELECT
            c.id            AS db_chunk_id,
            c.chunk_index   AS chunk_index,
            c.source_document AS source_document,
            c.content       AS content,
            d.title         AS document_title,
            d.file_type     AS file_type
        FROM knowledge_chunks c
        JOIN knowledge_documents d ON c.document_id = d.id
        WHERE c.source_document IS NOT NULL
        ORDER BY c.document_id, c.chunk_index
    """
    if limit:
        sql += " LIMIT :lim"

    params = {"lim": limit} if limit else {}
    async with async_session_factory() as session:
        result = await session.execute(text(sql), params)
        rows = result.fetchall()

    records: list[dict] = []
    for row in rows:
        # 稳定键公式必须与 ingestion.py 里 chunk_id 的生成公式完全一致：
        #   f"{source_document}#chunk{chunk_index}"
        stable_id = f"{row.source_document}#chunk{row.chunk_index}"
        records.append({
            "stable_id": stable_id,
            "db_chunk_id": row.db_chunk_id,
            "chunk_index": row.chunk_index,
            "document_title": row.document_title,
            "file_type": row.file_type,
            "content_preview": (row.content or "")[:120],
        })
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="导出知识库 chunk 清单")
    parser.add_argument("--limit", type=int, default=None, help="只导出前 N 条（用于预览）")
    parser.add_argument("--json", action="store_true", help="直接打印到 stdout 而非写文件")
    args = parser.parse_args()

    records = asyncio.run(dump_chunks(args.limit))

    if args.json or args.limit:
        # 预览模式：打印到屏幕
        for r in records:
            print(json.dumps(r, ensure_ascii=False))
        print(f"\n共 {len(records)} 条")
        return

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"已导出 {len(records)} 条 chunk → {OUT_PATH}")


if __name__ == "__main__":
    main()
