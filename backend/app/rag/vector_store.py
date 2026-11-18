"""基于 pgvector 的向量存储。

向量存放在 `knowledge_chunks.embedding` 列（PostgreSQL + pgvector），
因此本模块只是对 SQL 余弦检索的一层薄封装——无需独立服务。
权威 chunk 主键是 `knowledge_chunks.id`（PG 整数），对外暴露为 `db_chunk_id`。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.models.engine import async_session_factory


class VectorStore:
    """通过 pgvector 对 knowledge_chunks.embedding 做余弦相似度检索。"""

    def __init__(self) -> None:
        # 表结构由 init_db 负责创建，这里没有 collection 需要建
        self._collection_ready = True

    @property
    def is_ready(self) -> bool:
        # PG 表在 lifespan 的 init_db 中创建，pgvector 扩展也在那里确保就绪。
        return True

    async def create_collection(self, drop_existing: bool = False) -> None:
        """为保持接口兼容而保留的空实现——schema 由 init_db 统一管理。"""

    async def load(self) -> None:
        """为保持接口兼容而保留的空实现——pgvector 没有 load 步骤。"""

    async def search(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """按余弦相似度返回 top_k 个 chunk（1 表示完全相同）。

        `distance` 用 1 - 余弦距离 计算，这样调用方可以沿用
        「越大越接近」的旧约定。
        """
        if top_k <= 0:
            return []

        # 用字符串字面量 + CAST 传递查询向量：
        # 走原生 text() SQL 时，asyncpg 不会自动把 Python list 绑成 vector 类型，
        # 需要先序列化成 '[x,y,z]' 再显式 CAST（避免额外注册 pgvector 的 asyncpg codec）。
        vec_literal = "[" + ",".join(f"{x:.8f}" for x in query_vector) + "]"

        stmt = text(
            """
            SELECT
                c.id              AS db_chunk_id,
                c.document_id     AS document_id,
                c.content         AS content,
                c.source_document AS source_document,
                1 - (c.embedding <=> CAST(:qv AS vector)) AS similarity
            FROM knowledge_chunks c
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:qv AS vector)
            LIMIT :k
            """
        )
        async with async_session_factory() as session:
            result = await session.execute(
                stmt, {"qv": vec_literal, "k": top_k}
            )
            rows = result.fetchall()

        return [
            {
                "entity": {
                    "db_chunk_id": row.db_chunk_id,
                    "chunk_id": str(row.db_chunk_id),
                    "document_id": row.document_id,
                    "content": row.content,
                    "source_document": row.source_document,
                },
                "distance": round(float(row.similarity), 4),
            }
            for row in rows
        ]


# 单例
vector_store = VectorStore()
