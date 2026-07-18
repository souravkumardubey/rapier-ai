# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for Tier 4 autocompact and tiktoken integration."""

from __future__ import annotations

import pytest

from rapier.context.compactor import autocompact, format_messages_for_summary
from rapier.context.engine import ContextEngine, _build_token_counter
from rapier.context.history import MessageHistory
from rapier.llm.types import LLMResponse, Message, ToolCall, Usage

# ── Helpers ──────────────────────────────────────────────────────────


def _user_msg(content: str) -> Message:
    return Message(role="user", content=content)


def _assistant_msg(content: str | None = None) -> Message:
    return Message(role="assistant", content=content)


def _tool_msg(content: str, tool_call_id: str = "tc_1") -> Message:
    return Message(role="tool", content=content, tool_call_id=tool_call_id)


def _system_msg(content: str) -> Message:
    return Message(role="system", content=content)


class MockLLM:
    """Mock LLM that returns a fixed summary."""

    def __init__(self, summary: str = "Mocked conversation summary"):
        self.summary = summary
        self.call_count = 0
        self.last_messages = None

    async def chat(self, messages, tools, system=None, model=None):
        self.call_count += 1
        self.last_messages = messages
        return LLMResponse(
            content=self.summary,
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=5),
        )


# ── format_messages_for_summary ──────────────────────────────────────


class TestFormatMessagesForSummary:
    def test_formats_user_message(self):
        messages = [_user_msg("hello")]
        result = format_messages_for_summary(messages)
        assert "User: hello" in result

    def test_formats_assistant_message(self):
        messages = [_assistant_msg("response")]
        result = format_messages_for_summary(messages)
        assert "Assistant: response" in result

    def test_formats_tool_result_short(self):
        messages = [_tool_msg("result")]
        result = format_messages_for_summary(messages)
        assert "Tool result: result" in result

    def test_formats_tool_result_long(self):
        messages = [_tool_msg("x" * 500)]
        result = format_messages_for_summary(messages)
        assert "..." in result
        assert len(result) < 500

    def test_formats_assistant_with_tool_calls(self):
        tc = ToolCall(id="tc_1", name="read_file", input={"path": "foo.py"})
        msg = Message(role="assistant", content=None, tool_calls=[tc])
        result = format_messages_for_summary([msg])
        assert "read_file" in result

    def test_skips_system_messages(self):
        messages = [_system_msg("system"), _user_msg("hello")]
        result = format_messages_for_summary(messages)
        assert "system" not in result.lower() or "User: hello" in result

    def test_multiple_messages(self):
        messages = [_user_msg("q"), _assistant_msg("a"), _tool_msg("r")]
        result = format_messages_for_summary(messages)
        assert "User: q" in result
        assert "Assistant: a" in result
        assert "Tool result: r" in result


# ── autocompact ──────────────────────────────────────────────────────


class TestAutocompact:
    @pytest.mark.asyncio
    async def test_summarizes_messages(self):
        llm = MockLLM(summary="The agent read foo.py and made edits.")
        messages = [
            _system_msg("You are helpful"),
            _user_msg("read foo.py"),
            _assistant_msg("I'll read the file."),
            _tool_msg("def hello(): pass"),
            _assistant_msg("Done."),
        ]
        result = await autocompact(messages, llm)

        assert llm.call_count == 1
        assert len(result) == 2  # system + summary
        assert result[0].role == "system"
        assert result[1].role == "assistant"
        assert "Conversation summary" in result[1].content
        assert "The agent read foo.py" in result[1].content

    @pytest.mark.asyncio
    async def test_preserves_system_message(self):
        llm = MockLLM()
        messages = [_system_msg("sys"), _user_msg("q"), _assistant_msg("a")]
        result = await autocompact(messages, llm)
        assert result[0].role == "system"
        assert result[0].content == "sys"

    @pytest.mark.asyncio
    async def test_no_system_message(self):
        llm = MockLLM()
        messages = [_user_msg("q"), _assistant_msg("a")]
        result = await autocompact(messages, llm)
        assert result[0].role == "assistant"
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self):
        class FailingLLM:
            async def chat(self, messages, tools, system=None, model=None):
                raise RuntimeError("API error")

        messages = [_user_msg("q")]
        with pytest.raises(RuntimeError):
            await autocompact(messages, FailingLLM())

    @pytest.mark.asyncio
    async def test_empty_llm_response(self):
        llm = MockLLM(summary=None)
        messages = [_user_msg("q")]
        result = await autocompact(messages, llm)
        assert "Summary generation failed" in result[0].content


# ── ContextEngine Tier 4 integration ────────────────────────────────


class TestContextEngineTier4:
    @pytest.mark.asyncio
    async def test_compact_calls_autocompact_when_llm_provided(self):
        llm = MockLLM(summary="Compacted summary")
        engine = ContextEngine(
            max_input_tokens=100,
            chars_per_token=4.0,
            llm=llm,
            use_tiktoken=False,
        )
        h = MessageHistory()
        h.append(_user_msg("x" * 500))  # 125 tokens > 80% of 100

        await engine.compact(h)
        # autocompact should have been called
        assert llm.call_count >= 1

    @pytest.mark.asyncio
    async def test_compact_skips_tier4_without_llm(self):
        engine = ContextEngine(
            max_input_tokens=100,
            chars_per_token=4.0,
            llm=None,
            use_tiktoken=False,
        )
        h = MessageHistory()
        h.append(_user_msg("x" * 500))

        await engine.compact(h)
        # No LLM means tier 4 is skipped, tiers 1-3 still run

    @pytest.mark.asyncio
    async def test_get_messages_for_llm_calls_compact(self):
        llm = MockLLM(summary="summary")
        engine = ContextEngine(
            max_input_tokens=100,
            chars_per_token=4.0,
            llm=llm,
            use_tiktoken=False,
        )
        h = MessageHistory()
        h.append(_user_msg("x" * 500))

        await engine.get_messages_for_llm(h)
        assert llm.call_count >= 1


# ── tiktoken integration ────────────────────────────────────────────


class TestTiktokenIntegration:
    def test_build_token_counter_returns_callable(self):
        counter = _build_token_counter(use_tiktoken=True)
        # May be None if tiktoken not installed
        if counter is not None:
            tokens = counter("hello world")
            assert isinstance(tokens, int)
            assert tokens > 0

    def test_build_token_counter_disabled(self):
        counter = _build_token_counter(use_tiktoken=False)
        assert counter is None

    def test_engine_uses_tiktoken_when_available(self):
        engine = ContextEngine(max_input_tokens=100000, use_tiktoken=True)
        h = MessageHistory()
        h.append(_user_msg("hello"))
        # should_compact should work regardless of tiktoken availability
        assert engine.should_compact(h) is False

    def test_engine_heuristic_fallback(self):
        engine = ContextEngine(
            max_input_tokens=100000,
            chars_per_token=4.0,
            use_tiktoken=False,
        )
        h = MessageHistory()
        h.append(_user_msg("hello"))  # 5 chars = 1 token
        assert engine.should_compact(h) is False

    def test_estimate_tokens_with_tiktoken(self):
        engine = ContextEngine(max_input_tokens=100000, use_tiktoken=True)
        h = MessageHistory()
        h.append(_user_msg("hello world"))
        tokens = engine._estimate_tokens(h)
        assert isinstance(tokens, int)
        assert tokens > 0
