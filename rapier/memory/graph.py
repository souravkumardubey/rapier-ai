# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — knowledge graph with topic/concept/fact hierarchy."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from rapier.memory.store import MemoryStore
from rapier.memory.types import Fact, Topic


class KnowledgeGraph:
    """Topic -> Concept -> Fact hierarchy with storage backend."""

    def __init__(self, store: MemoryStore):
        self.store = store

    def add_fact(
        self,
        topic: str,
        concept: str,
        fact: str,
        source_file: str = "",
        embedding: Any = None,
    ) -> Fact:
        """Add a fact to the knowledge graph."""
        f = Fact(
            id=str(uuid4()),
            topic=topic,
            concept=concept,
            fact=fact,
            source_file=source_file,
            embedding=embedding,
        )
        self.store.store(f)
        return f

    def add_facts(self, facts: list[dict[str, str]], source_file: str = "") -> list[Fact]:
        """Add multiple facts from a list of dicts."""
        result = []
        for f in facts:
            result.append(
                self.add_fact(
                    topic=f.get("topic", "general"),
                    concept=f.get("concept", "general"),
                    fact=f.get("fact", ""),
                    source_file=source_file,
                )
            )
        return result

    def recall(self, query: str, limit: int = 10) -> list[Fact]:
        """Recall facts relevant to a query (keyword-based)."""
        return self.store.search_by_keyword(query, limit)

    def recall_by_topic(self, topic: str, limit: int = 10) -> list[Fact]:
        """Recall all facts for a topic."""
        return self.store.recall_by_topic(topic, limit)

    def topics(self) -> list[Topic]:
        """Get all topics with their concept counts."""
        all_facts = self.store.recall_all(limit=10000)
        topic_map: dict[str, dict[str, int]] = {}
        for f in all_facts:
            if f.topic not in topic_map:
                topic_map[f.topic] = {}
            if f.concept not in topic_map[f.topic]:
                topic_map[f.topic][f.concept] = 0
            topic_map[f.topic][f.concept] += 1

        return [
            Topic(
                name=topic,
                concepts=list(concepts.keys()),
                fact_count=sum(concepts.values()),
            )
            for topic, concepts in topic_map.items()
        ]

    def stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        topics = self.topics()
        return {
            "total_facts": self.store.count(),
            "topics": len(topics),
            "topic_list": [t.name for t in topics],
        }
