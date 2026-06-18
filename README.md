# CogniFlow —— 电商智能客服

多 Agent 协作 + RAG 混合检索 + Function Calling 的企业级电商智能客服系统，覆盖**售前、售中、售后**全链路。

## 核心特性

- **三 Agent 协作**：售前（商品/优惠/会员）· 售中（支付/地址/发票）· 售后（物流/退款/投诉），Qwen 1.5B LLM 意图分类 + 关键词降级
- **混合检索 RAG**：Milvus 向量 + BM25 关键词（0.7/0.3 加权融合），bge-reranker 重排序，235 个知识切片
- **多格式知识库**：Markdown（文档结构）· FAQ（Q&A边界）· PDF/Word（语义切片）· Excel（按行切表）· 纯文本（滑动窗口）
- **Function Calling**：13 个业务工具，Agent 自主决策调用，mock 数据即插即用
- **工具容错**：指数退避重试（1s→2s→4s）+ 熔断器（连续 5 次失败自动熔断 30s）+ 网络/业务错误区分
- **联网搜索降级**：DuckDuckGo，知识库无匹配时自动查询网页
- **LLM 记忆压缩**：Qwen 1.5B 对话摘要，超 8 轮自动压缩，Redis 持久化 24h TTL
- **转人工兜底**：用户主动 / 工具全失败 / 知识缺失三种触发 + WebSocket 3 次连续失败兜底
- **敏感信息脱敏**：身份证/银行卡/手机号/邮箱自动检测打码，安全检测前先脱敏
- **实时流式**：WebSocket 流式输出 + HTTP 降级，打字机光标 + 反馈追问

## 架构

```
用户消息 → 内容安全 + 脱敏 → Qwen 1.5B 意图分类 → 路由 Agent
  → LangGraph: 检索 → 重排序 → 工具决策 → 工具调用(重试+熔断) → 生成
  → LLM 摘要压缩 → Redis 持久化 → WebSocket 流式 / Handoff 转人工
```

## 技术栈

| 层面 | 选型 |
|------|------|
| 后端框架 | Python FastAPI + LangGraph 对话编排 |
| LLM | Qwen Max / Plus / 1.5B（DashScope API） |
| Embedding | text-embedding-v3（1024 维） |
| 向量库 | Milvus Lite（开发）/ Milvus Server（生产） |
| 关键词检索 | BM25Okapi（内存 + pickle 持久化） |
| 重排序 | bge-reranker-v2-m3 / 分数降级 |
| 缓存 / 记忆 | Redis（会话持久化，24h TTL） |
| 数据库 | PostgreSQL + SQLAlchemy 2.0 async |
| 前端 | React + TypeScript + WebSocket + Tailwind CSS |

## 快速开始

```bash
# 1. 配置 API Key
cp backend/.env.example backend/.env   # 编辑填入 DashScope API Key

# 2. 安装依赖
cd backend && pip install -r requirements.txt

# 3. 注入知识库（首次）
python scripts/ingest.py --rebuild

# 4. 启动 PostgreSQL 后同步 DB
python scripts/ingest.py --sync-db

# 5. 启动后端
uvicorn app.main:app --reload --port 8000

# 6. 启动前端
cd frontend/widget && npm install && npm run dev    # 用户端
cd frontend/admin && npm install && npm run dev     # 管理端
```

## 项目结构

```
backend/
├── app/
│   ├── agents/              # 三 Agent（pre_sales / during_sales / after_sales）
│   │   └── router.py        # LLM 意图分类 + 路由分发
│   ├── rag/                 # RAG 检索管线
│   │   ├── splitter.py      # 5 种文档分切器（Markdown/FAQ/PDF/Word/Excel/Text）
│   │   ├── embedder.py      # DashScope 向量化
│   │   ├── vector_store.py  # Milvus Lite 封装
│   │   ├── bm25_store.py    # BM25 关键词索引（pickle 持久化）
│   │   ├── retriever.py     # 混合检索（向量+BM25 加权融合）
│   │   ├── reranker.py      # bge-reranker 重排序 / 分数降级
│   │   └── ingestion.py     # 文档注入管线（分切→嵌入→存储+DB同步）
│   ├── core/
│   │   ├── memory.py        # LLM 对话摘要 + Redis 持久化
│   │   ├── security.py      # 内容安全 + 敏感信息脱敏
│   │   └── resilience.py    # 重试退避 + 熔断器
│   ├── tools/
│   │   ├── registry.py      # 全局工具注册中心
│   │   └── web_search.py    # DuckDuckGo 联网搜索
│   ├── api/
│   │   ├── chat.py           # REST API + DB 持久化
│   │   ├── websocket.py      # WebSocket 流式
│   │   └── admin.py          # Admin 后台 API（8 端点）
│   └── models/
│       ├── database.py       # 26 个 ORM 模型
│       └── engine.py         # async SQLAlchemy 引擎
├── scripts/
│   └── ingest.py            # CLI 文档注入工具
└── data/                    # 知识库文档（9 文件 / 235 chunks）
```

## MVP 完成度

- [x] Widget 前端 + WebSocket 流式 + 暗黑主题
- [x] Qwen 1.5B LLM 意图分类 + 三 Agent 路由
- [x] Markdown / FAQ / PDF / Word / Excel 多格式知识库
- [x] Milvus + BM25 混合检索 + bge-reranker 重排序
- [x] 13 个 Function Calling 工具 + 重试熔断容错
- [x] LLM 对话摘要 + Redis 持久化记忆
- [x] Agent 内 Handoff 转人工 + WebSocket 失败兜底
- [x] 敏感信息自动脱敏 + 内容安全检测
- [x] 反馈按钮 + 追问弹窗 + PostgreSQL 全量持久化
- [x] Admin 后台（仪表盘/对话回放/反馈看板/知识库管理/Agent配置/工具管理/文档上传）
- [x] 联网搜索降级（知识库无匹配时自动查网页）
- [x] 100 款商品知识库（235 个切片，11 个品类）
