# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — vector recall using sentence-transformers."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from rapier.memory.store import MemoryStore
from rapier.memory.types import Fact

logger = logging.getLogger(__name__)


class VectorRecall:
    """Semantic search using sentence-transformers embeddings."""

    def __init__(
        self,
        store: MemoryStore,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.store = store
        self.model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed, falling back to keyword search"
                )
                return None
        return self._model

    def embed(self, text: str) -> np.ndarray | None:
        """Embed text using sentence-transformers."""
        model = self._get_model()
        if model is None:
            return None
        return model.encode(text, convert_to_numpy=True)

    def recall(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.3,
    ) -> list[tuple[Fact, float]]:
        """Semantic search across all facts.

        Returns list of (fact, score) tuples sorted by relevance.
        Falls back to keyword search if sentence-transformers unavailable.
        """
        query_embedding = self.embed(query)
        if query_embedding is None:
            facts = self.store.search_by_keyword(query, limit)
            return [(f, 1.0) for f in facts]

        all_facts = self.store.recall_all(limit=10000)
        scored: list[tuple[Fact, float]] = []

        for fact in all_facts:
            if fact.embedding is not None:
                score = self._cosine_similarity(query_embedding, fact.embedding)
                if score >= min_score:
                    scored.append((fact, float(score)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def store_with_embedding(self, fact: Fact) -> None:
        """Store a fact with its embedding computed."""
        if fact.embedding is None:
            fact.embedding = self.embed(f"{fact.topic} {fact.concept}: {fact.fact}")
        self.store.store(fact)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
