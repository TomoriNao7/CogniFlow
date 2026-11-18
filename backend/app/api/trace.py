"""trace 回放 API —— 还原一次回答的检索与生成完整轨迹。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.models.database import (
    KnowledgeChunk,
    KnowledgeDocument,
    Message,
    MessageTrace,
    TraceFunctionCall,
    TraceRetrievalChunk,
)
from app.models.engine import async_session_factory

router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("/{trace_id}")
async def get_trace(trace_id: int) -> dict:
    """返回某条 message_traces 记录的完整轨迹，含每个 chunk 的明细。"""
    async with async_session_factory() as session:
        mt = (
            await session.execute(
                select(MessageTrace).where(MessageTrace.id == trace_id)
            )
        ).scalar_one_or_none()
        if mt is None:
            raise HTTPException(404, f"trace {trace_id} not found")

        message = (
            await session.execute(
                select(Message).where(Message.id == mt.message_id)
            )
        ).scalar_one_or_none()

        chunks = (
            await session.execute(
                select(TraceRetrievalChunk)
                .where(TraceRetrievalChunk.trace_id == trace_id)
                .order_by(TraceRetrievalChunk.rank_position)
            )
        ).scalars().all()

        chunk_detail = []
        for rc in chunks:
            kc = (
                await session.execute(
                    select(KnowledgeChunk).where(KnowledgeChunk.id == rc.chunk_id)
                )
            ).scalar_one_or_none()
            doc = None
            if kc is not None:
                doc = (
                    await session.execute(
                        select(KnowledgeDocument).where(
                            KnowledgeDocument.id == kc.document_id
                        )
                    )
                ).scalar_one_or_none()
            chunk_detail.append({
                "chunk_id": rc.chunk_id,
                "document_id": rc.document_id,
                "source": rc.source,
                "score": float(rc.score),
                "rank_position": rc.rank_position,
                "content": kc.content if kc else None,
                "source_document": kc.source_document if kc else None,
                "document_title": doc.title if doc else None,
            })

        tool_calls = (
            await session.execute(
                select(TraceFunctionCall)
                .where(TraceFunctionCall.trace_id == trace_id)
                .order_by(TraceFunctionCall.id)
            )
        ).scalars().all()

    return {
        "trace_id": mt.id,
        "message_id": mt.message_id,
        "message_content": message.content if message else None,
        "intent_agent": mt.intent_agent,
        "intent_confidence": float(mt.intent_confidence) if mt.intent_confidence is not None else None,
        "retrieval_query": mt.retrieval_query,
        "retrieval_recalled_count": mt.retrieval_recalled_count,
        "retrieval_top_k": mt.retrieval_top_k,
        "retrieval_duration_ms": mt.retrieval_duration_ms,
        "rerank_model": mt.rerank_model,
        "rerank_duration_ms": mt.rerank_duration_ms,
        "generation_model": mt.generation_model,
        "generation_prompt_tokens": mt.generation_prompt_tokens,
        "generation_completion_tokens": mt.generation_completion_tokens,
        "generation_duration_ms": mt.generation_duration_ms,
        "retrieval_chunks": chunk_detail,
        "tool_calls": [
            {
                "tool_name": tc.tool_name,
                "is_success": tc.is_success,
                "result_summary": tc.result_summary,
                "duration_ms": tc.duration_ms,
            }
            for tc in tool_calls
        ],
    }
