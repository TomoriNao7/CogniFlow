"""Chat REST API endpoint."""

from fastapi import APIRouter, HTTPException

from app.agents.router import classify_intent, route_to_agent
from app.core.security import Severity, SafetyAction, content_safety
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # Step 1: Content safety check
    safety = content_safety.check(req.message)
    if not safety.passed:
        return ChatResponse(
            conversation_id=req.conversation_id,
            reply=content_safety.block_message(safety.severity, safety.action),
            intent="blocked",
        )

    # Step 2: Intent classification → route to agent
    intent = classify_intent(req.message)
    agent = route_to_agent(intent)

    # Step 3: Run agent (LangGraph workflow)
    try:
        state = await agent.run(
            conversation_id=req.conversation_id,
            user_query=req.message,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    return ChatResponse(
        conversation_id=req.conversation_id,
        reply=state["final_response"],
        intent=intent.intent_name,
        handoff=state.get("handoff", False),
        handoff_reason=state.get("handoff_reason", ""),
        trace=state.get("trace"),
    )


@router.post("/feedback")
async def feedback(req: FeedbackRequest) -> dict:
    # TODO: persist feedback to database
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
