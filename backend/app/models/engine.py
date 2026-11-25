"""数据库 engine 与 session 管理。"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.database import Base

# async engine，驱动用 asyncpg
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# session 工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """创建所有表（幂等），并补齐已存在表缺失的列。"""
    async with engine.begin() as conn:
        # knowledge_chunks.embedding 需要 pgvector 扩展
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

        # create_all 只建新表、不改已有表。已有库需要幂等补列。
        await conn.execute(text(
            """
            DO $$
            BEGIN
                IF to_regclass('public.knowledge_chunks') IS NOT NULL THEN
                    ALTER TABLE knowledge_chunks
                        ADD COLUMN IF NOT EXISTS source_document VARCHAR(256);
                    ALTER TABLE knowledge_chunks
                        ADD COLUMN IF NOT EXISTS embedding vector(1024);
                END IF;
            END $$;
            """
        ))
        # 同上的补列：trace 要能记录本次精排是 off / cross / fallback
        await conn.execute(text(
            "ALTER TABLE message_traces "
            "ADD COLUMN IF NOT EXISTS rerank_mode VARCHAR(16)"
        ))

        # 三个业务 Agent 是 conversations/intent_definitions 的外键目标，
        # 空表会让 /chat 落库时撞 ForeignKeyViolationError，这里幂等补种子。
        await conn.execute(
            text(
                """
                INSERT INTO agents (name, display_name, model, status)
                VALUES
                    ('pre_sales',    '售前咨询', :pre,    'active'),
                    ('during_sales', '售中服务', :during, 'active'),
                    ('after_sales',  '售后服务', :after,  'active')
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "pre": settings.pre_sales_model or settings.llm_model,
                "during": settings.during_sales_model or settings.llm_model,
                "after": settings.after_sales_model or settings.llm_model,
            },
        )


async def get_session() -> AsyncSession:
    """提供 async session 供依赖注入。"""
    async with async_session_factory() as session:
        yield session
