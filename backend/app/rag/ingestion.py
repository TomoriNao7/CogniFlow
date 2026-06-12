"""Document ingestion pipeline — split → embed → store in Milvus + BM25."""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.rag.splitter import auto_split, Chunk
from app.rag.embedder import embedder
from app.rag.vector_store import vector_store
from app.rag.bm25_store import Bm25Doc, bm25_store

# Data directory relative to backend/
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

# BM25 index persistence path
BM25_INDEX_PATH = str(DATA_DIR / ".index" / "bm25.pkl")

# Batch size for embedding API calls
EMBED_BATCH = 10  # DashScope limit: max 10 texts per request


def _collect_files(root: Path) -> list[Path]:
    """Walk data/ and collect .md and .faq files."""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".md", ".faq", ".txt"):
            files.append(path)
    return files


def _file_type(path: Path) -> str:
    """Map file extension to splitter type."""
    ext = path.suffix.lower()
    if ext in (".md",):
        return "md"
    if ext in (".faq",):
        return "faq"
    return "txt"


def _source_name(path: Path, root: Path) -> str:
    """Derive a human-readable source document name from the file path."""
    rel = path.relative_to(root)
    return str(rel.with_suffix("")).replace(os.sep, " / ")


def ingest(rebuild: bool = False) -> dict[str, int]:
    """Run the full ingestion pipeline.

    Returns a dict with stats: {files, chunks, embedded, milvus_count, bm25_count}
    """
    t0 = time.monotonic()
    root = DATA_DIR
    files = _collect_files(root)

    if not files:
        return {"files": 0, "chunks": 0, "embedded": 0, "milvus_count": 0, "bm25_count": 0}

    # Step 1: Split all files into chunks
    all_chunks: list[tuple[Path, Chunk]] = []
    for fp in files:
        content = fp.read_text(encoding="utf-8")
        ft = _file_type(fp)
        chunks = auto_split(content, ft)
        for c in chunks:
            all_chunks.append((fp, c))

    # Step 2: Embed chunks in batches
    texts = [c.content for _, c in all_chunks]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        vectors.extend(embedder.embed(batch))

    # Step 3: Prepare Milvus rows and BM25 docs
    source_root = root
    milvus_rows: list[dict] = []
    bm25_docs: list[Bm25Doc] = []

    for idx, ((fp, chunk), vec) in enumerate(zip(all_chunks, vectors)):
        chunk_id = f"{_source_name(fp, source_root)}#chunk{chunk.chunk_index}"
        src = _source_name(fp, source_root)
        heading = chunk.metadata.get("heading", "")

        milvus_rows.append({
            "chunk_id": chunk_id,
            "content": chunk.content,
            "source_document": src,
            "heading": heading,
            "chunk_index": chunk.chunk_index,
            "embedding": vec,
        })

        bm25_docs.append(Bm25Doc(
            chunk_id=chunk_id,
            content=chunk.content,
            source_document=src,
            heading=heading,
            chunk_index=chunk.chunk_index,
        ))

    # Step 4: Store in Milvus
    vector_store.create_collection(drop_existing=rebuild)
    insert_count = vector_store.insert(milvus_rows)
    vector_store.load()  # Ensure collection is loaded into memory

    # Step 5: Build and persist BM25 index
    bm25_store.build(bm25_docs)
    bm25_store.save(BM25_INDEX_PATH)

    elapsed = int((time.monotonic() - t0) * 1000)
    return {
        "files": len(files),
        "chunks": len(all_chunks),
        "embedded": len(vectors),
        "milvus_count": insert_count,
        "bm25_count": len(bm25_store),
        "elapsed_ms": elapsed,
    }


def ingest_file(file_path: str) -> dict:
    """Ingest a single file — split → embed → store in Milvus + BM25.

    Returns stats dict. Also persists BM25 index after ingestion.
    """
    t0 = time.monotonic()
    fp = Path(file_path)
    if not fp.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = fp.read_text(encoding="utf-8")
    ft = _file_type(fp)
    chunks = auto_split(content, ft)

    if not chunks:
        return {"files": 0, "chunks": 0, "embedded": 0, "milvus_count": 0, "bm25_count": 0}

    # Embed
    texts = [c.content for c in chunks]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        vectors.extend(embedder.embed(batch))

    # Use same root-relative naming convention
    root = DATA_DIR
    src = _source_name(fp, root)

    # Milvus rows
    milvus_rows: list[dict] = []
    bm25_docs: list[Bm25Doc] = []
    for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
        chunk_id = f"{src}#chunk{chunk.chunk_index}"
        heading = chunk.metadata.get("heading", "")
        milvus_rows.append({
            "chunk_id": chunk_id,
            "content": chunk.content,
            "source_document": src,
            "heading": heading,
            "chunk_index": chunk.chunk_index,
            "embedding": vec,
        })
        bm25_docs.append(Bm25Doc(
            chunk_id=chunk_id, content=chunk.content,
            source_document=src, heading=heading, chunk_index=chunk.chunk_index,
        ))

    # Ensure collection exists and is loaded
    if not vector_store.is_ready:
        vector_store.create_collection()
    insert_count = vector_store.insert(milvus_rows)
    vector_store.load()

    # Merge into existing BM25 index and rebuild
    existing = bm25_store._docs[:] if bm25_store.is_ready else []
    existing.extend(bm25_docs)
    bm25_store.build(existing)
    bm25_store.save(BM25_INDEX_PATH)

    return {
        "files": 1,
        "chunks": len(chunks),
        "embedded": len(vectors),
        "milvus_count": insert_count,
        "bm25_count": len(bm25_store),
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "source": src,
    }
