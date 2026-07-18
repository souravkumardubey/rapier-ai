# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — Anthropic API adapter."""

from __future__ import annotations

import os
from typing import Any

from rapier.llm.retry import with_retry
from rapier.llm.types import LLMResponse, Message, ToolCall, ToolDefinition, Usage

# Retryable Anthropic errors
_RETRYABLE_ERRORS: tuple[type[Exception], ...] = (
    Exception,  # Anthropic SDK raises various APIError subclasses
)


class AnthropicClient:
    """Anthropic Claude API client."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or "claude-sonnet-4-20250514"
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system: str | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Send a chat request to Anthropic Claude."""

        async def _call() -> LLMResponse:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key)

            # Convert messages
            api_messages = [m.to_dict() for m in messages]

            # Convert tools
            api_tools = [t.to_dict() for t in tools] if tools else None

            # Make request
            kwargs: dict[str, Any] = {
                "model": model or self.model,
                "max_tokens": 8192,
                "messages": api_messages,
            }
            if system:
                kwargs["system"] = system
            if api_tools:
                kwargs["tools"] = api_tools

            response = await client.messages.create(**kwargs)

            # Parse response
            content = None
            tool_calls: list[ToolCall] = []

            for block in response.content:
                if block.type == "text":
                    content = block.text
                elif block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.id,
                            name=block.name,
                            input=block.input,
                        )
                    )

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage=Usage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                ),
            )

        return await with_retry(_call, retryable_errors=_RETRYABLE_ERRORS)
