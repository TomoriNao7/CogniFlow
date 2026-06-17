"""Chat REST API endpoint — with PostgreSQL persistence."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.agents.router import classify_intent, route_to_agent
from app.core.security import Severity, SafetyAction, content_safety, mask_sensitive
from app.models.database import (
    Conversation,
    Feedback,
    Message,
    MessageTrace,
    TraceFunctionCall,
    User,
)
from app.models.engine import async_session_factory
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest

router = APIRouter(tags=["chat"])


async def _get_or_create_user(user_id: str) -> int:
    """Get existing user or create one. Returns user DB id."""
    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.external_id == user_id).limit(1)
        )
        user = result.scalar_one_or_none()
        if user:
            return user.id

        user = User(external_id=user_id, nickname=user_id, phone="")
        session.add(user)
        await session.commit()
        return user.id


async def _save_conversation(user_db_id: int, intent_agent: str) -> int:
    """Create a conversation record. Returns conversation_id."""
    async with async_session_factory() as session:
        conv = Conversation(
            user_id=user_db_id,
            agent_id={
                "pre_sales": 1,
                "during_sales": 2,
                "after_sales": 3,
            }.get(intent_agent, 1),
            title=None,
            source="api",
            last_message_at=datetime.now(timezone.utc),
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        return conv.id


async def _save_message(conversation_id: int, role: str, content: str) -> int:
    """Save a message and return its id."""
    async with async_session_factory() as session:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        session.add(msg)
        # Update last_message_at on conversation
        from sqlalchemy import update
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=datetime.now(timezone.utc))
        )
        await session.commit()
        await session.refresh(msg)
        return msg.id


async def _save_trace(message_id: int, state: dict) -> None:
    """Persist trace data to message_traces."""
    trace = state.get("trace", {})
    if not trace:
        return

    async with async_session_factory() as session:
        mt = MessageTrace(
            message_id=message_id,
            generation_model=trace.get("model"),
            generation_prompt_tokens=trace.get("prompt_tokens"),
            generation_completion_tokens=trace.get("completion_tokens"),
            generation_duration_ms=trace.get("generation_ms"),
            retrieval_recalled_count=trace.get("retrieval_count"),
            retrieval_duration_ms=trace.get("retrieval_ms"),
            rerank_duration_ms=trace.get("rerank_ms"),
        )
        session.add(mt)
        await session.commit()
        await session.refresh(mt)

        # Tool call details
        for tc in trace.get("tool_call_results", []):
            session.add(TraceFunctionCall(
                trace_id=mt.id,
                tool_name=tc.get("tool", "unknown"),
                is_success=tc.get("success", False),
                result_summary=str(tc.get("data", ""))[:256] if tc.get("data") else tc.get("error", ""),
                duration_ms=tc.get("duration_ms"),
            ))
        await session.commit()


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # Step 1: Mask sensitive info + content safety check
    clean_msg = mask_sensitive(req.message)
    safety = content_safety.check(clean_msg)
    if not safety.passed:
        return ChatResponse(
            conversation_id=req.conversation_id,
            reply=content_safety.block_message(safety.severity, safety.action),
            intent="blocked",
        )

    # Step 2: Intent classification → route to agent
    intent = classify_intent(clean_msg)
    agent = route_to_agent(intent)

    # Step 3: Run agent (LangGraph workflow)
    try:
        state = await agent.run(
            conversation_id=req.conversation_id,
            user_query=clean_msg,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    # Step 4: Persist to database
    message_id = None
    try:
        user_db_id = await _get_or_create_user(req.user_id)
        conv_id = await _save_conversation(user_db_id, intent.target_agent)
        # Use the real conversation_id if generated
        user_msg_id = await _save_message(conv_id, "user", req.message)
        bot_msg_id = await _save_message(conv_id, "bot", state["final_response"])
        await _save_trace(bot_msg_id, state)
        message_id = bot_msg_id
    except Exception as e:
        print(f"[db] Persist warning: {e}")
        conv_id = req.conversation_id

    return ChatResponse(
        conversation_id=conv_id if message_id else req.conversation_id,
        message_id=message_id,
        reply=state["final_response"],
        intent=intent.intent_name,
        handoff=state.get("handoff", False),
        handoff_reason=state.get("handoff_reason", ""),
        trace=state.get("trace"),
    )


@router.post("/feedback")
async def feedback(req: FeedbackRequest) -> dict:
    """Persist user feedback to database."""
    try:
        async with async_session_factory() as session:
            fb = Feedback(
                message_id=req.message_id,
                rating=req.rating,
                reason=req.reason,
            )
            session.add(fb)
            await session.commit()
    except Exception as e:
        print(f"[db] Feedback persist warning: {e}")

    return {"status": "ok", "message_id": req.message_id, "rating": req.rating}


@router.get("/tools")
async def list_tools() -> dict:
    from app.tools.registry import tool_registry

    tools: list[dict] = []
    seen: set[str] = set()
    for spec in tool_registry.list_all():
        if spec.definition.name not in seen:
            seen.add(spec.definition.name)
            tools.append({
                "name": spec.definition.name,
                "display_name": spec.definition.display_name,
                "description": spec.definition.description,
                "version": spec.definition.version,
                "agent_id": spec.agent_id,
            })
    return {"agent": "all", "tools": tools}
