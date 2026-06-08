from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int = Field(..., description="会话 ID")
    user_id: str = Field(default="user_001", description="用户标识")
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int | None = None
    reply: str
    intent: str = ""
    handoff: bool = False
    handoff_reason: str = ""
    trace: dict | None = None


class FeedbackRequest(BaseModel):
    message_id: int
    rating: str  # "helpful" | "not_helpful"
    reason: str | None = None


class HealthResponse(BaseModel):
    status: str
    agent: str
    version: str
