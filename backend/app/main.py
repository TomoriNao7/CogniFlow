import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: auto-load BM25 index and ensure Milvus collection exists."""
    try:
        from app.rag.bm25_store import bm25_store, BM25_INDEX_PATH
        from app.rag.vector_store import vector_store

        # Load BM25 index if available
        if os.path.exists(BM25_INDEX_PATH) and not bm25_store.is_ready:
            bm25_store.load(BM25_INDEX_PATH)
            print(f"[startup] BM25 index loaded: {len(bm25_store)} docs")

        # Ensure Milvus collection loaded
        if vector_store.is_ready:
            vector_store.load()
            print("[startup] Milvus collection loaded")
        else:
            vector_store.create_collection()
            print("[startup] Milvus collection created")
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
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
async def health():
    from app.rag.vector_store import vector_store
    from app.rag.bm25_store import bm25_store

    return {
        "status": "ok",
        "agent": "multi",
        "milvus": vector_store.is_ready,
        "bm25": bm25_store.is_ready,
        "bm25_count": len(bm25_store),
    }
