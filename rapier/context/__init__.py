# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — context management package."""

from rapier.context.compactor import (
    CompactionCircuitBreaker,
    collapse_tool_outputs,
    microcompact,
    reactive_compact,
    snip_old_results,
)
from rapier.context.engine import ContextEngine
from rapier.context.history import MessageHistory

__all__ = [
    "CompactionCircuitBreaker",
    "ContextEngine",
    "MessageHistory",
    "collapse_tool_outputs",
    "microcompact",
    "reactive_compact",
    "snip_old_results",
]
