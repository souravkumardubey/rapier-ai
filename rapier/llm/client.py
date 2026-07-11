# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — provider-agnostic LLM client."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rapier.llm.types import LLMResponse, Message, ToolDefinition


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients."""

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system: str | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Send a chat request to the LLM."""
        ...


def get_client(provider: str, model: str | None = None) -> LLMClient:
    """Factory function to get an LLM client by provider name."""
    if provider == "anthropic":
        from rapier.llm.anthropic import AnthropicClient

        return AnthropicClient(model=model)
    elif provider == "openai":
        from rapier.llm.openai_provider import OpenAIClient

        return OpenAIClient(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'.")
