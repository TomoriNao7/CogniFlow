from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from app.tools.base import ToolDefinition, ToolResult


@dataclass
class ToolSpec:
    """Internal representation of a registered tool callable."""

    definition: ToolDefinition
    handler: Callable[..., ToolResult]
    agent_id: int | None = None


class ToolRegistry:
    """Central registry for all tools. Agent startup pulls its tools from here."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: Callable[..., ToolResult],
        agent_id: int | None = None,
    ) -> None:
        key = f"{definition.name}:{definition.version}"
        self._tools[key] = ToolSpec(
            definition=definition, handler=handler, agent_id=agent_id
        )

    def get(self, name: str, version: str = "1.0") -> ToolSpec | None:
        return self._tools.get(f"{name}:{version}")

    def list_for_agent(self, agent_id: int) -> list[ToolSpec]:
        return [t for t in self._tools.values() if t.agent_id is None or t.agent_id == agent_id]

    def list_all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def to_openai_tools(self, agent_id: int) -> list[dict[str, Any]]:
        """Export tools as OpenAI-compatible function definitions."""
        tools: list[dict[str, Any]] = []
        for spec in self.list_for_agent(agent_id):
            params: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
            for p in spec.definition.parameters:
                params["properties"][p.param_name] = {
                    "type": p.param_type,
                    "description": p.param_desc or "",
                }
                if p.is_required:
                    params["required"].append(p.param_name)
            if not params["required"]:
                del params["required"]
            tools.append({
                "type": "function",
                "function": {
                    "name": spec.definition.name,
                    "description": spec.definition.description,
                    "parameters": params,
                },
            })
        return tools


# Global singleton
tool_registry = ToolRegistry()
