"""Web search tool — DuckDuckGo, shared across all agents."""

from __future__ import annotations

import time

from app.tools.base import ToolDefinition, ToolParameterDef, ToolResult
from app.tools.registry import tool_registry


def _web_search(query: str = "", max_results: str = "3") -> ToolResult:
    """Search the web using DuckDuckGo and return results."""
    t0 = time.monotonic()
    try:
        max_n = min(int(max_results), 5)
    except (ValueError, TypeError):
        max_n = 3

    try:
        from duckduckgo_search import DDGS

        results: list[dict] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_n):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:500],
                    "url": r.get("href", ""),
                })

        if not results:
            return ToolResult(
                success=True,
                data={"query": query, "results": [], "message": "未找到相关搜索结果"},
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": results,
                "source": "DuckDuckGo",
            },
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    except ImportError:
        return ToolResult(
            success=False,
            error="联网搜索依赖未安装，请运行: pip install duckduckgo-search",
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"搜索失败: {e}",
        )


def register_web_search(agent_id: int | None = None) -> None:
    """Register the web_search tool. agent_id=None means available to all agents."""
    tool_registry.register(
        ToolDefinition(
            name="web_search",
            display_name="联网搜索",
            description="当知识库中没有相关信息时，联网搜索最新商品信息、价格、参数等实时数据",
            parameters=[
                ToolParameterDef("query", "string", "搜索关键词", is_required=True),
                ToolParameterDef("max_results", "string", "最大返回条数，默认3，最大5"),
            ],
            timeout_ms=10000,
            retry_count=2,
        ),
        _web_search,
        agent_id=agent_id,  # None = global, available to all agents
    )
