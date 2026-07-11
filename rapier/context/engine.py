# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — context engine orchestrator."""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from rapier.context.compactor import (
    CompactionCircuitBreaker,
    collapse_tool_outputs,
    microcompact,
    reactive_compact,
    snip_old_results,
)
from rapier.context.history import MessageHistory
from rapier.llm.types import Message


# Default context limits
DEFAULT_MAX_INPUT_TOKENS = 150_000  # conservative for most models
DEFAULT_CHARS_PER_TOKEN = 4.0
AUTOCOMPACT_THRESHOLD = 0.80  # trigger at 80% capacity


class ContextEngine:
    """Manages what the LLM sees each turn.

    Applies 5-tier compaction to keep context within token limits:
    1. Snip — clear old tool results (>60min)
    2. Microcompact — remove stale tool results
    3. Context Collapse — truncate large tool outputs
    4. Autocompact — LLM summarizes history (not implemented here, needs LLM ref)
    5. Reactive — emergency truncation on API error
    """

    def __init__(
        self,
        max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
        autocompact_threshold: float = AUTOCOMPACT_THRESHOLD,
    ):
        self.max_input_tokens = max_input_tokens
        self.chars_per_token = chars_per_token
        self.autocompact_threshold = autocompact_threshold
        self._circuit_breaker = CompactionCircuitBreaker()

    @property
    def circuit_breaker(self) -> CompactionCircuitBreaker:
        return self._circuit_breaker

    def should_compact(self, history: MessageHistory) -> bool:
        """Check if context is approaching token limit."""
        estimated = history.estimate_tokens(self.chars_per_token)
        return estimated > self.max_input_tokens * self.autocompact_threshold

    def compact(self, history: MessageHistory) -> MessageHistory:
        """Apply compaction tiers 1-3 in sequence.

        Returns the history with compacted messages.
        """
        if self._circuit_breaker.is_open:
            return history

        try:
            messages = history.messages
            timestamps = history.timestamps

            # Tier 1: Snip old results (>60 min)
            messages = snip_old_results(messages, timestamps)

            # Tier 2: Microcompact — clear older tool results
            messages = microcompact(messages)

            # Tier 3: Collapse — truncate large tool outputs
            messages = collapse_tool_outputs(messages)

            history.replace(messages)
            self._circuit_breaker.record_success()
            return history

        except Exception:
            self._circuit_breaker.record_failure()
            return history

    def handle_context_error(self, history: MessageHistory) -> MessageHistory:
        """Handle API context_length_exceeded error.

        Applies Tier 5 (reactive) emergency truncation.
        """
        try:
            messages = reactive_compact(history.messages)
            history.replace(messages)
            self._circuit_breaker.record_success()
            return history
        except Exception:
            self._circuit_breaker.record_failure()
            return history

    def get_messages_for_llm(self, history: MessageHistory) -> list[Message]:
        """Get the message list ready for LLM consumption.

        Applies compaction if needed, then returns the list.
        """
        if self.should_compact(history):
            history = self.compact(history)
        return history.to_list()
