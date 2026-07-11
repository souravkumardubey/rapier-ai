# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for the context engine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from rapier.context.compactor import (
    CompactionCircuitBreaker,
    collapse_tool_outputs,
    microcompact,
    reactive_compact,
    snip_old_results,
)
from rapier.context.engine import ContextEngine
from rapier.context.history import MessageHistory
from rapier.llm.types import Message, ToolCall


# ── Helper ──────────────────────────────────────────────────────────


def _tool_msg(content: str, tool_call_id: str = "tc_1") -> Message:
    return Message(role="tool", content=content, tool_call_id=tool_call_id)


def _user_msg(content: str) -> Message:
    return Message(role="user", content=content)


def _assistant_msg(content: str | None = None, tool_calls: list[ToolCall] | None = None) -> Message:
    return Message(role="assistant", content=content, tool_calls=tool_calls)


# ── Tier 1: Snip ────────────────────────────────────────────────────


class TestSnip:
    def test_snips_old_tool_results(self):
        messages = [
            _user_msg("hello"),
            _tool_msg("old result"),
            _assistant_msg("done"),
        ]
        timestamps = {
            0: datetime.now(),
            1: datetime.now() - timedelta(minutes=90),
            2: datetime.now(),
        }
        result = snip_old_results(messages, timestamps, max_age_minutes=60)
        assert result[1].content == "[old result cleared]"
        assert result[0].content == "hello"

    def test_keeps_recent_tool_results(self):
        messages = [
            _user_msg("hello"),
            _tool_msg("recent result"),
        ]
        timestamps = {
            0: datetime.now(),
            1: datetime.now() - timedelta(minutes=30),
        }
        result = snip_old_results(messages, timestamps, max_age_minutes=60)
        assert result[1].content == "recent result"

    def test_preserves_tool_call_id(self):
        messages = [_tool_msg("old", tool_call_id="tc_99")]
        timestamps = {0: datetime.now() - timedelta(minutes=120)}
        result = snip_old_results(messages, timestamps, max_age_minutes=60)
        assert result[0].tool_call_id == "tc_99"

    def test_non_tool_messages_unchanged(self):
        messages = [_user_msg("hello"), _assistant_msg("hi")]
        timestamps = {0: datetime.now() - timedelta(hours=5), 1: datetime.now()}
        result = snip_old_results(messages, timestamps, max_age_minutes=60)
        assert result[0].content == "hello"
        assert result[1].content == "hi"


# ── Tier 2: Microcompact ────────────────────────────────────────────


class TestMicrocompact:
    def test_clears_old_tool_results(self):
        messages = [
            _user_msg("q1"),
            _tool_msg("r1"),
            _assistant_msg("a1"),
            _tool_msg("r2"),
            _assistant_msg("a2"),
            _user_msg("q2"),
            _tool_msg("r3"),
            _assistant_msg("a3"),
        ]
        result = microcompact(messages, keep_recent=4)
        # First tool result should be cleared
        assert result[1].content == "[tool result cleared]"
        # Recent ones preserved
        assert result[5].content == "q2"
        assert result[6].content == "r3"

    def test_short_history_unchanged(self):
        messages = [_user_msg("hi"), _assistant_msg("hello")]
        result = microcompact(messages, keep_recent=10)
        assert len(result) == 2
        assert result[0].content == "hi"

    def test_preserves_message_order(self):
        messages = [
            _user_msg("q"),
            _tool_msg("r1"),
            _assistant_msg("a"),
            _tool_msg("r2"),
        ]
        result = microcompact(messages, keep_recent=2)
        assert result[0].role == "user"
        assert result[1].role == "tool"
        assert result[2].role == "assistant"
        assert result[3].role == "tool"


# ── Tier 3: Context Collapse ────────────────────────────────────────


class TestCollapseToolOutputs:
    def test_truncates_large_outputs(self):
        large_content = "x" * 5000
        messages = [_tool_msg(large_content)]
        result = collapse_tool_outputs(messages, max_tool_chars=2000)
        assert len(result[0].content) < 5000
        assert "truncated" in result[0].content

    def test_keeps_small_outputs(self):
        messages = [_tool_msg("short result")]
        result = collapse_tool_outputs(messages, max_tool_chars=2000)
        assert result[0].content == "short result"

    def test_non_tool_messages_unchanged(self):
        messages = [_user_msg("hello")]
        result = collapse_tool_outputs(messages, max_tool_chars=2000)
        assert result[0].content == "hello"


# ── Tier 5: Reactive ────────────────────────────────────────────────


class TestReactiveCompact:
    def test_keeps_last_n_messages(self):
        messages = [_user_msg(f"msg{i}") for i in range(20)]
        result = reactive_compact(messages, keep_last=5)
        assert len(result) == 6  # 1 summary + 5 kept
        assert "15 earlier messages truncated" in result[0].content

    def test_short_history_unchanged(self):
        messages = [_user_msg("hi"), _assistant_msg("hello")]
        result = reactive_compact(messages, keep_last=5)
        assert len(result) == 2

    def test_empty_history(self):
        result = reactive_compact([], keep_last=5)
        assert result == []


# ── Circuit Breaker ─────────────────────────────────────────────────


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CompactionCircuitBreaker(max_failures=3)
        assert cb.is_open is False

    def test_opens_after_max_failures(self):
        cb = CompactionCircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_success_resets_count(self):
        cb = CompactionCircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert cb.is_open is False  # only 1 failure after reset

    def test_reset(self):
        cb = CompactionCircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True
        cb.reset()
        assert cb.is_open is False
        assert cb.failures == 0


# ── MessageHistory ──────────────────────────────────────────────────


class TestMessageHistory:
    def test_init_with_system_prompt(self):
        h = MessageHistory(system_prompt="You are helpful")
        assert len(h) == 1
        assert h[0].role == "system"
        assert h[0].content == "You are helpful"

    def test_init_without_system_prompt(self):
        h = MessageHistory()
        assert len(h) == 0

    def test_append(self):
        h = MessageHistory()
        h.append(_user_msg("hello"))
        assert len(h) == 1
        assert h[0].content == "hello"

    def test_extend(self):
        h = MessageHistory()
        h.extend([_user_msg("a"), _assistant_msg("b")])
        assert len(h) == 2

    def test_replace(self):
        h = MessageHistory()
        h.append(_user_msg("old"))
        h.replace([_user_msg("new")])
        assert len(h) == 1
        assert h[0].content == "new"

    def test_to_list(self):
        h = MessageHistory()
        h.append(_user_msg("hello"))
        msgs = h.to_list()
        assert isinstance(msgs, list)
        assert msgs[0].content == "hello"

    def test_estimate_tokens(self):
        h = MessageHistory()
        h.append(_user_msg("hello world"))  # 11 chars
        tokens = h.estimate_tokens(chars_per_token=4.0)
        assert tokens == 2  # 11/4 = 2.75 -> 2


# ── ContextEngine ───────────────────────────────────────────────────


class TestContextEngine:
    def test_should_compact_when_over_threshold(self):
        engine = ContextEngine(max_input_tokens=100, chars_per_token=4.0)
        h = MessageHistory()
        # 500 chars = 125 tokens > 80% of 100 = 80
        h.append(_user_msg("x" * 500))
        assert engine.should_compact(h) is True

    def test_should_not_compact_when_under_threshold(self):
        engine = ContextEngine(max_input_tokens=1000, chars_per_token=4.0)
        h = MessageHistory()
        h.append(_user_msg("hello"))
        assert engine.should_compact(h) is False

    def test_compact_applies_tiers(self):
        engine = ContextEngine(max_input_tokens=10000)
        h = MessageHistory()
        h.append(_user_msg("hello"))
        h.append(_tool_msg("x" * 5000))
        h.append(_assistant_msg("done"))
        result = engine.compact(h)
        # Tool output should be truncated
        assert len(result[1].content) < 5000

    def test_circuit_breaker_opens(self):
        engine = ContextEngine()
        engine.circuit_breaker.record_failure()
        engine.circuit_breaker.record_failure()
        engine.circuit_breaker.record_failure()
        assert engine.circuit_breaker.is_open is True
        # Compaction should be skipped
        h = MessageHistory()
        h.append(_user_msg("test"))
        original_len = len(h)
        engine.compact(h)
        assert len(h) == original_len  # unchanged

    def test_handle_context_error(self):
        engine = ContextEngine()
        h = MessageHistory()
        for i in range(20):
            h.append(_user_msg(f"msg{i}"))
        result = engine.handle_context_error(h)
        assert len(result) < 20


# ── Integration: loop.py with context engine ────────────────────────


class TestLoopWithContext:
    @pytest.mark.asyncio
    async def test_loop_with_context_engine(self):
        """Test that the agent loop works with a context engine."""
        from rapier.loop import agent_loop
        from rapier.llm.types import LLMResponse, Usage

        class MockLLM:
            def __init__(self):
                self.call_count = 0

            async def chat(self, messages, tools, system=None, model=None):
                self.call_count += 1
                return LLMResponse(
                    content="Done",
                    tool_calls=[],
                    usage=Usage(input_tokens=10, output_tokens=5),
                )

        engine = ContextEngine(max_input_tokens=1_000_000)
        result = await agent_loop(
            prompt="hello",
            tools={},
            llm=MockLLM(),
            system_prompt="test",
            context_engine=engine,
        )
        assert result.completed is True
        assert result.content == "Done"
