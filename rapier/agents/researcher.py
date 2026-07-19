# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — researcher specialist agent."""

from __future__ import annotations

from typing import Any

from rapier.agents.base import Agent, AgentConfig


def create_researcher(llm: Any, all_tools: dict[str, Any]) -> Agent:
    """Create a Researcher agent (Haiku-class, read-only tools)."""
    return Agent(
        config=AgentConfig(
            name="Researcher",
            allowed_tools=["read_file", "grep", "glob", "web_fetch"],
            max_iterations=10,
            system_prompt_extra=(
                "You are a research specialist. Gather information efficiently.\n"
                "Use grep and glob to find relevant code.\n"
                "Summarize findings concisely."
            ),
        ),
        llm=llm,
        all_tools=all_tools,
    )
