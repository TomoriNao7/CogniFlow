"""Admin panel REST API — conversations, feedback, knowledge, agents, tools."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.models.database import (
    Agent,
    AgentRetrievalParam,
    Conversation,
    Feedback,
    KnowledgeChunk,
    KnowledgeDocument,
    Message,
    Tool,
)
from app.models.engine import async_session_factory

router = APIRouter(prefix="/admin", tags=["admin"])

# Upload destination — project root / data/
UPLOAD_DIR = str(
    __import__("pathlib").Path(__file__).parent.parent.parent.parent / "data"
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AgentUpdate(BaseModel):
    model: str | None = None
    system_prompt: str | None = None
    top_k: int | None = None
    similarity_threshold: float | None = None
    bm25_weight: float | None = None


# ── Dashboard stats ───────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard_stats():
    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_conv = (await session.execute(select(func.count(Conversation.id)))).scalar() or 0
        today_conv = (await session.execute(
            select(func.count(Conversation.id)).where(Conversation.created_at >= today)
        )).scalar() or 0
        active_conv = (await session.execute(
            select(func.count(Conversation.id)).where(Conversation.status == "active")
        )).scalar() or 0
        handoff_conv = (await session.execute(
            select(func.count(Conversation.id)).where(Conversation.status == "handoff")
        )).scalar() or 0
        total_msgs = (await session.execute(select(func.count(Message.id)))).scalar() or 0
        helpful = (await session.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "helpful")
        )).scalar() or 0
        unhelpful = (await session.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "unhelpful")
        )).scalar() or 0
        total_fb = helpful + unhelpful
        satisfaction = round(helpful / total_fb * 100, 1) if total_fb > 0 else 100.0

        # Agent distribution
        agent_dist = (await session.execute(
            select(Conversation.agent_id, func.count(Conversation.id))
            .where(Conversation.agent_id.isnot(None))
            .group_by(Conversation.agent_id)
        )).all()
        agent_map = {1: "售前 Agent", 2: "售中 Agent", 3: "售后 Agent"}
        agents = [
            {"name": agent_map.get(aid, f"Agent {aid}"), "count": cnt}
            for aid, cnt in agent_dist
        ]

        return {
            "total_conversations": total_conv,
            "today_conversations": today_conv,
            "active_conversations": active_conv,
            "total_messages": total_msgs,
            "handoff_count": handoff_conv,
            "satisfaction": satisfaction,
            "total_feedback": total_fb,
            "agent_distribution": agents,
        }


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(page: int = 1, page_size: int = 20, status: str = ""):
    async with async_session_factory() as session:
        q = select(Conversation).order_by(desc(Conversation.last_message_at))
        if status:
            q = q.where(Conversation.status == status)
        offset = (page - 1) * page_size
        result = await session.execute(q.limit(page_size).offset(offset))
        convs = result.scalars().all()

        agent_names = {1: "售前客服", 2: "售中客服", 3: "售后客服"}

        rows: list[dict] = []
        for c in convs:
            msg_count = (await session.execute(
                select(func.count(Message.id)).where(Message.conversation_id == c.id)
            )).scalar() or 0
            rows.append({
                "id": c.id,
                "user_id": c.user_id,
                "agent_name": agent_names.get(c.agent_id or 1, "售前客服"),
                "status": c.status,
                "title": c.title or f"会话 #{c.id}",
                "message_count": msg_count,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        return {"rows": rows, "page": page, "page_size": page_size}


@router.get("/conversations/{conv_id}/messages")
async def conversation_messages(conv_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        msgs = result.scalars().all()
        return {
            "conversation_id": conv_id,
            "messages": [
                {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else None}
                for m in msgs
            ],
        }


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.get("/feedback")
async def list_feedback(page: int = 1, page_size: int = 20, rating: str = ""):
    async with async_session_factory() as session:
        q = select(Feedback).order_by(desc(Feedback.created_at))
        if rating:
            q = q.where(Feedback.rating == rating)
        offset = (page - 1) * page_size
        result = await session.execute(q.limit(page_size).offset(offset))
        items = result.scalars().all()

        return {
            "rows": [
                {
                    "id": f.id,
                    "message_id": f.message_id,
                    "rating": f.rating,
                    "reason": f.reason,
                    "review_status": f.review_status,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in items
            ],
            "page": page, "page_size": page_size,
        }


@router.get("/feedback/stats")
async def feedback_stats():
    async with async_session_factory() as session:
        total = (await session.execute(select(func.count(Feedback.id)))).scalar() or 0
        helpful = (await session.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "helpful")
        )).scalar() or 0
        unhelpful = (await session.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "unhelpful")
        )).scalar() or 0
        pending = (await session.execute(
            select(func.count(Feedback.id)).where(Feedback.review_status == "pending")
        )).scalar() or 0

        rate = round(helpful / total * 100, 1) if total > 0 else 100.0

        return {
            "total": total,
            "helpful": helpful,
            "unhelpful": unhelpful,
            "satisfaction_rate": rate,
            "pending_review": pending,
        }


# ── Knowledge ─────────────────────────────────────────────────────────────────

@router.get("/knowledge")
async def list_knowledge(page: int = 1, page_size: int = 20):
    async with async_session_factory() as session:
        q = select(KnowledgeDocument).order_by(desc(KnowledgeDocument.created_at))
        offset = (page - 1) * page_size
        result = await session.execute(q.limit(page_size).offset(offset))
        docs = result.scalars().all()

        rows: list[dict] = []
        for d in docs:
            chunk_count = (await session.execute(
                select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.document_id == d.id)
            )).scalar() or 0
            total_retrievals = (await session.execute(
                select(func.coalesce(func.sum(KnowledgeChunk.retrieval_count), 0))
                .where(KnowledgeChunk.document_id == d.id)
            )).scalar() or 0
            rows.append({
                "id": d.id,
                "title": d.title,
                "file_type": d.file_type,
                "split_method": d.split_method,
                "chunk_count": chunk_count,
                "total_retrievals": total_retrievals,
                "status": d.status,
                "version": d.version,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })
        return {"rows": rows, "page": page, "page_size": page_size}


@router.get("/knowledge/stats")
async def knowledge_stats():
    async with async_session_factory() as session:
        total_docs = (await session.execute(
            select(func.count(KnowledgeDocument.id))
        )).scalar() or 0
        total_chunks = (await session.execute(
            select(func.count(KnowledgeChunk.id))
        )).scalar() or 0
        total_retrievals = (await session.execute(
            select(func.coalesce(func.sum(KnowledgeChunk.retrieval_count), 0))
        )).scalar() or 0
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_retrievals": total_retrievals,
        }


# ── Agents ────────────────────────────────────────────────────────────────────

@router.get("/agents")
async def list_agents():
    async with async_session_factory() as session:
        result = await session.execute(select(Agent).order_by(Agent.id))
        agents = result.scalars().all()

        rows: list[dict] = []
        for a in agents:
            params_result = await session.execute(
                select(AgentRetrievalParam).where(AgentRetrievalParam.agent_id == a.id)
            )
            params = {p.param_key: p.param_value for p in params_result.scalars().all()}
            rows.append({
                "id": a.id,
                "name": a.name,
                "display_name": a.display_name,
                "model": a.model,
                "system_prompt": a.system_prompt,
                "status": a.status,
                "retrieval_params": params,
            })
        return {"agents": rows}


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, body: AgentUpdate):
    async with async_session_factory() as session:
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if not agent:
            raise HTTPException(404, "Agent not found")

        if body.model is not None:
            agent.model = body.model
        if body.system_prompt is not None:
            agent.system_prompt = body.system_prompt
        agent.updated_at = datetime.now(timezone.utc)
        await session.commit()

        # Update retrieval params
        for key, val in [("top_k", body.top_k), ("similarity_threshold", body.similarity_threshold), ("bm25_weight", body.bm25_weight)]:
            if val is not None:
                existing = (await session.execute(
                    select(AgentRetrievalParam).where(
                        AgentRetrievalParam.agent_id == agent_id,
                        AgentRetrievalParam.param_key == key,
                    )
                )).scalar_one_or_none()
                if existing:
                    existing.param_value = str(val)
                else:
                    session.add(AgentRetrievalParam(agent_id=agent_id, param_key=key, param_value=str(val)))
        await session.commit()

        return {"status": "ok", "agent_id": agent_id}


# ── Tools ─────────────────────────────────────────────────────────────────────

@router.get("/tools")
async def list_admin_tools():
    async with async_session_factory() as session:
        result = await session.execute(select(Tool).order_by(Tool.id))
        tools = result.scalars().all()
        return {
            "tools": [
                {
                    "id": t.id,
                    "name": t.name,
                    "display_name": t.display_name,
                    "description": t.description,
                    "http_method": t.http_method,
                    "endpoint_url": t.endpoint_url,
                    "version": t.version,
                    "status": t.status,
                    "timeout_ms": t.timeout_ms,
                    "retry_count": t.retry_count,
                }
                for t in tools
            ]
        }


# ── Knowledge upload ──────────────────────────────────────────────────────────

@router.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """Upload a document, save it, and run the ingestion pipeline."""
    if not file.filename:
        raise HTTPException(400, "No file selected")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".md", ".faq", ".txt", ".pdf", ".docx", ".xlsx"):
        raise HTTPException(400, f"Unsupported format: {ext}. Supports .md, .faq, .txt, .pdf, .docx, .xlsx")

    # Detect split method
    SPLIT_MAP = {
        "md": "structure", "faq": "qa_boundary", "txt": "fixed_size",
        "pdf": "semantic", "docx": "semantic", "xlsx": "row_table",
    }
    split_method = SPLIT_MAP.get(ext.lstrip("."), "fixed_size")
    file_type = ext.lstrip(".")

    # Save file to data/ directory
    save_dir = os.path.join(UPLOAD_DIR, file_type)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run ingestion (includes DB persistence via _persist_to_db)
    try:
        from app.rag.ingestion import ingest_file
        stats = ingest_file(save_path)
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {e}")

    return {
        "status": "ok",
        "filename": file.filename,
        "document_id": stats.get("document_id"),
        "chunks": stats.get("chunks", 0),
        "split_method": split_method,
        "file_type": file_type,
        "elapsed_ms": stats.get("elapsed_ms", 0),
    }
