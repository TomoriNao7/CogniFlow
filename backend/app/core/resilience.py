"""Retry with exponential backoff and circuit breaker for tool calls."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.config import settings


def is_retryable(error: Exception) -> bool:
    """Network/timeout errors are retryable; business errors are not."""
    msg = str(error).lower()
    retryable = ["timeout", "connection", "network", "unreachable", "refused", "reset"]
    return any(kw in msg for kw in retryable)


async def retry_with_backoff(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int | None = None,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Call fn with retry on retryable errors. Delay: 1s → 2s → 4s …"""
    retries = max_retries if max_retries is not None else settings.tool_retry_count
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < retries and is_retryable(e):
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                break

    raise last_error  # type: ignore[misc]


@dataclass
class CircuitBreaker:
    """Tracks consecutive failures; opens circuit when threshold exceeded."""

    failure_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    last_failure_time: float = 0.0
    state: str = "closed"  # closed | open | half_open

    def record_success(self) -> None:
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def is_open(self) -> bool:
        if self.state == "open":
            if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                self.failure_count = 0
                return False
            return True
        return False


# Per-tool circuit breakers (tool_name → CircuitBreaker)
_circuits: dict[str, CircuitBreaker] = {}


def circuit_check(tool_name: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a tool."""
    if tool_name not in _circuits:
        _circuits[tool_name] = CircuitBreaker()
    return _circuits[tool_name]
