#!/usr/bin/env python3
"""Run the document ingestion pipeline — split → embed → store in Milvus + BM25.

Usage:
    cd backend
    python scripts/ingest.py             # incremental (skip if already ingested)
    python scripts/ingest.py --rebuild   # drop and rebuild from scratch
"""

from __future__ import annotations

import argparse
import sys
import os

# Ensure backend/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.ingestion import ingest
from app.rag.vector_store import vector_store
from app.rag.bm25_store import bm25_store
from app.rag.ingestion import BM25_INDEX_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="CogniFlow RAG ingestion")
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Drop existing collection and re-ingest all documents",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Only check if ingestion is needed",
    )
    args = parser.parse_args()

    if args.check:
        milvus_ok = vector_store.is_ready
        bm25_ok = bm25_store.is_ready
        if milvus_ok and bm25_ok:
            print("✓ RAG indexes are ready")
        else:
            print(f"✗ Milvus: {'ready' if milvus_ok else 'not ready'}, BM25: {'ready' if bm25_ok else 'not ready'}")
            print("  Run: python scripts/ingest.py [--rebuild]")
        return

    print("Ingesting documents…")
    stats = ingest(rebuild=args.rebuild)
    print(f"\nDone in {stats.get('elapsed_ms', 0)}ms:")
    print(f"  Files processed:  {stats['files']}")
    print(f"  Chunks created:   {stats['chunks']}")
    print(f"  Vectors embedded: {stats['embedded']}")
    print(f"  Milvus rows:      {stats['milvus_count']}")
    print(f"  BM25 docs:        {stats['bm25_count']}")


if __name__ == "__main__":
    main()
