import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.websocket import router as ws_router
from app.api.admin import router as admin_router
from app.api.trace import router as trace_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：初始化 DB、加载 BM25 索引。"""
    # 初始化数据表
    try:
        from app.models.engine import init_db
        await init_db()
        print("[startup] Database tables ensured")
    except Exception as e:
        print(f"[startup] DB init warning: {e}")

    # 加载 RAG 索引（仅 BM25 —— 向量存放在 PostgreSQL 的 pgvector 中）
    try:
        from app.rag.bm25_store import bm25_store
        from app.rag.ingestion import BM25_INDEX_PATH

        if os.path.exists(BM25_INDEX_PATH) and not bm25_store.is_ready:
            bm25_store.load(BM25_INDEX_PATH)
            print(f"[startup] BM25 index loaded: {len(bm25_store)} docs")
    except Exception as e:
        print(f"[startup] RAG index load warning: {e}")

    yield


app = FastAPI(
    title="CogniFlow — 智能客服",
    description="电商智能客服系统 — 售前/售中/售后三 Agent 服务",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(trace_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
async def health():
    from app.rag.vector_store import vector_store
    from app.rag.bm25_store import bm25_store

    db_ok = False
    try:
        from app.models.engine import engine as db_engine
        async with db_engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "agent": "multi",
        "vector": vector_store.is_ready,
        "bm25": bm25_store.is_ready,
        "bm25_count": len(bm25_store),
        "database": db_ok,
    }
