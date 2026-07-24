# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for vector recall."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from rapier.memory.recall import VectorRecall
from rapier.memory.store import MemoryStore
from rapier.memory.types import Fact


# ── Helpers ──────────────────────────────────────────────────────────


@pytest.fixture
def tmp_recall(tmp_path: Path) -> VectorRecall:
    """Create a temporary recall instance for testing."""
    store = MemoryStore(db_path=tmp_path / "test_recall.db")
    yield VectorRecall(store=store, model_name="all-MiniLM-L6-v2")
    store.close()


def _make_fact(topic: str = "auth", concept: str = "JWT", fact: str = "RS256") -> Fact:
    return Fact(
        id="test-id",
        topic=topic,
        concept=concept,
        fact=fact,
        source_file="test.py",
    )


class MockSentenceTransformer:
    """Mock SentenceTransformer that doesn't need network."""

    def encode(self, text: str, convert_to_numpy: bool = True) -> np.ndarray:
        import hashlib

        # Build a deterministic embedding from character-level features so that
        # texts sharing characters get positively-correlated vectors.
        vec = np.zeros(384, dtype=np.float32)
        for _i, ch in enumerate(text):
            seed = int(hashlib.md5(ch.encode()).hexdigest()[:8], 16) % (2**31)
            rng = np.random.RandomState(seed)
            vec += rng.randn(384).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


# ── Tests ────────────────────────────────────────────────────────────


class TestVectorRecall:
    def test_cosine_similarity(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert VectorRecall._cosine_similarity(a, b) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert VectorRecall._cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert VectorRecall._cosine_similarity(a, b) == 0.0

    def test_store_with_embedding(self, tmp_recall: VectorRecall):
        with patch.object(tmp_recall, "_get_model", return_value=MockSentenceTransformer()):
            fact = _make_fact()
            tmp_recall.store_with_embedding(fact)
            assert tmp_recall.store.count() == 1

    def test_recall_falls_back_to_keyword(self, tmp_path: Path):
        """When model is None, recall uses keyword search."""
        store = MemoryStore(db_path=tmp_path / "test_keyword.db")
        recall = VectorRecall(store=store)
        recall._model = None  # Force fallback

        fact = _make_fact(fact="bcrypt hashing with 12 rounds")
        store.store(fact)

        with patch.object(recall, "_get_model", return_value=None):
            results = recall.recall("bcrypt")
            assert len(results) >= 1
        store.close()

    def test_recall_with_embeddings(self, tmp_path: Path):
        """Test recall with mock embeddings."""
        store = MemoryStore(db_path=tmp_path / "test_vec.db")
        recall = VectorRecall(store=store)
        mock_model = MockSentenceTransformer()

        # Store facts with embeddings
        for i, fact_text in enumerate(["RS256 signing", "password hashing", "JWT tokens"]):
            fact = _make_fact(fact=fact_text, topic=f"topic_{i}", concept=f"concept_{i}")
            fact.embedding = mock_model.encode(fact_text)
            store.store(fact)

        with patch.object(recall, "_get_model", return_value=mock_model):
            results = recall.recall("signing", min_score=0.0)
            assert len(results) > 0
            assert all(isinstance(score, float) for _, score in results)
        store.close()
