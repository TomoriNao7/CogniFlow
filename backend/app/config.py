from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 自动加载 backend/ 目录下的 .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        # 未装 python-dotenv，手动解析 .env
        with open(_env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _key, _val = _line.split("=", 1)
                    os.environ.setdefault(_key.strip(), _val.strip())


@dataclass
class Settings:
    # PostgreSQL
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cogniflow",
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 向量存储（pgvector —— 向量存放在 knowledge_chunks.embedding）
    pgvector_collection: str = os.getenv("PGVECTOR_COLLECTION", "knowledge_chunks")

    # Qwen API
    # repr=False 是关键：防止 print(settings) / logger.info(settings) 把密钥打进日志
    qwen_api_key: str = field(
        default_factory=lambda: (
            os.getenv("QWEN_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
        ),
        repr=False,
    )
    qwen_base_url: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 模型分配：全部走 .env，换模型不需要改代码
    # QWEN_MODEL 是全局默认模型，三个业务 agent 共用
    llm_model: str = os.getenv("QWEN_MODEL", "qwen-max")
    # 意图分类与对话摘要共用 INTENT_MODEL；不设则复用 QWEN_MODEL
    # 想省钱可单独设 INTENT_MODEL=qwen-turbo（只影响这两处小任务）
    intent_model: str = os.getenv("INTENT_MODEL", "") or llm_model
    pre_sales_model: str = os.getenv("PRE_SALES_MODEL", "") or llm_model
    during_sales_model: str = os.getenv("DURING_SALES_MODEL", "") or llm_model
    after_sales_model: str = os.getenv("AFTER_SALES_MODEL", "") or llm_model
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    # 精排模型（须带组织前缀，否则 FlagReranker 无法解析为仓库 ID）
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    reranker_device: str = os.getenv("RERANKER_DEVICE", "cpu")
    # 精排开关，默认关。83 条全量实测：交叉编码器用 5 条 hit@1 换 4 条
    # allrecall@5，且 CPU 上 24s/query，不适合放进默认链路。
    reranker_enabled: bool = os.getenv("RERANKER_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # Agent 默认值
    max_conversation_turns: int = 10
    summary_trigger_turns: int = 8
    tool_retry_count: int = 3
    tool_timeout_ms: int = 5000
    max_handoff_failures: int = 3

    # 检索默认值
    retrieval_top_k: int = 5
    similarity_threshold: float = 0.75
    # 权重互补（和恒为 1）。0.1/0.9 来自 83 条评估集的扫描：0.3 时 hit@1
    # 比 0.1 少命中 6 条，是噪声地板（1 条 ≈ 1.2pt）的 6 倍。
    bm25_weight: float = 0.1
    vector_weight: float = 0.9
    # BM25 分词器：bigram（字符二元组，默认）/ char（单字）/ jieba（词典分词）
    # 单字切分让「电池」和「电饭煲」共享 token，BM25 召回的是「提到这些字的
    # chunk」而非「有答案的 chunk」。83 条实测 Hit@1：char 0.5783 /
    # jieba 0.5663 / bigram 0.6265，故默认 bigram。
    bm25_tokenizer: str = os.getenv("BM25_TOKENIZER", "bigram")

    # 深度思考开关
    # qwen4-max 默认 enable_thinking=true、reasoning_effort=high，
    # 客服场景下会让首字延迟涨到十几秒、token 成本翻几倍，所以默认关掉。
    # 需要更强推理时把 .env 里的 QWEN_ENABLE_THINKING 设为 true。
    enable_thinking: bool = os.getenv("QWEN_ENABLE_THINKING", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    def thinking_extra(self, enable: bool | None = None) -> dict[str, bool]:
        """构造深度思考参数。

        DashScope 兼容模式下 enable_thinking 不是 OpenAI 标准字段，
        必须通过 request 的 extra_body 传入，否则会被静默忽略。
        """
        return {"enable_thinking": self.enable_thinking if enable is None else enable}


settings = Settings()
