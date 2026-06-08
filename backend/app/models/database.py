from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128))
    model: Mapped[str] = mapped_column(String(32))
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    retrieval_params: Mapped[list[AgentRetrievalParam]] = relationship(
        back_populates="agent", lazy="selectin"
    )


class AgentRetrievalParam(Base):
    __tablename__ = "agent_retrieval_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    param_key: Mapped[str] = mapped_column(String(64))
    param_value: Mapped[str] = mapped_column(String(128))

    agent: Mapped[Agent] = relationship(back_populates="retrieval_params")


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[Optional[str]] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text)
    endpoint_url: Mapped[str] = mapped_column(String(512))
    http_method: Mapped[str] = mapped_column(String(8), default="POST")
    timeout_ms: Mapped[int] = mapped_column(Integer, default=5000)
    retry_count: Mapped[int] = mapped_column(Integer, default=2)
    auth_type: Mapped[str] = mapped_column(String(32), default="none")
    version: Mapped[str] = mapped_column(String(16), default="1.0")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    parameters: Mapped[list[ToolParameter]] = relationship(
        back_populates="tool", lazy="selectin"
    )


class ToolParameter(Base):
    __tablename__ = "tool_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id"))
    param_name: Mapped[str] = mapped_column(String(64))
    param_type: Mapped[str] = mapped_column(String(32))
    param_desc: Mapped[Optional[str]] = mapped_column(String(256))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[Optional[str]] = mapped_column(String(128))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    tool: Mapped[Tool] = relationship(back_populates="parameters")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    title: Mapped[Optional[str]] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(32), default="widget")
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(8))
    content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    rating: Mapped[str] = mapped_column(String(16))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admin_users.id"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class HumanHandoff(Base):
    __tablename__ = "human_handoffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    reason: Mapped[str] = mapped_column(String(64))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    intent_agent: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
