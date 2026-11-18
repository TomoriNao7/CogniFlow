"""文档入库流水线 —— 切分 → 落 PG → 向量化 → 向量(pgvector) + BM25。

权威 chunk 主键是 `knowledge_chunks.id`（PostgreSQL）。pgvector 列
（`knowledge_chunks.embedding`）和 BM25 索引都携带这个 `db_chunk_id`，
这样 trace 记录可以直接 join 回源内容。

异步边界约定：
  - 所有数据库/批量向量化操作都在 **单个** 事件循环里顺序执行（`_*_async` 实现），
    避免多个 `asyncio.run` 复用同一 async engine 导致
    「Future attached to a different loop」。
  - 对外提供两套入口：
      · 同步版 ingest() / ingest_file() / sync_db_all()：供 CLI 脚本调用，
        内部只 asyncio.run 一次。
      · 异步版 ingest_async() / ingest_file_async() / sync_db_all_async()：
        供 FastAPI endpoint 调用，直接 await，不创建事件循环。
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from app.rag.splitter import auto_split, Chunk, extract_text
from app.rag.embedder import embedder
from app.rag.bm25_store import Bm25Doc, bm25_store

# 数据目录，相对于 backend/
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

# BM25 索引持久化路径
BM25_INDEX_PATH = str(DATA_DIR / ".index" / "bm25.pkl")

# embedding API 调用批大小
EMBED_BATCH = 10  # DashScope 限制：单次最多 10 条文本


def _collect_files(root: Path) -> list[Path]:
    """遍历 data/，收集所有支持的文件类型。"""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".md", ".faq", ".txt", ".pdf", ".docx", ".xlsx"):
            files.append(path)
    return files


def _file_type(path: Path) -> str:
    """根据文件扩展名映射到切分器类型。"""
    ext = path.suffix.lower()
    for t in ("md", "faq", "pdf", "docx", "xlsx"):
        if ext == f".{t}":
            return t
    return "txt"


def _read_file_content(fp: Path) -> str:
    """读取文件内容，二进制格式先抽取文本。"""
    ft = _file_type(fp)
    if ft in ("pdf", "docx", "xlsx"):
        return extract_text(str(fp), ft)
    return fp.read_text(encoding="utf-8")


def _source_name(path: Path, root: Path) -> str:
    """从文件路径推导人类可读的源文档名。"""
    rel = path.relative_to(root)
    return str(rel.with_suffix("")).replace(os.sep, " / ")


def _split_method(file_type: str) -> str:
    return {"md": "structure", "faq": "qa_boundary", "txt": "fixed_size"}.get(
        file_type, "fixed_size"
    )


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """同步批量向量化（按 DashScope 批上限切片）。"""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        vectors.extend(embedder.embed(batch))
    return vectors


# ── PostgreSQL 持久化 ──────────────────────────────────────────────────────────


async def _persist_chunks_async(
    file_path: str,
    chunks: list[Chunk],
    file_type: str,
    split_method: str,
    source: str,
    rebuild: bool = False,
) -> tuple[int, list[int]]:
    """创建 document + chunk 行，返回 (document_id, [chunk_db_id])，与 `chunks` 对齐。

    rebuild 时，先删除匹配（按 original_filename）的旧文档及其 chunk。
    否则复用已有文档，并返回其 chunk id，以便重写 embedding 而不重复建行。
    """
    from sqlalchemy import delete, select

    from app.models.database import KnowledgeChunk, KnowledgeDocument
    from app.models.engine import async_session_factory

    fp = Path(file_path)
    filename = fp.name
    file_size = fp.stat().st_size if fp.exists() else 0

    async with async_session_factory() as session:
        existing = (
            await session.execute(
                select(KnowledgeDocument)
                .where(KnowledgeDocument.original_filename == filename)
                .limit(1)
            )
        ).scalar_one_or_none()

        if existing and rebuild:
            await session.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.document_id == existing.id)
            )
            await session.delete(existing)
            await session.commit()
            existing = None

        if existing is not None:
            chunk_rows = (
                await session.execute(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.document_id == existing.id)
                    .order_by(KnowledgeChunk.chunk_index)
                )
            ).scalars().all()
            return existing.id, [c.id for c in chunk_rows]

        doc = KnowledgeDocument(
            title=filename,
            file_type=file_type,
            split_method=split_method,
            file_path=str(fp),
            original_filename=filename,
            file_size_bytes=file_size,
            status="active",
        )
        session.add(doc)
        await session.flush()  # 分配 doc.id

        chunk_objs: list[KnowledgeChunk] = []
        for chunk in chunks:
            c = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                source_document=source,
            )
            session.add(c)
            chunk_objs.append(c)
        await session.flush()  # 分配 chunk id
        chunk_db_ids = [c.id for c in chunk_objs]
        await session.commit()
        return doc.id, chunk_db_ids


async def _write_embeddings_async(chunk_ids: list[int], vectors: list[list[float]]) -> None:
    """把向量写回 knowledge_chunks.embedding（pgvector）。"""
    if not chunk_ids:
        return
    from sqlalchemy import select

    from app.models.database import KnowledgeChunk
    from app.models.engine import async_session_factory

    async with async_session_factory() as session:
        objs = (
            await session.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids))
            )
        ).scalars().all()
        by_id = {o.id: o for o in objs}
        for cid, vec in zip(chunk_ids, vectors):
            if cid in by_id:
                by_id[cid].embedding = vec
        await session.commit()


async def _clear_all_async() -> None:
    """清空所有 knowledge chunk + document（用于 --rebuild）。"""
    from sqlalchemy import delete

    from app.models.database import KnowledgeChunk, KnowledgeDocument
    from app.models.engine import async_session_factory

    async with async_session_factory() as session:
        await session.execute(delete(KnowledgeChunk))
        await session.execute(delete(KnowledgeDocument))
        await session.commit()


async def _ensure_schema_async() -> None:
    """建表 + 补齐缺失列（幂等）。

    ingest 脚本不走 FastAPI lifespan，不会自动调 init_db()，
    所以这里显式调用，保证 CLI 直接跑 ingest 时表一定存在。
    """
    from app.models.engine import init_db
    await init_db()


# ── 异步实现（供 FastAPI endpoint 直接 await）──────────────────────────────────


async def ingest_async(rebuild: bool = False) -> dict:
    """全量入库（异步实现）：切分 → 落 PG → 向量化 → 写向量 → 建 BM25。

    返回统计字典。向量存储是 PostgreSQL（pgvector），没有独立的 Milvus
    collection。`milvus_count` 键为兼容 CLI 而保留，现在表示「已写入的向量数」。
    """
    t0 = time.monotonic()
    root = DATA_DIR
    files = _collect_files(root)

    if not files:
        return {"files": 0, "chunks": 0, "embedded": 0, "milvus_count": 0, "bm25_count": 0}

    # 关键：先建表，否则 --rebuild 的 DELETE 会撞上「表不存在」
    await _ensure_schema_async()

    if rebuild:
        await _clear_all_async()

    all_bm25_docs: list[Bm25Doc] = []
    total_chunks = 0
    total_embedded = 0
    total_vectors = 0

    for fp in files:
        content = _read_file_content(fp)
        ft = _file_type(fp)
        chunks = auto_split(content, ft)
        if not chunks:
            continue

        src = _source_name(fp, root)
        doc_id, chunk_db_ids = await _persist_chunks_async(
            str(fp), chunks, ft, _split_method(ft), src, rebuild=rebuild
        )

        texts = [c.content for c in chunks]
        # 同步 embedding 调用放到线程池，避免阻塞事件循环
        vectors = await asyncio.to_thread(_embed_batch, texts)
        await _write_embeddings_async(chunk_db_ids, vectors)

        for chunk, cid in zip(chunks, chunk_db_ids):
            all_bm25_docs.append(
                Bm25Doc(
                    chunk_id=f"{src}#chunk{chunk.chunk_index}",
                    content=chunk.content,
                    source_document=src,
                    heading=chunk.metadata.get("heading", ""),
                    chunk_index=chunk.chunk_index,
                    db_chunk_id=cid,
                )
            )

        total_chunks += len(chunks)
        total_embedded += len(vectors)
        total_vectors += len(chunk_db_ids)

    bm25_store.build(all_bm25_docs)
    bm25_store.save(BM25_INDEX_PATH)

    return {
        "files": len(files),
        "chunks": total_chunks,
        "embedded": total_embedded,
        "milvus_count": total_vectors,
        "bm25_count": len(bm25_store),
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
    }


async def ingest_file_async(file_path: str) -> dict:
    """入库单个文件（异步实现）：切分 → 落 PG → 向量化 → 写向量 → 合并进 BM25。"""
    t0 = time.monotonic()
    fp = Path(file_path)
    if not fp.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = _read_file_content(fp)
    ft = _file_type(fp)
    chunks = auto_split(content, ft)

    if not chunks:
        return {"files": 0, "chunks": 0, "embedded": 0, "milvus_count": 0, "bm25_count": 0}

    # 关键：先建表，否则落库会撞上「表不存在」
    await _ensure_schema_async()

    root = DATA_DIR
    src = _source_name(fp, root)
    doc_id, chunk_db_ids = await _persist_chunks_async(
        str(fp), chunks, ft, _split_method(ft), src
    )

    texts = [c.content for c in chunks]
    vectors = await asyncio.to_thread(_embed_batch, texts)
    await _write_embeddings_async(chunk_db_ids, vectors)

    bm25_docs = [
        Bm25Doc(
            chunk_id=f"{src}#chunk{chunk.chunk_index}",
            content=chunk.content,
            source_document=src,
            heading=chunk.metadata.get("heading", ""),
            chunk_index=chunk.chunk_index,
            db_chunk_id=cid,
        )
        for chunk, cid in zip(chunks, chunk_db_ids)
    ]

    # 合并进现有 BM25 索引并重建
    existing = bm25_store._docs[:] if bm25_store.is_ready else []
    existing.extend(bm25_docs)
    bm25_store.build(existing)
    bm25_store.save(BM25_INDEX_PATH)

    return {
        "files": 1,
        "chunks": len(chunks),
        "embedded": len(vectors),
        "milvus_count": len(chunk_db_ids),
        "bm25_count": len(bm25_store),
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "source": src,
        "document_id": doc_id,
    }


async def sync_db_all_async() -> dict:
    """把 data/ 现有文件同步到 PostgreSQL（仅 chunk 行，不做 embedding）。"""
    files = _collect_files(DATA_DIR)
    if not files:
        return {"files": 0, "documents": 0, "chunks": 0}

    # 关键：先建表
    await _ensure_schema_async()

    docs_created = 0
    chunks_created = 0
    for fp in files:
        content = _read_file_content(fp)
        ft = _file_type(fp)
        chunks = auto_split(content, ft)
        if not chunks:
            continue
        src = _source_name(fp, DATA_DIR)
        doc_id, chunk_ids = await _persist_chunks_async(
            str(fp), chunks, ft, _split_method(ft), src
        )
        if doc_id:
            docs_created += 1
            chunks_created += len(chunk_ids)

    return {"files": len(files), "documents": docs_created, "chunks": chunks_created}


# ── 同步外壳（供 CLI 脚本调用，内部只创建一次事件循环）────────────────────────


def ingest(rebuild: bool = False) -> dict:
    """全量入库（同步入口，供 CLI 使用，内部只 asyncio.run 一次）。"""
    return asyncio.run(ingest_async(rebuild=rebuild))


def ingest_file(file_path: str) -> dict:
    """入库单个文件（同步入口，供 CLI 使用）。"""
    return asyncio.run(ingest_file_async(file_path))


def sync_db_all() -> dict:
    """同步文件到 PG（同步入口，供 CLI 使用）。"""
    return asyncio.run(sync_db_all_async())
