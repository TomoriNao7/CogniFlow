#!/usr/bin/env python3
"""Run the document ingestion pipeline — split → embed → store in Milvus + BM25 + PostgreSQL.

Usage:
    cd backend
    python scripts/ingest.py               # incremental ingestion
    python scripts/ingest.py --rebuild     # drop and rebuild from scratch
    python scripts/ingest.py --sync-db     # sync existing data files to PostgreSQL only
    python scripts/ingest.py --check       # check if indexes are ready
"""

from __future__ import annotations

import argparse
import sys
import os

# Ensure backend/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.ingestion import ingest, sync_db_all
from app.rag.vector_store import vector_store
from app.rag.bm25_store import bm25_store
from app.rag.ingestion import BM25_INDEX_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="CogniFlow RAG ingestion")
    parser.add_argument("--rebuild", action="store_true", help="Drop and re-ingest all documents")
    parser.add_argument("--check", action="store_true", help="Only check if ingestion is needed")
    parser.add_argument("--sync-db", action="store_true", help="Sync existing data files to PostgreSQL only")
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
    print(f"  Milvus rows:      {stats['milvus_count']}")
    print(f"  BM25 docs:        {stats['bm25_count']}")


if __name__ == "__main__":
    main()
