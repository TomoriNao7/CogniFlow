"""验证 message_traces.rerank_mode 列已补上（init_db 的幂等 ALTER）。"""

import asyncio
import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cogniflow"
)

from sqlalchemy import text  # noqa: E402

from app.models.engine import engine, init_db  # noqa: E402


async def main() -> None:
    await init_db()
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='message_traces' AND column_name='rerank_mode'"
                )
            )
        ).fetchall()
    print("rerank_mode column rows:", rows)

    from app.rag.reranker import Reranker

    r = Reranker()
    print("reranker.mode:", r.mode, "| enabled:", r.load_error)


if __name__ == "__main__":
    asyncio.run(main())
