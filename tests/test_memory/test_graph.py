# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for knowledge graph."""

from __future__ import annotations

from pathlib import Path

import pytest

from rapier.memory.graph import KnowledgeGraph
from rapier.memory.store import MemoryStore


# ── Helpers ──────────────────────────────────────────────────────────


@pytest.fixture
def tmp_graph(tmp_path: Path) -> KnowledgeGraph:
    """Create a temporary graph for testing."""
    store = MemoryStore(db_path=tmp_path / "test_graph.db")
    graph = KnowledgeGraph(store=store)
    yield graph
    store.close()


# ── Tests ────────────────────────────────────────────────────────────


class TestKnowledgeGraph:
    def test_add_fact_and_recall(self, tmp_graph: KnowledgeGraph):
        tmp_graph.add_fact(
            topic="auth",
            concept="JWT",
            fact="Uses RS256 signing",
            source_file="auth.py",
        )
        results = tmp_graph.recall("RS256")
        assert len(results) == 1
        assert results[0].fact == "Uses RS256 signing"

    def test_add_facts_batch(self, tmp_graph: KnowledgeGraph):
        facts = [
            {"topic": "auth", "concept": "JWT", "fact": "RS256 signing"},
            {"topic": "auth", "concept": "session", "fact": "Redis-backed"},
            {"topic": "db", "concept": "ORM", "fact": "SQLAlchemy"},
        ]
        result = tmp_graph.add_facts(facts, source_file="config.py")
        assert len(result) == 3
        assert tmp_graph.store.count() == 3

    def test_recall_by_topic(self, tmp_graph: KnowledgeGraph):
        tmp_graph.add_fact(topic="auth", concept="JWT", fact="fact1")
        tmp_graph.add_fact(topic="auth", concept="session", fact="fact2")
        tmp_graph.add_fact(topic="db", concept="ORM", fact="fact3")

        results = tmp_graph.recall_by_topic("auth")
        assert len(results) == 2

    def test_topics_returns_hierarchy(self, tmp_graph: KnowledgeGraph):
        tmp_graph.add_fact(topic="auth", concept="JWT", fact="fact1")
        tmp_graph.add_fact(topic="auth", concept="session", fact="fact2")
        tmp_graph.add_fact(topic="db", concept="ORM", fact="fact3")

        topics = tmp_graph.topics()
        assert len(topics) == 2

        auth_topic = next(t for t in topics if t.name == "auth")
        assert auth_topic.fact_count == 2
        assert "JWT" in auth_topic.concepts
        assert "session" in auth_topic.concepts

    def test_stats(self, tmp_graph: KnowledgeGraph):
        tmp_graph.add_fact(topic="auth", concept="JWT", fact="fact1")
        tmp_graph.add_fact(topic="db", concept="ORM", fact="fact2")

        stats = tmp_graph.stats()
        assert stats["total_facts"] == 2
        assert stats["topics"] == 2
        assert "auth" in stats["topic_list"]
        assert "db" in stats["topic_list"]
