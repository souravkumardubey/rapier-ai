# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — cascading permission gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Awaitable

from rapier.permissions.bash_analyzer import BashAnalyzer, RiskLevel
from rapier.permissions.rules import PermissionRules


class PermissionMode(Enum):
    """Permission modes for the gate."""

    DEFAULT = "default"  # Ask user for risky operations
    AUTO = "auto"  # Allow everything (trusted environments)
    PLAN = "plan"  # Read-only, block all writes/deletes


class PermissionVerdict(Enum):
    """Outcome of a permission check."""

    ALLOWED = "allowed"
    DENIED = "denied"
    ASK = "ask"


@dataclass
class PermissionResult:
    """Result of a permission check."""

    verdict: PermissionVerdict
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.SAFE


# Callback type for asking the user: (tool_name, input, reason) -> bool
AskCallback = Callable[[str, dict[str, Any], str], Awaitable[bool]]


class PermissionGate:
    """Cascading permission gate.

    Decision cascade:
    1. Check deny rules → DENIED (hard deny)
    2. Check bash safety → DENIED if critical, ASK if risky
    3. Check allow rules → ALLOWED (pre-approved)
    4. Check mode (auto/plan) → ASK or ALLOWED
    5. Prompt user → ALLOWED / DENIED
    """

    def __init__(
        self,
        rules: PermissionRules | None = None,
        mode: PermissionMode = PermissionMode.DEFAULT,
        on_ask: AskCallback | None = None,
    ):
        self.rules = rules or PermissionRules()
        self.mode = mode
        self.on_ask = on_ask
        self._bash_analyzer = BashAnalyzer()

    async def check(self, tool_name: str, tool_input: dict[str, Any]) -> PermissionResult:
        """Check if a tool invocation is permitted.

        Returns PermissionResult with verdict and reason.
        """
        # 1. Hard deny rules — cannot be overridden
        if self.rules.is_denied(tool_name, tool_input):
            return PermissionResult(
                verdict=PermissionVerdict.DENIED,
                reason="Blocked by deny rule",
                risk_level=RiskLevel.CRITICAL,
            )

        # 2. Bash-specific safety analysis
        if tool_name == "bash":
            command = tool_input.get("command", "")
            analysis = self._bash_analyzer.analyze(command)

            # Check protected paths first
            if self.rules.is_protected_path(command):
                return PermissionResult(
                    verdict=PermissionVerdict.DENIED,
                    reason=f"Protected path access blocked: {command}",
                    risk_level=RiskLevel.HIGH,
                )

            if analysis.risk_level == RiskLevel.CRITICAL:
                return PermissionResult(
                    verdict=PermissionVerdict.DENIED,
                    reason=f"Critical risk: {'; '.join(analysis.issues)}",
                    risk_level=RiskLevel.CRITICAL,
                )

            if analysis.risk_level == RiskLevel.HIGH:
                if self.mode == PermissionMode.AUTO:
                    return PermissionResult(
                        verdict=PermissionVerdict.ALLOWED,
                        reason="Auto mode — allowing despite high risk",
                        risk_level=RiskLevel.HIGH,
                    )
                return await self._ask_user(
                    tool_name,
                    tool_input,
                    f"High risk command: {'; '.join(analysis.issues)}",
                    RiskLevel.HIGH,
                )

            if analysis.risk_level == RiskLevel.MEDIUM:
                if self.mode == PermissionMode.AUTO:
                    return PermissionResult(
                        verdict=PermissionVerdict.ALLOWED,
                        reason="Auto mode — allowing despite medium risk",
                        risk_level=RiskLevel.MEDIUM,
                    )
                if self.mode == PermissionMode.DEFAULT:
                    return await self._ask_user(
                        tool_name,
                        tool_input,
                        f"Medium risk: {'; '.join(analysis.issues)}",
                        RiskLevel.MEDIUM,
                    )
                # Plan mode — block writes
                return PermissionResult(
                    verdict=PermissionVerdict.DENIED,
                    reason="Plan mode — blocking risky write",
                    risk_level=RiskLevel.MEDIUM,
                )

        # 3. Check protected paths for file-writing tools
        if tool_name in ("write_file", "edit_file"):
            path = tool_input.get("path", "")
            if self.rules.is_protected_path(path):
                return PermissionResult(
                    verdict=PermissionVerdict.DENIED,
                    reason=f"Protected path: {path}",
                    risk_level=RiskLevel.HIGH,
                )

        # 4. Plan mode — block all writes
        if self.mode == PermissionMode.PLAN and tool_name in (
            "write_file",
            "edit_file",
            "bash",
        ):
            return PermissionResult(
                verdict=PermissionVerdict.DENIED,
                reason="Plan mode — read only",
                risk_level=RiskLevel.LOW,
            )

        # 5. Allow rules — pre-approved
        if self.rules.is_allowed(tool_name, tool_input):
            return PermissionResult(
                verdict=PermissionVerdict.ALLOWED,
                reason="Pre-approved by allow rule",
            )

        # 6. Auto mode — allow everything else
        if self.mode == PermissionMode.AUTO:
            return PermissionResult(
                verdict=PermissionVerdict.ALLOWED,
                reason="Auto mode — allowing",
            )

        # 7. Default — ask user for confirmation
        return await self._ask_user(
            tool_name,
            tool_input,
            f"Tool '{tool_name}' not in allow list",
            RiskLevel.LOW,
        )

    async def _ask_user(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        reason: str,
        risk_level: RiskLevel,
    ) -> PermissionResult:
        """Prompt the user for permission."""
        if self.on_ask is None:
            # No callback — deny by default (non-interactive)
            return PermissionResult(
                verdict=PermissionVerdict.DENIED,
                reason=f"No user prompt available — denying: {reason}",
                risk_level=risk_level,
            )

        try:
            allowed = await self.on_ask(tool_name, tool_input, reason)
        except Exception:
            return PermissionResult(
                verdict=PermissionVerdict.DENIED,
                reason="User prompt failed — denying",
                risk_level=risk_level,
            )

        if allowed:
            return PermissionResult(
                verdict=PermissionVerdict.ALLOWED,
                reason=f"User approved: {reason}",
                risk_level=risk_level,
            )

        return PermissionResult(
            verdict=PermissionVerdict.DENIED,
            reason=f"User denied: {reason}",
            risk_level=risk_level,
        )
