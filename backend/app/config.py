from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # PostgreSQL
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cogniflow",
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Milvus
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: int = int(os.getenv("MILVUS_PORT", "19530"))
    milvus_collection: str = os.getenv("MILVUS_COLLECTION", "knowledge_chunks")

    # Qwen API
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_base_url: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # Model assignments
    intent_model: str = "qwen2.5-1.5b"
    pre_sales_model: str = "qwen-max"
    embedding_model: str = "text-embedding-v3"

    # Reranker
    reranker_model: str = "bge-reranker-v2-m3"
    reranker_device: str = os.getenv("RERANKER_DEVICE", "cpu")

    # Agent defaults
    max_conversation_turns: int = 10
    summary_trigger_turns: int = 8
    tool_retry_count: int = 3
    tool_timeout_ms: int = 5000
    max_handoff_failures: int = 3

    # Retrieval defaults
    retrieval_top_k: int = 5
    similarity_threshold: float = 0.75
    bm25_weight: float = 0.3
    vector_weight: float = 0.7


settings = Settings()
