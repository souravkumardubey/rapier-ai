# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — memory data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Fact:
    """A single durable fact extracted from tool results."""

    id: str
    topic: str
    concept: str
    fact: str
    source_file: str
    created_at: datetime = field(default_factory=datetime.now)
    embedding: Any = None


@dataclass
class Topic:
    """A topic grouping related concepts."""

    name: str
    concepts: list[str] = field(default_factory=list)
    fact_count: int = 0
