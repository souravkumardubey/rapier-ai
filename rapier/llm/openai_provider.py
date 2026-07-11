# Copyright (c) 2025 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — OpenAI API adapter."""

from __future__ import annotations

import json
import os
from typing import Any

from rapier.llm.types import LLMResponse, Message, ToolCall, ToolDefinition, Usage


class OpenAIClient:
    """OpenAI API client."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or "gpt-4o"
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system: str | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Send a chat request to OpenAI."""
        import openai

        client = openai.AsyncOpenAI(api_key=self.api_key)

        # Convert messages
        api_messages: list[dict[str, Any]] = []
        if system:
            api_messages.append({"role": "system", "content": system})
        for m in messages:
            api_messages.append(m.to_dict())

        # Convert tools
        api_tools = [t.to_dict() for t in tools] if tools else None

        # Make request
        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "messages": api_messages,
        }
        if api_tools:
            kwargs["tools"] = api_tools

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        # Parse response
        content = choice.message.content
        tool_calls: list[ToolCall] = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        input=args,
                    )
                )

        usage = Usage()
        if response.usage:
            usage = Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
        )
