# CogniFlow —— 电商智能客服

基于多 Agent 协作架构的企业级电商智能客服系统，覆盖**售前、售中、售后**全链路场景。

## 核心特性

- **三 Agent 协作**：售前（商品/优惠/会员）、售中（支付/地址/发票）、售后（物流/退款/投诉），Qwen 1.5B LLM 意图分类自动路由
- **混合检索 RAG**：Milvus 向量检索 + BM25 关键词，bge-reranker 重排序，Markdown/FAQ 双格式知识库
- **Function Calling**：12 个业务工具，Agent 自主决策调用，mock 数据即插即用
- **LLM 记忆压缩**：Qwen 1.5B 对话摘要，Redis 持久化，支持多轮上下文
- **实时通信**：WebSocket 流式输出 + HTTP 降级，打字机光标效果
- **转人工兜底**：三种触发条件（用户主动 / 工具失败 / 知识缺失）

## 架构总览

```
用户消息
  → 内容安全检测
  → Qwen 1.5B 意图分类
  → 路由 Agent（售前 / 售中 / 售后）
     → LangGraph 编排
     → 混合检索（Milvus + BM25）
     → bge-reranker 重排序
     → Function Calling 工具调用
     → Qwen Max / Plus 生成回复
     → LLM 记忆摘要压缩
  → Handoff 转人工 / WebSocket 流式返回
```

## 技术栈

| 层面 | 选型 |
|------|------|
| 前端 — Widget | React + TypeScript + WebSocket + Tailwind CSS |
| 前端 — Admin | React + TypeScript + React Router + Zustand |
| 后端框架 | Python FastAPI + LangGraph |
| 对话编排 | LangGraph（retrieve → rerank → decide_tools → call_tools → generate） |
| LLM | Qwen Max（售前/售后）/ Qwen Plus（售中）/ Qwen 1.5B（意图+摘要） |
| Embedding | DashScope text-embedding-v3（1024 维） |
| 向量库 | Milvus Lite（开发）/ Milvus Server（生产） |
| 关键词检索 | BM25Okapi（内存，pickle 持久化） |
| 重排序 | bge-reranker-v2-m3 / 分数降级 |
| 缓存 / 记忆 | Redis（会话持久化，24h TTL） |
| 数据库 | PostgreSQL + SQLAlchemy 2.0（待接入） |

## 项目结构

```
CogniFlow/
├── backend/
│   ├── app/
│   │   ├── agents/                  # Agent 模块
│   │   │   ├── pre_sales/           # 售前：商品/库存/优惠/会员
│   │   │   ├── during_sales/        # 售中：支付/地址/发票
│   │   │   ├── after_sales/         # 售后：物流/退款/投诉
│   │   │   └── router.py            # 意图分类 + 路由分发
│   │   ├── rag/                     # RAG 检索
│   │   │   ├── embedder.py          # 向量化（DashScope）
│   │   │   ├── vector_store.py      # Milvus Lite 封装
│   │   │   ├── bm25_store.py        # BM25 关键词索引
│   │   │   ├── retriever.py         # 混合检索（向量+BM25 融合）
│   │   │   ├── reranker.py          # 重排序
│   │   │   ├── splitter.py          # 文档分切（Markdown/FAQ/FixedSize）
│   │   │   └── ingestion.py         # 文档注入管线
│   │   ├── core/                    # 核心组件
│   │   │   ├── memory.py            # 对话记忆（LLM 摘要 + Redis）
│   │   │   └── security.py          # 内容安全检测
│   │   ├── tools/                   # 工具注册中心
│   │   │   ├── base.py              # ToolDefinition / ToolResult
│   │   │   └── registry.py          # 全局工具注册表
│   │   ├── api/
│   │   │   ├── chat.py              # REST API
│   │   │   └── websocket.py         # WebSocket 流式
│   │   ├── config.py                # 全局配置
│   │   └── main.py                  # FastAPI 入口
│   ├── scripts/
│   │   └── ingest.py                # 知识库注入 CLI
│   └── requirements.txt
├── data/                            # 知识库文档
│   ├── pre_sales/                   # 商品目录/促销规则/会员政策
│   ├── during_sales/                # 支付指南/发票规则
│   └── after_sales/                 # 退换货政策/物流配送/售后服务
├── frontend/
│   ├── widget/                      # 用户端聊天窗口
│   └── admin/                       # 后台管理系统
└── 立项文档.md
```

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
-（可选）Redis 服务

### 1. 克隆项目

```bash
git clone https://github.com/TomoriNao7/CogniFlow.git
cd CogniFlow
```

### 2. 配置 API Key

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DashScope API Key
```

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 注入知识库

```bash
python scripts/ingest.py --rebuild
```

输出示例：

```
Files processed:  8
Chunks created:   126
Milvus rows:      126
BM25 docs:        126
```

### 5. 启动后端

```bash
uvicorn app.main:app --reload --port 8000
```

验证：`http://localhost:8000/health`

### 6. 启动前端

**Widget 聊天窗口：**

```bash
cd frontend/widget
npm install && npm run dev
```

**Admin 管理面板：**

```bash
cd frontend/admin
npm install && npm run dev
```

## API 接口

### REST

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 发送消息 |
| `POST` | `/api/v1/feedback` | 提交反馈 |
| `GET` | `/api/v1/tools` | 查看所有工具 |
| `GET` | `/health` | 健康检查 |

### 请求示例

```json
POST /api/v1/chat
{
  "conversation_id": 1,
  "user_id": "user_001",
  "message": "iPhone 15 Pro 多少钱？"
}
```

```json
{
  "conversation_id": 1,
  "reply": "iPhone 15 Pro 256GB 售价 ¥8,999...",
  "intent": "query_product",
  "handoff": false,
  "trace": {
    "retrieval_count": 5,
    "model": "qwen-max",
    "generation_ms": 1834
  }
}
```

### WebSocket

```
ws://localhost:8000/ws/chat
```

消息协议：

```json
// 发送
{"message": "你好", "conversation_id": 1}

// 接收
{"type": "intent", "intent": "query_product", "confidence": 0.95, "classifier": "llm"}
{"type": "chunk", "content": "您好！"}
{"type": "reply", "content": "您好！有什么可以帮您的？", "trace": {...}, "done": true}
```

## 三 Agent 能力矩阵

| | 售前 Agent | 售中 Agent | 售后 Agent |
|------|------|------|------|
| **模型** | Qwen Max | Qwen Plus | Qwen Max |
| **场景** | 商品咨询、规格对比、库存、优惠券、会员 | 下单问题、支付失败、地址修改、发票 | 物流查询、退款退货、质量投诉 |
| **工具** | `query_product` `check_inventory` `check_coupons` `check_membership` | `query_unpaid_order` `check_payment_status` `modify_address` `apply_invoice` | `check_logistics` `query_order` `request_refund` `check_refund_status` |
| **知识库** | 商品目录 / 促销规则 / 会员政策 | 支付指南 / 发票规则 | 退换货政策 / 物流配送 / 售后服务 |

## Handoff 转人工

| 触发条件 | 优先级 | 说明 |
|---------|------|------|
| 用户主动要求 | 1 | 检测关键词：转人工、人工客服、找客服 |
| 全部工具失败 | 2 | 所有 Function Calling 返回 error |
| 知识缺失 | 3 | 无检索结果且无可调用工具 |

WebSocket 层还有 3 次连续失败兜底。

## MVP 完成度

- [x] React Widget 前端（WebSocket + 流式）
- [x] Qwen 1.5B LLM 意图分类 + 三 Agent 路由
- [x] 知识库 Markdown + FAQ（8 份文档，126 chunks）
- [x] 混合检索（Milvus + BM25）+ bge-reranker 重排序
- [x] Function Calling 链路（12 个业务工具）
- [x] LLM 对话摘要 + Redis 持久化
- [x] Agent 内 Handoff 转人工
- [x] 基础反馈按钮

## License

MIT
