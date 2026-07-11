# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — regex-based bash command safety analyzer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    """Risk level for a bash command."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Numeric ordering for risk comparison
_RISK_ORDER = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    """Return the higher of two risk levels."""
    return a if _RISK_ORDER[a] >= _RISK_ORDER[b] else b


@dataclass
class BashAnalysis:
    """Result of analyzing a bash command."""

    safe: bool
    risk_level: RiskLevel
    issues: list[str] = field(default_factory=list)


class BashAnalyzer:
    """Regex-based bash command safety analyzer.

    Checks for dangerous patterns without requiring a full AST parser.
    Catches the vast majority of harmful commands.
    """

    # Dangerous builtins that can execute arbitrary code
    DANGEROUS_BUILTINS = {
        "eval",
        "source",
        ".",
        "exec",
        "trap",
        "kill",
        "suspend",
        "zmodload",
        "ztcp",
    }

    # Destructive commands that can trash a system
    DESTRUCTIVE_COMMANDS = {
        "rm": [r"\brm\b.*\b(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b", r"\brm\s+-rf\b"],
        "dd": [r"\bdd\b"],
        "mkfs": [r"\bmkfs\b"],
        "format": [r"\bformat\b"],
    }

    # Patterns that indicate code execution / injection
    INJECTION_PATTERNS = [
        ("command_substitution", r"\$\("),
        ("backtick_substitution", r"`[^`]+`"),
        ("process_substitution_read", r"<\("),
        ("process_substitution_write", r">\("),
        ("subshell", r"\([^)]*\)"),
    ]

    # Dangerous pipe/redirect patterns
    DESTRUCTIVE_REDIRECTS = [
        ("overwrite_root", r">\s*/"),
        ("append_sensitive", r">>\s*/etc/"),
    ]

    # Commands that access protected paths
    PROTECTED_PATH_PATTERNS = [
        r"\.git/",
        r"\.env\b",
        r"\.rapier/",
        r"node_modules/",
        r"__pycache__/",
        r"/etc/passwd",
        r"/etc/shadow",
        r"/etc/sudoers",
    ]

    def analyze(self, command: str) -> BashAnalysis:
        """Analyze a bash command for dangerous patterns."""
        issues: list[str] = []
        risk = RiskLevel.SAFE

        # Check for dangerous builtins
        risk = self._check_builtins(command, issues, risk)

        # Check for destructive commands
        risk = self._check_destructive(command, issues, risk)

        # Check for injection patterns
        risk = self._check_injection(command, issues, risk)

        # Check for destructive redirects
        risk = self._check_redirects(command, issues, risk)

        # Check for protected path access
        risk = self._check_protected_paths(command, issues, risk)

        # Check for network exfiltration patterns
        risk = self._check_exfiltration(command, issues, risk)

        return BashAnalysis(
            safe=risk in (RiskLevel.SAFE, RiskLevel.LOW),
            risk_level=risk,
            issues=issues,
        )

    def _check_builtins(
        self, command: str, issues: list[str], current_risk: RiskLevel
    ) -> RiskLevel:
        risk = current_risk
        # Only check the first word (the actual command) for dangerous builtins
        # "find ." is fine — "." is a path argument, not the source builtin
        first_word = command.split()[0] if command.split() else ""
        clean = first_word.lstrip("-").strip("'\"")
        if clean in self.DANGEROUS_BUILTINS:
            issues.append(f"Dangerous builtin: {clean}")
            risk = _max_risk(risk, RiskLevel.HIGH)
        return risk

    def _check_destructive(
        self, command: str, issues: list[str], current_risk: RiskLevel
    ) -> RiskLevel:
        risk = current_risk
        for cmd, patterns in self.DESTRUCTIVE_COMMANDS.items():
            for pattern in patterns:
                if re.search(pattern, command):
                    issues.append(f"Destructive command: {cmd}")
                    risk = _max_risk(risk, RiskLevel.CRITICAL)
                    break
        return risk

    def _check_injection(
        self, command: str, issues: list[str], current_risk: RiskLevel
    ) -> RiskLevel:
        risk = current_risk
        for name, pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, command):
                issues.append(f"Code injection risk: {name}")
                risk = _max_risk(risk, RiskLevel.MEDIUM)
        return risk

    def _check_redirects(
        self, command: str, issues: list[str], current_risk: RiskLevel
    ) -> RiskLevel:
        risk = current_risk
        for name, pattern in self.DESTRUCTIVE_REDIRECTS:
            if re.search(pattern, command):
                issues.append(f"Destructive redirect: {name}")
                risk = _max_risk(risk, RiskLevel.HIGH)
        return risk

    def _check_protected_paths(
        self, command: str, issues: list[str], current_risk: RiskLevel
    ) -> RiskLevel:
        risk = current_risk
        for pattern in self.PROTECTED_PATH_PATTERNS:
            if re.search(pattern, command):
                issues.append(f"Protected path access: {pattern}")
                risk = _max_risk(risk, RiskLevel.HIGH)
        return risk

    def _check_exfiltration(
        self, command: str, issues: list[str], current_risk: RiskLevel
    ) -> RiskLevel:
        risk = current_risk
        exfil_patterns = [
            (r"\bcurl\b.*\bPOST\b", "HTTP POST (possible exfiltration)"),
            (r"\bwget\b.*\bpost\b", "HTTP POST (possible exfiltration)"),
            (r"\bssh\b", "SSH connection"),
            (r"\bscp\b", "SCP file transfer"),
            (r"\brsync\b.*:", "rsync remote transfer"),
            (r"\bnc\b.*-e", "netcat with exec (reverse shell)"),
        ]
        for pattern, desc in exfil_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                issues.append(f"Network risk: {desc}")
                risk = _max_risk(risk, RiskLevel.MEDIUM)
        return risk
