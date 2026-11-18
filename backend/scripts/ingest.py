#!/usr/bin/env python3
"""运行文档入库流水线 —— 切分 → 落 PG → 向量化 → 向量(pgvector) + BM25。

用法：
    cd backend
    python scripts/ingest.py               # 增量入库
    python scripts/ingest.py --rebuild     # 清空重建
    python scripts/ingest.py --sync-db     # 仅把 data/ 文件同步到 PostgreSQL
    python scripts/ingest.py --check       # 检查索引是否就绪
"""

from __future__ import annotations

import argparse
import sys
import os

# 确保 backend/ 在 sys.path 上
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.ingestion import ingest, sync_db_all
from app.rag.bm25_store import bm25_store
from app.rag.ingestion import BM25_INDEX_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="CogniFlow RAG ingestion")
    parser.add_argument("--rebuild", action="store_true", help="Drop and re-ingest all documents")
    parser.add_argument("--check", action="store_true", help="Only check if ingestion is needed")
    parser.add_argument("--sync-db", action="store_true", help="Sync existing data files to PostgreSQL only")
    args = parser.parse_args()

    if args.check:
        bm25_ok = bm25_store.is_ready
        if bm25_ok:
            print("✓ BM25 index is ready")
        else:
            print(f"✗ BM25: {'ready' if bm25_ok else 'not ready'}")
            print("  Run: python scripts/ingest.py [--rebuild]")
        return

    if args.sync_db:
        print("Syncing data/ files to PostgreSQL…")
        stats = sync_db_all()
        print(f"Done: {stats['files']} files → {stats['documents']} documents, {stats['chunks']} chunks")
        return

    print("Ingesting documents…")
    stats = ingest(rebuild=args.rebuild)
    print(f"\nDone in {stats.get('elapsed_ms', 0)}ms:")
    print(f"  Files processed:  {stats['files']}")
    print(f"  Chunks created:   {stats['chunks']}")
    print(f"  Vectors embedded: {stats['embedded']}")
    print(f"  Vector rows:      {stats['milvus_count']}")
    print(f"  BM25 docs:        {stats['bm25_count']}")


if __name__ == "__main__":
    main()
