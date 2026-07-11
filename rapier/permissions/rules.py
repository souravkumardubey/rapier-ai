# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — permission rules definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath


# Default protected paths — always blocked from write/delete
DEFAULT_PROTECTED_PATHS: list[str] = [
    ".git/",
    ".rapier/",
    ".env",
    ".env.*",
    "node_modules/",
    "__pycache__/",
    ".DS_Store",
]

# Default deny patterns — tool+input combos that are always blocked
DEFAULT_DENY_PATTERNS: list[dict[str, str]] = [
    {"tool": "bash", "pattern": "rm -rf /"},
    {"tool": "bash", "pattern": "rm -rf /*"},
    {"tool": "bash", "pattern": "mkfs"},
    {"tool": "bash", "pattern": "dd if=/dev/zero"},
    {"tool": "bash", "pattern": "dd if=/dev/random"},
    {"tool": "bash", "pattern": r":(){ :\|:& };:"},  # fork bomb
]

# Default allow patterns — tool+input combos that are pre-approved
DEFAULT_ALLOW_PATTERNS: list[dict[str, str]] = [
    {"tool": "read_file"},
    {"tool": "glob"},
    {"tool": "grep"},
    {"tool": "web_fetch"},
    {"tool": "bash", "pattern": "ls"},
    {"tool": "bash", "pattern": "pwd"},
    {"tool": "bash", "pattern": "cat"},
    {"tool": "bash", "pattern": "head"},
    {"tool": "bash", "pattern": "tail"},
    {"tool": "bash", "pattern": "wc"},
    {"tool": "bash", "pattern": "echo"},
    {"tool": "bash", "pattern": "which"},
    {"tool": "bash", "pattern": "find"},
    {"tool": "bash", "pattern": "git status"},
    {"tool": "bash", "pattern": "git log"},
    {"tool": "bash", "pattern": "git diff"},
    {"tool": "bash", "pattern": "git show"},
    {"tool": "bash", "pattern": "python"},
    {"tool": "bash", "pattern": "pip"},
    {"tool": "bash", "pattern": "uv"},
    {"tool": "bash", "pattern": "pytest"},
    {"tool": "bash", "pattern": "ruff"},
    {"tool": "bash", "pattern": "mypy"},
]


@dataclass
class PermissionRules:
    """Defines what is denied, allowed, and needs confirmation.

    Rules are checked in order:
    1. deny — hard block, cannot be overridden
    2. allow — pre-approved, no confirmation needed
    3. Everything else falls through to the gate's mode logic
    """

    deny: list[dict[str, str]] = field(default_factory=lambda: list(DEFAULT_DENY_PATTERNS))
    allow: list[dict[str, str]] = field(default_factory=lambda: list(DEFAULT_ALLOW_PATTERNS))
    protected_paths: list[str] = field(default_factory=lambda: list(DEFAULT_PROTECTED_PATHS))

    def is_denied(self, tool_name: str, tool_input: dict) -> bool:
        """Check if a tool invocation is hard-denied."""
        for rule in self.deny:
            rule_tool = rule.get("tool")
            if rule_tool and rule_tool != tool_name:
                continue
            pattern = rule.get("pattern")
            if not pattern:
                # Tool-level deny (no pattern) — block all invocations of this tool
                return True
            if self._input_matches_pattern(tool_input, pattern):
                return True
        return False

    def is_allowed(self, tool_name: str, tool_input: dict) -> bool:
        """Check if a tool invocation is pre-approved."""
        for rule in self.allow:
            if rule.get("tool") and rule["tool"] != tool_name:
                continue
            pattern = rule.get("pattern")
            if not pattern:
                # Tool-level allow (e.g., read_file is always allowed)
                return True
            if self._input_matches_pattern(tool_input, pattern):
                return True
        return False

    def is_protected_path(self, path: str) -> bool:
        """Check if a file path is in the protected list."""
        p = PurePosixPath(path)
        for protected in self.protected_paths:
            # Check each part of the path
            for part in p.parts:
                if PurePosixPath(part).match(protected):
                    return True
            # Also check the full path string
            if PurePosixPath(path).match(protected):
                return True
        return False

    def _input_matches_pattern(self, tool_input: dict, pattern: str) -> bool:
        """Check if any string value in tool_input contains the pattern."""
        for value in tool_input.values():
            if isinstance(value, str) and pattern in value:
                return True
        return False
