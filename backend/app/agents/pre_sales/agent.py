"""Pre-sales Agent — LangGraph workflow orchestrating RAG + Tools + LLM generation."""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.pre_sales.prompt import PRE_SALES_SYSTEM_PROMPT
from app.agents.pre_sales.tools import register_pre_sales_tools
from app.config import settings
from app.core.memory import ConversationMemory, memory_store
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever
from app.tools.registry import tool_registry

_registered = False


class AgentState(TypedDict):
    conversation_id: int
    user_query: str
    intent: str
    safety_passed: bool
    safety_message: str
    retrieved_docs: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    final_response: str
    handoff: bool
    handoff_reason: str
    trace: dict[str, Any]


class PreSalesAgent:
    """LangGraph-based pre-sales agent.

    Flow:
      retrieve → rerank → decide_tools → call_tools → generate → END
    """

    def __init__(self) -> None:
        global _registered
        if not _registered:
            register_pre_sales_tools(agent_id=1)
            _registered = True

        self.retriever = HybridRetriever(
            bm25_weight=settings.bm25_weight,
            vector_weight=settings.vector_weight,
            top_k=settings.retrieval_top_k,
        )
        self.reranker = Reranker(model_name=settings.reranker_model)
        self._llm_client: Any = None
        self.graph = self._build_graph()

    @property
    def llm(self) -> Any:
        if self._llm_client is None:
            from openai import AsyncOpenAI

            self._llm_client = AsyncOpenAI(
                api_key=settings.qwen_api_key,
                base_url=settings.qwen_base_url,
            )
        return self._llm_client

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("rerank", self._rerank)
        workflow.add_node("decide_tools", self._decide_tools)
        workflow.add_node("call_tools", self._call_tools)
        workflow.add_node("generate", self._generate)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "decide_tools")
        workflow.add_conditional_edges(
            "decide_tools",
            self._should_call_tools,
            {"tools": "call_tools", "generate": "generate"},
        )
        workflow.add_edge("call_tools", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    # ── Nodes ──────────────────────────────────────────────────────────────

    async def _retrieve(self, state: AgentState) -> AgentState:
        t0 = time.monotonic()
        try:
            results = await self.retriever.retrieve(state["user_query"])
            state["retrieved_docs"] = [
                {"id": r.chunk_id, "content": r.content, "score": r.score, "source": r.source_document}
                for r in results
            ]
            state["trace"]["retrieval_count"] = len(results)
        except Exception as exc:
            state["retrieved_docs"] = []
            state["trace"]["retrieval_error"] = str(exc)
        state["trace"]["retrieval_ms"] = int((time.monotonic() - t0) * 1000)
        return state

    async def _rerank(self, state: AgentState) -> AgentState:
        t0 = time.monotonic()
        if not state["retrieved_docs"]:
            state["trace"]["rerank_ms"] = 0
            return state
        try:
            from app.rag.retriever import RetrievalResult

            raw = [
                RetrievalResult(chunk_id=d["id"], content=d["content"], score=d["score"], source_document=d["source"])
                for d in state["retrieved_docs"]
            ]
            reranked = await self.reranker.rerank(state["user_query"], raw)
            state["retrieved_docs"] = [
                {"id": r.chunk_id, "content": r.content, "score": r.score, "source": r.source_document}
                for r in reranked
            ]
        except Exception as exc:
            state["trace"]["rerank_error"] = str(exc)
        state["trace"]["rerank_ms"] = int((time.monotonic() - t0) * 1000)
        return state

    async def _decide_tools(self, state: AgentState) -> AgentState:
        tools_schema = tool_registry.to_openai_tools(agent_id=1)
        if not tools_schema:
            state["tool_calls"] = []
            return state

        knowledge = "\n".join(
            f"[{d['source']}] {d['content']}" for d in state["retrieved_docs"][:3]
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是售前客服决策助手。根据用户问题和已有知识库内容，判断是否需要调用工具获取实时数据。\n"
                    "需要实时数据的场景：库存查询、价格查询、优惠券查询、会员信息查询。\n"
                    "不需要工具的场景：一般商品咨询、功能介绍、对比说明（知识库已覆盖）。\n"
                    "如果需要工具，选择最合适的工具并填写参数。如果不需要，返回空数组。"
                ),
            },
            {
                "role": "user",
                "content": f"用户问题：{state['user_query']}\n\n已有知识库内容：\n{knowledge}",
            },
        ]

        t0 = time.monotonic()
        resp = await self.llm.chat.completions.create(
            model=settings.pre_sales_model,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature=0.1,
        )
        state["trace"]["decision_ms"] = int((time.monotonic() - t0) * 1000)

        choice = resp.choices[0]
        state["tool_calls"] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                state["tool_calls"].append({"name": tc.function.name, "arguments": args})
        return state

    async def _call_tools(self, state: AgentState) -> AgentState:
        results: list[dict[str, Any]] = []
        for tc in state["tool_calls"]:
            t0 = time.monotonic()
            spec = tool_registry.get(tc["name"])
            if spec is None:
                results.append({"tool": tc["name"], "success": False, "error": "工具未注册"})
                continue
            try:
                handler = spec.handler
                if inspect.iscoroutinefunction(handler):
                    result = await handler(**tc["arguments"])
                else:
                    result = await asyncio.to_thread(
                        functools.partial(handler, **tc["arguments"])
                    )
                results.append({
                    "tool": tc["name"],
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                })
            except Exception as exc:
                results.append({"tool": tc["name"], "success": False, "error": str(exc)})
        state["tool_results"] = results
        state["trace"]["tool_call_results"] = results
        return state

    async def _generate(self, state: AgentState) -> AgentState:
        t0 = time.monotonic()

        knowledge = "\n---\n".join(
            f"[{d['source']}] {d['content']}" for d in state["retrieved_docs"][:3]
        )
        system_prompt = PRE_SALES_SYSTEM_PROMPT.replace(
            "{knowledge_context}", knowledge or "暂无匹配知识"
        )

        memory = memory_store.get_or_create(
            state["conversation_id"],
            max_turns=settings.max_conversation_turns,
            summary_trigger=settings.summary_trigger_turns,
        )
        memory.add_turn("user", state["user_query"])
        await memory.summarize_async()  # LLM compression when threshold reached

        # Use memory's built-in message builder (handles summary + turns)
        messages = memory.to_messages(system_prompt)

        if state["tool_results"]:
            tool_context = "\n\n## 工具查询结果\n"
            for tr in state["tool_results"]:
                data_str = json.dumps(tr.get("data", {}), ensure_ascii=False, indent=2)
                tool_context += f"\n### {tr['tool']}\n{data_str}\n"
            messages.append({"role": "system", "content": tool_context})

        resp = await self.llm.chat.completions.create(
            model=settings.pre_sales_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        reply = resp.choices[0].message.content or ""
        memory.add_turn("assistant", reply)

        # ── Handoff detection ────────────────────────────────────────────
        # 1. User explicitly requests human
        if any(kw in state["user_query"] for kw in ["转人工", "人工客服", "找客服", "找人工"]):
            state["handoff"] = True
            state["handoff_reason"] = "user_request"
        # 2. All tool calls failed
        elif state["tool_results"] and all(not tr.get("success") for tr in state["tool_results"]):
            state["handoff"] = True
            state["handoff_reason"] = "tool_failure_all"
        # 3. No knowledge retrieved and no tools available or called
        elif not state["retrieved_docs"] and not state["tool_results"] and not state["tool_calls"]:
            state["handoff"] = True
            state["handoff_reason"] = "knowledge_gap"

        # Persist memory if Redis store is available
        if hasattr(memory_store, 'persist'):
            memory_store.persist(memory)

        state["final_response"] = reply
        state["trace"]["model"] = settings.pre_sales_model
        state["trace"]["prompt_tokens"] = resp.usage.prompt_tokens if resp.usage else 0
        state["trace"]["completion_tokens"] = resp.usage.completion_tokens if resp.usage else 0
        state["trace"]["generation_ms"] = int((time.monotonic() - t0) * 1000)
        return state

    # ── Conditional edge ────────────────────────────────────────────────────

    def _should_call_tools(self, state: AgentState) -> str:
        return "tools" if state["tool_calls"] else "generate"

    # ── Public API ──────────────────────────────────────────────────────────

    async def run(self, conversation_id: int, user_query: str) -> AgentState:
        initial: AgentState = {
            "conversation_id": conversation_id,
            "user_query": user_query,
            "intent": "pre_sales",
            "safety_passed": True,
            "safety_message": "",
            "retrieved_docs": [],
            "tool_calls": [],
            "tool_results": [],
            "final_response": "",
            "handoff": False,
            "handoff_reason": "",
            "trace": {},
        }
        return await self.graph.ainvoke(initial)


# Singleton
pre_sales_agent = PreSalesAgent()
