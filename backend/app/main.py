from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.websocket import router as ws_router

app = FastAPI(
    title="CogniFlow — 售前 Agent",
    description="电商智能客服系统 — 售前领域 Agent 服务",
    version="0.1.0",
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
    return {"status": "ok", "agent": "pre_sales"}
