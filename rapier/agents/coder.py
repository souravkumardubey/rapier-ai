# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — coder specialist agent."""

from __future__ import annotations

from typing import Any

from rapier.agents.base import Agent, AgentConfig


def create_coder(llm: Any, all_tools: dict[str, Any]) -> Agent:
    """Create a Coder agent (Sonnet-class, code tools only)."""
    return Agent(
        config=AgentConfig(
            name="Coder",
            allowed_tools=["read_file", "write_file", "edit_file", "bash", "grep", "glob"],
            max_iterations=20,
            system_prompt_extra=(
                "You are a code specialist. Write clean, tested code.\n"
                "Always read files before modifying them.\n"
                "Run tests after making changes."
            ),
        ),
        llm=llm,
        all_tools=all_tools,
    )
