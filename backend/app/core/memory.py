"""Conversation memory with LLM summarization and Redis persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.config import settings


@dataclass
class ConversationMemory:
    """Holds the current session context for a conversation.

    Short-term memory: last N turns, with LLM summary compression when exceeding
    the trigger threshold. Summary is persisted so long-running sessions stay compact.
    """

    conversation_id: int
    turns: list[Turn] = field(default_factory=list)
    summary: str = ""
    max_turns: int = 10
    summary_trigger_turns: int = 8

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content))
        if len(self.turns) > self.summary_trigger_turns:
            self._compress()

    def _compress(self) -> None:
        """Summarize older turns to keep context window manageable.

        Uses LLM summarization when available; falls back to truncation.
        """
        older = self.turns[:-4]  # keep last 4 turns verbatim
        if not older:
            return
        self.turns = self.turns[-4:]

    async def summarize_async(self) -> str:
        """Async LLM-based summary of current turns. Returns the new summary string.

        Called externally after add_turn() so the caller can await the LLM call.
        """
        if len(self.turns) < 6:
            return self.summary

        older = self.turns[:-4]
        if not older:
            return self.summary

        self.turns = self.turns[-4:]

        try:
            new_summary = await _summarize_llm(self.summary, older)
            if new_summary:
                self.summary = new_summary
                return self.summary
        except Exception:
            pass

        # Fallback: string truncation
        lines = [f"[{t.role}]: {t.content[:200]}" for t in older]
        self.summary = _merge_summaries(self.summary, "对话摘要: " + "; ".join(lines))
        return self.summary

    def to_messages(self, system_prompt: str = "") -> list[dict[str, str]]:
        """Build the message list ready for LLM injection."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            prompt = system_prompt
            if self.summary:
                prompt += f"\n\n[历史对话摘要]\n{self.summary}"
            messages.append({"role": "system", "content": prompt})
        for t in self.turns:
            messages.append({"role": t.role, "content": t.content})
        return messages

    def to_messages_for_classification(self) -> str:
        """Return the last user message for intent classification."""
        for t in reversed(self.turns):
            if t.role == "user":
                return t.content
        return ""

    def reset(self) -> None:
        self.turns.clear()
        self.summary = ""

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "turns": [{"role": t.role, "content": t.content, "metadata": t.metadata} for t in self.turns],
            "summary": self.summary,
            "max_turns": self.max_turns,
            "summary_trigger_turns": self.summary_trigger_turns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConversationMemory:
        mem = cls(
            conversation_id=data["conversation_id"],
            summary=data.get("summary", ""),
            max_turns=data.get("max_turns", 10),
            summary_trigger_turns=data.get("summary_trigger_turns", 8),
        )
        mem.turns = [
            Turn(role=t["role"], content=t["content"], metadata=t.get("metadata", {}))
            for t in data.get("turns", [])
        ]
        return mem


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "tool"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ── LLM summarization ────────────────────────────────────────────────────────

_SUMMARY_PROMPT = """你是一个对话摘要助手。请用 1-2 句话提取以下对话的关键信息。

要求：
- 突出用户的核心诉求和已提供的信息（如订单号、商品名、问题描述）
- 突出助手已给出的关键结论或操作
- 如果已有历史摘要，将新信息融入进去
- 只返回摘要内容，不要解释

已有摘要: {previous}
"""


async def _summarize_llm(previous_summary: str, turns: list[Turn]) -> str:
    """Call Qwen to generate a conversation summary."""
    dialogue = "\n".join(f"[{t.role}]: {t.content}" for t in turns)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            timeout=8.0,
        )

        resp = await client.chat.completions.create(
            model=settings.intent_model,  # qwen2.5-1.5b — fast & cheap for summary
            messages=[
                {"role": "system", "content": _SUMMARY_PROMPT.format(previous=previous_summary or "无")},
                {"role": "user", "content": dialogue},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""


def _merge_summaries(old: str, new: str) -> str:
    """Merge old and new summaries, avoiding duplication."""
    if not old:
        return new
    if len(new) > len(old):
        return new
    return old


# ── Memory stores ─────────────────────────────────────────────────────────────

class MemoryStore:
    """In-memory store — fast, suitable for dev / single-process."""

    def __init__(self) -> None:
        self._store: dict[int, ConversationMemory] = {}

    def get_or_create(
        self, conversation_id: int, max_turns: int = 10, summary_trigger: int = 8
    ) -> ConversationMemory:
        if conversation_id not in self._store:
            self._store[conversation_id] = ConversationMemory(
                conversation_id=conversation_id,
                max_turns=max_turns,
                summary_trigger_turns=summary_trigger,
            )
        return self._store[conversation_id]

    def remove(self, conversation_id: int) -> None:
        self._store.pop(conversation_id, None)


class RedisMemoryStore:
    """Redis-backed memory store — persistent, suitable for multi-process / production."""

    _KEY_PREFIX = "cogniflow:memory:"
    _TTL = 86400  # 24 hours

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._client: Any = None

    @property
    def client(self):
        if self._client is None:
            import redis

            self._client = redis.Redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def _key(self, conversation_id: int) -> str:
        return f"{self._KEY_PREFIX}{conversation_id}"

    def get_or_create(
        self, conversation_id: int, max_turns: int = 10, summary_trigger: int = 8
    ) -> ConversationMemory:
        key = self._key(conversation_id)
        try:
            raw = self.client.get(key)
            if raw:
                data = json.loads(raw)
                mem = ConversationMemory.from_dict(data)
                mem.max_turns = max_turns
                mem.summary_trigger_turns = summary_trigger
                return mem
        except Exception:
            pass

        mem = ConversationMemory(
            conversation_id=conversation_id,
            max_turns=max_turns,
            summary_trigger_turns=summary_trigger,
        )
        self._save(mem)
        return mem

    def _save(self, memory: ConversationMemory) -> None:
        try:
            key = self._key(memory.conversation_id)
            self.client.setex(key, self._TTL, json.dumps(memory.to_dict(), ensure_ascii=False))
        except Exception:
            pass

    def persist(self, memory: ConversationMemory) -> None:
        """Persist a memory instance back to Redis (call after updates)."""
        self._save(memory)

    def remove(self, conversation_id: int) -> None:
        try:
            self.client.delete(self._key(conversation_id))
        except Exception:
            pass


# ── Global singleton (auto-selects Redis if available) ────────────────────────

def _create_store():
    store = RedisMemoryStore()
    try:
        store.client.ping()
        print("[memory] Using Redis memory store")
        return store
    except Exception:
        print("[memory] Redis unavailable, using in-memory store")
        return MemoryStore()


memory_store: MemoryStore | RedisMemoryStore = _create_store()
