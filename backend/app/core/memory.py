from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationMemory:
    """Holds the current session context for a conversation.

    Short-term memory: current session, last N turns, with summary compression
    when exceeding the trigger threshold.
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
        """Summarize older turns to keep context window manageable."""
        older = self.turns[:-4]  # keep last 4 turns verbatim
        if not older:
            return
        lines = [f"[{t.role}]: {t.content[:200]}" for t in older]
        self.summary = "对话摘要: " + "; ".join(lines)
        self.turns = self.turns[-4:]

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


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "tool"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryStore:
    """In-memory store mapping conversation_id -> ConversationMemory.
    In production, this is backed by Redis.
    """

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


memory_store = MemoryStore()
