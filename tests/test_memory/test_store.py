# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for SQLite memory store."""

from __future__ import annotations

from uuid import uuid4

import pytest

from rapier.memory.store import MemoryStore
from rapier.memory.types import Fact


# ── Helpers ──────────────────────────────────────────────────────────


@pytest.fixture
def tmp_store(tmp_path: Path) -> MemoryStore:
    """Create a temporary store for testing."""
    db_path = tmp_path / "test_memory.db"
    store = MemoryStore(db_path=db_path)
    yield store
    store.close()


def _make_fact(
    topic: str = "auth",
    concept: str = "JWT",
    fact: str = "Uses RS256 signing",
    source: str = "auth.py",
) -> Fact:
    return Fact(
        id=str(uuid4()),
        topic=topic,
        concept=concept,
        fact=fact,
        source_file=source,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestMemoryStore:
    def test_store_and_recall(self, tmp_store: MemoryStore):
        f = _make_fact()
        tmp_store.store(f)
        results = tmp_store.recall_by_topic("auth")
        assert len(results) == 1
        assert results[0].fact == "Uses RS256 signing"

    def test_store_many(self, tmp_store: MemoryStore):
        facts = [_make_fact(fact=f"fact_{i}") for i in range(5)]
        tmp_store.store_many(facts)
        assert tmp_store.count() == 5

    def test_search_by_keyword(self, tmp_store: MemoryStore):
        tmp_store.store(_make_fact(fact="bcrypt with 12 rounds"))
        tmp_store.store(_make_fact(fact="argon2 for password hashing"))
        tmp_store.store(_make_fact(fact="JWT expiry 1h"))

        results = tmp_store.search_by_keyword("bcrypt")
        assert len(results) == 1
        results = tmp_store.search_by_keyword("password")
        assert len(results) == 1

    def test_delete(self, tmp_store: MemoryStore):
        f = _make_fact()
        tmp_store.store(f)
        assert tmp_store.count() == 1
        tmp_store.delete(f.id)
        assert tmp_store.count() == 0

    def test_count(self, tmp_store: MemoryStore):
        assert tmp_store.count() == 0
        tmp_store.store(_make_fact())
        assert tmp_store.count() == 1
        tmp_store.store(_make_fact(fact="another"))
        assert tmp_store.count() == 2

    def test_topics(self, tmp_store: MemoryStore):
        tmp_store.store(_make_fact(topic="auth"))
        tmp_store.store(_make_fact(topic="db"))
        tmp_store.store(_make_fact(topic="auth"))
        topics = tmp_store.topics()
        assert "auth" in topics
        assert "db" in topics

    def test_recall_all(self, tmp_store: MemoryStore):
        for i in range(5):
            tmp_store.store(_make_fact(fact=f"fact_{i}"))
        results = tmp_store.recall_all(limit=3)
        assert len(results) == 3

    def test_recall_by_topic_empty(self, tmp_store: MemoryStore):
        results = tmp_store.recall_by_topic("nonexistent")
        assert len(results) == 0
