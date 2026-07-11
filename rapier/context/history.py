# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — message history management with timestamps."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rapier.llm.types import Message


class MessageHistory:
    """Managed message list with timestamps for age-based compaction.

    Wraps a list[Message] and tracks when each message was added.
    The Message dataclass is immutable-ish (no timestamp field),
    so we store timestamps in a parallel dict keyed by index.
    """

    def __init__(self, system_prompt: str | None = None):
        self._messages: list[Message] = []
        self._timestamps: dict[int, datetime] = {}
        if system_prompt:
            self._messages.append(Message(role="system", content=system_prompt))
            self._timestamps[0] = datetime.now()

    @property
    def messages(self) -> list[Message]:
        return self._messages

    @property
    def timestamps(self) -> dict[int, datetime]:
        return self._timestamps

    def __len__(self) -> int:
        return len(self._messages)

    def __getitem__(self, index: int) -> Message:
        return self._messages[index]

    def append(self, message: Message) -> None:
        """Append a message with a timestamp."""
        idx = len(self._messages)
        self._messages.append(message)
        self._timestamps[idx] = datetime.now()

    def extend(self, messages: list[Message]) -> None:
        """Append multiple messages with timestamps."""
        for msg in messages:
            self.append(msg)

    def replace(self, messages: list[Message]) -> None:
        """Replace all messages (after compaction). Resets timestamps."""
        self._messages = messages
        self._timestamps = {i: datetime.now() for i in range(len(messages))}

    def get_system_message(self) -> Message | None:
        """Get the system message if present."""
        if self._messages and self._messages[0].role == "system":
            return self._messages[0]
        return None

    def to_list(self) -> list[Message]:
        """Return a plain list of messages (for passing to LLM)."""
        return list(self._messages)

    def estimate_tokens(self, chars_per_token: float = 4.0) -> int:
        """Rough token estimate based on character count."""
        total_chars = 0
        for msg in self._messages:
            if msg.content:
                total_chars += len(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total_chars += len(str(tc.input))
        return int(total_chars / chars_per_token)
