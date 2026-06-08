from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolParameterDef:
    param_name: str
    param_type: str
    param_desc: str = ""
    is_required: bool = False
    default_value: str | None = None


@dataclass
class ToolDefinition:
    name: str
    display_name: str
    description: str
    parameters: list[ToolParameterDef] = field(default_factory=list)
    version: str = "1.0"
    timeout_ms: int = 5000
    retry_count: int = 2


@dataclass
class ToolResult:
    success: bool
    data: object = None
    error: str | None = None
    duration_ms: int = 0
