# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — 5-tier context compaction strategy."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from rapier.llm.types import Message

# ── Tier 1: Snip ────────────────────────────────────────────────────


def snip_old_results(
    messages: list[Message],
    timestamps: dict[int, datetime],
    max_age_minutes: int = 60,
    now: datetime | None = None,
) -> list[Message]:
    """Replace old tool results with a placeholder.

    Tier 1 — Free. Oldest tool results are cleared.
    """
    now = now or datetime.now()
    cutoff = now - timedelta(minutes=max_age_minutes)

    result: list[Message] = []
    for i, msg in enumerate(messages):
        if msg.role == "tool":
            ts = timestamps.get(i)
            if ts and ts < cutoff:
                result.append(
                    Message(
                        role="tool",
                        content="[old result cleared]",
                        tool_call_id=msg.tool_call_id,
                    )
                )
                continue
        result.append(msg)
    return result


# ── Tier 2: Microcompact ────────────────────────────────────────────


def microcompact(messages: list[Message], keep_recent: int = 10) -> list[Message]:
    """Remove stale tool results, keeping recent ones intact.

    Tier 2 — Low cost. Preserves message order for cache hits.
    """
    if len(messages) <= keep_recent:
        return messages

    # Find the last tool_use index in the recent window
    recent = messages[-keep_recent:]
    old = messages[:-keep_recent]

    result: list[Message] = []
    for msg in old:
        if msg.role == "tool":
            result.append(
                Message(
                    role="tool",
                    content="[tool result cleared]",
                    tool_call_id=msg.tool_call_id,
                )
            )
        else:
            result.append(msg)

    result.extend(recent)
    return result


# ── Tier 3: Context Collapse ────────────────────────────────────────


def collapse_tool_outputs(
    messages: list[Message],
    max_tool_chars: int = 2000,
) -> list[Message]:
    """Truncate large tool outputs to save context space.

    Tier 3 — Low cost. Keeps first N chars + summary line.
    """
    result: list[Message] = []
    for msg in messages:
        if msg.role == "tool" and msg.content and len(msg.content) > max_tool_chars:
            truncated = msg.content[:max_tool_chars]
            remaining = len(msg.content) - max_tool_chars
            result.append(
                Message(
                    role="tool",
                    content=f"{truncated}\n\n... [{remaining} chars truncated]",
                    tool_call_id=msg.tool_call_id,
                )
            )
        else:
            result.append(msg)
    return result


# ── Tier 4: Autocompact ─────────────────────────────────────────────


def format_messages_for_summary(messages: list[Message]) -> str:
    """Format messages into a readable string for LLM summarization."""
    lines: list[str] = []
    for msg in messages:
        if msg.role == "system":
            continue
        if msg.role == "user":
            lines.append(f"User: {msg.content or ''}")
        elif msg.role == "assistant":
            if msg.tool_calls:
                tools = ", ".join(tc.name for tc in msg.tool_calls)
                lines.append(f"Assistant: [called tools: {tools}]")
            if msg.content:
                lines.append(f"Assistant: {msg.content}")
        elif msg.role == "tool":
            # Keep short summaries of tool results
            content = msg.content or ""
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"Tool result: {content}")
    return "\n".join(lines)


async def autocompact(
    messages: list[Message],
    llm: Any,
    max_summary_chars: int = 8000,
) -> list[Message]:
    """Summarize conversation history using LLM.

    Tier 4 — Medium cost. Produces a coherent summary of the conversation
    so the agent retains context without keeping every message.
    """
    from rapier.llm.types import Message as LLMMessage

    formatted = format_messages_for_summary(messages)

    # Keep system message if present
    system_msg = messages[0] if messages and messages[0].role == "system" else None

    summary_prompt = (
        f"Summarize the following conversation concisely.\n"
        f"Focus on: key decisions made, files modified, current state of work, "
        f"and any pending tasks.\n"
        f"Keep the summary under {max_summary_chars} characters.\n\n"
        f"Conversation:\n{formatted}"
    )

    response = await llm.chat(
        messages=[LLMMessage(role="user", content=summary_prompt)],
        tools=[],
    )

    summary_content = response.content or "[Summary generation failed]"

    result: list[Message] = []
    if system_msg:
        result.append(system_msg)
    result.append(
        Message(
            role="assistant",
            content=f"[Conversation summary]\n{summary_content}",
        )
    )
    return result


# ── Tier 5: Reactive ────────────────────────────────────────────────


def reactive_compact(
    messages: list[Message],
    keep_last: int = 5,
) -> list[Message]:
    """Emergency truncation when API returns context_length_exceeded.

    Tier 5 — Emergency. Keeps system message + last N messages.
    """
    if not messages:
        return messages

    # Find system message (if first message)
    system_msg: Message | None = None
    rest = messages
    if messages[0].role == "system":
        system_msg = messages[0]
        rest = messages[1:]

    # Keep the last N messages
    kept = rest[-keep_last:] if len(rest) > keep_last else rest

    result: list[Message] = []
    if system_msg:
        result.append(system_msg)

    # Add a summary message if we dropped content
    dropped = len(rest) - len(kept)
    if dropped > 0:
        result.append(
            Message(
                role="assistant",
                content=f"[{dropped} earlier messages truncated due to context limit]",
            )
        )

    result.extend(kept)
    return result


# ── Circuit Breaker ─────────────────────────────────────────────────


class CompactionCircuitBreaker:
    """Prevents infinite compaction loops.

    After 3 consecutive failures, compaction is skipped for the session.
    """

    def __init__(self, max_failures: int = 3):
        self.failures = 0
        self.max_failures = max_failures
        self._open = False

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.max_failures:
            self._open = True

    def record_success(self) -> None:
        self.failures = 0

    @property
    def is_open(self) -> bool:
        return self._open

    def reset(self) -> None:
        self.failures = 0
        self._open = False
