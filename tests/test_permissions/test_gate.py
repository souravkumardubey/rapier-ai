# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for the permission system."""

from __future__ import annotations

import pytest

from rapier.permissions.bash_analyzer import BashAnalyzer, RiskLevel
from rapier.permissions.gate import (
    PermissionGate,
    PermissionMode,
    PermissionResult,
    PermissionVerdict,
)
from rapier.permissions.rules import PermissionRules


# ── BashAnalyzer tests ─────────────────────────────────────────────


class TestBashAnalyzer:
    def setup_method(self):
        self.analyzer = BashAnalyzer()

    def test_safe_command(self):
        result = self.analyzer.analyze("ls -la")
        assert result.safe is True
        assert result.risk_level == RiskLevel.SAFE

    def test_safe_python_command(self):
        result = self.analyzer.analyze("python -m pytest tests/")
        assert result.safe is True

    def test_dangerous_rm_rf(self):
        result = self.analyzer.analyze("rm -rf /")
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert any("rm" in i for i in result.issues)

    def test_dangerous_rm_rf_star(self):
        result = self.analyzer.analyze("rm -rf /*")
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_dangerous_eval(self):
        result = self.analyzer.analyze("eval 'malicious code'")
        assert result.safe is False
        assert result.risk_level == RiskLevel.HIGH
        assert any("eval" in i for i in result.issues)

    def test_command_substitution(self):
        result = self.analyzer.analyze("echo $(whoami)")
        assert result.safe is False  # medium risk is not safe
        assert result.risk_level == RiskLevel.MEDIUM
        assert any("command_substitution" in i for i in result.issues)

    def test_backtick_substitution(self):
        result = self.analyzer.analyze("echo `whoami`")
        assert result.risk_level == RiskLevel.MEDIUM

    def test_protected_path_git(self):
        result = self.analyzer.analyze("rm -rf .git/")
        assert result.safe is False
        assert any(".git/" in i for i in result.issues)

    def test_protected_path_env(self):
        result = self.analyzer.analyze("cat .env")
        assert any(".env" in i for i in result.issues)

    def test_dd_destructive(self):
        result = self.analyzer.analyze("dd if=/dev/zero of=/dev/sda")
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_ssh_risk(self):
        result = self.analyzer.analyze("ssh user@host")
        assert result.risk_level == RiskLevel.MEDIUM

    def test_safe_find_command(self):
        result = self.analyzer.analyze("find . -name '*.py'")
        assert result.safe is True


# ── PermissionRules tests ───────────────────────────────────────────


class TestPermissionRules:
    def setup_method(self):
        self.rules = PermissionRules()

    def test_deny_rm_rf(self):
        assert self.rules.is_denied("bash", {"command": "rm -rf /"}) is True

    def test_deny_mkfs(self):
        assert self.rules.is_denied("bash", {"command": "mkfs /dev/sda"}) is True

    def test_not_denied_ls(self):
        assert self.rules.is_denied("bash", {"command": "ls -la"}) is False

    def test_allow_read_file(self):
        assert self.rules.is_allowed("read_file", {"path": "foo.py"}) is True

    def test_allow_glob(self):
        assert self.rules.is_allowed("glob", {"pattern": "*.py"}) is True

    def test_allow_grep(self):
        assert self.rules.is_allowed("grep", {"pattern": "foo"}) is True

    def test_allow_bash_ls(self):
        assert self.rules.is_allowed("bash", {"command": "ls"}) is True

    def test_allow_bash_python(self):
        assert self.rules.is_allowed("bash", {"command": "python script.py"}) is True

    def test_not_allow_unknown_tool(self):
        assert self.rules.is_allowed("unknown_tool", {}) is False

    def test_protected_path_git(self):
        assert self.rules.is_protected_path(".git/config") is True

    def test_protected_path_env(self):
        assert self.rules.is_protected_path(".env") is True

    def test_protected_path_node_modules(self):
        assert self.rules.is_protected_path("node_modules/package/index.js") is True

    def test_not_protected_normal_path(self):
        assert self.rules.is_protected_path("src/main.py") is False


# ── PermissionGate tests ────────────────────────────────────────────


class TestPermissionGate:
    def setup_method(self):
        self.gate = PermissionGate(mode=PermissionMode.AUTO)

    @pytest.mark.asyncio
    async def test_deny_rm_rf(self):
        result = await self.gate.check("bash", {"command": "rm -rf /"})
        assert result.verdict == PermissionVerdict.DENIED

    @pytest.mark.asyncio
    async def test_allow_read_file(self):
        result = await self.gate.check("read_file", {"path": "foo.py"})
        assert result.verdict == PermissionVerdict.ALLOWED

    @pytest.mark.asyncio
    async def test_auto_mode_allows_bash(self):
        result = await self.gate.check("bash", {"command": "ls -la"})
        assert result.verdict == PermissionVerdict.ALLOWED

    @pytest.mark.asyncio
    async def test_plan_mode_blocks_writes(self):
        gate = PermissionGate(mode=PermissionMode.PLAN)
        result = await gate.check("write_file", {"path": "foo.py", "content": "x"})
        assert result.verdict == PermissionVerdict.DENIED
        assert "Plan mode" in result.reason

    @pytest.mark.asyncio
    async def test_plan_mode_allows_reads(self):
        gate = PermissionGate(mode=PermissionMode.PLAN)
        result = await gate.check("read_file", {"path": "foo.py"})
        assert result.verdict == PermissionVerdict.ALLOWED

    @pytest.mark.asyncio
    async def test_protected_path_blocked(self):
        result = await self.gate.check("write_file", {"path": ".env", "content": "x"})
        assert result.verdict == PermissionVerdict.DENIED
        assert "Protected path" in result.reason

    @pytest.mark.asyncio
    async def test_critical_bash_denied_in_auto(self):
        result = await self.gate.check("bash", {"command": "rm -rf /"})
        assert result.verdict == PermissionVerdict.DENIED

    @pytest.mark.asyncio
    async def test_high_risk_bash_allowed_in_auto(self):
        result = await self.gate.check("bash", {"command": "eval 'echo hello'"})
        assert result.verdict == PermissionVerdict.ALLOWED

    @pytest.mark.asyncio
    async def test_default_mode_asks_for_unknown_tool(self):
        async def ask(tool, inp, reason):
            return True

        gate = PermissionGate(mode=PermissionMode.DEFAULT, on_ask=ask)
        result = await gate.check("unknown_tool", {"input": "do something"})
        assert result.verdict == PermissionVerdict.ALLOWED
        assert "User approved" in result.reason

    @pytest.mark.asyncio
    async def test_default_mode_denies_when_no_callback(self):
        gate = PermissionGate(mode=PermissionMode.DEFAULT)
        result = await gate.check("unknown_tool", {"input": "do something"})
        assert result.verdict == PermissionVerdict.DENIED
        assert "No user prompt" in result.reason

    @pytest.mark.asyncio
    async def test_user_deny(self):
        async def ask(tool, inp, reason):
            return False

        gate = PermissionGate(mode=PermissionMode.DEFAULT, on_ask=ask)
        result = await gate.check("unknown_tool", {"input": "do something"})
        assert result.verdict == PermissionVerdict.DENIED
        assert "User denied" in result.reason


# ── Integration: loop.py with permission gate ───────────────────────


class TestLoopWithPermissions:
    @pytest.mark.asyncio
    async def test_permission_denied_blocks_tool(self):
        """Test that permission gate blocks tool execution in the agent loop."""
        from rapier.loop import agent_loop

        call_count = 0

        class MockTool:
            name = "dangerous_tool"
            description = "A dangerous tool"

            def get_schema(self):
                from rapier.llm.types import ToolDefinition

                return ToolDefinition(
                    name=self.name,
                    description=self.description,
                    parameters={"type": "object", "properties": {}},
                )

            async def execute(self, input):
                nonlocal call_count
                call_count += 1
                return "should not reach here"

        class MockLLM:
            def __init__(self):
                self.call_count = 0

            async def chat(self, messages, tools, system=None, model=None):
                self.call_count += 1
                if self.call_count == 1:
                    from rapier.llm.types import LLMResponse, ToolCall, Usage

                    return LLMResponse(
                        content=None,
                        tool_calls=[ToolCall(id="1", name="dangerous_tool", input={})],
                        usage=Usage(input_tokens=10, output_tokens=10),
                    )
                from rapier.llm.types import LLMResponse, Usage

                return LLMResponse(
                    content="Done",
                    tool_calls=[],
                    usage=Usage(input_tokens=10, output_tokens=10),
                )

        gate = PermissionGate(mode=PermissionMode.AUTO)
        # Override rules to deny this tool
        gate.rules.deny.append({"tool": "dangerous_tool"})

        result = await agent_loop(
            prompt="do something",
            tools={"dangerous_tool": MockTool()},
            llm=MockLLM(),
            system_prompt="test",
            permission_gate=gate,
        )

        # Tool should not have executed
        assert call_count == 0
        assert result.completed is True
