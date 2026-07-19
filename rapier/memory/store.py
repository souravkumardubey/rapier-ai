# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — SQLite-backed memory storage."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from rapier.memory.types import Fact

DEFAULT_DB_PATH = Path.home() / ".rapier" / "memory.db"


class MemoryStore:
    """SQLite-backed storage for facts."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS facts ("
            "id TEXT PRIMARY KEY, "
            "topic TEXT NOT NULL, "
            "concept TEXT NOT NULL, "
            "fact TEXT NOT NULL, "
            "source_file TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "embedding BLOB"
            ")"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_topic ON facts(topic)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_concept ON facts(concept)"
        )
        self._conn.commit()

    def store(self, fact: Fact) -> None:
        """Store a fact."""
        embedding_bytes = _serialize_embedding(fact.embedding) if fact.embedding is not None else None
        self._conn.execute(
            "INSERT OR REPLACE INTO facts "
            "(id, topic, concept, fact, source_file, created_at, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                fact.id,
                fact.topic,
                fact.concept,
                fact.fact,
                fact.source_file,
                fact.created_at.isoformat(),
                embedding_bytes,
            ),
        )
        self._conn.commit()

    def store_many(self, facts: list[Fact]) -> None:
        """Store multiple facts."""
        for fact in facts:
            self.store(fact)

    def recall_by_topic(self, topic: str, limit: int = 10) -> list[Fact]:
        """Recall facts by exact topic match."""
        cursor = self._conn.execute(
            "SELECT id, topic, concept, fact, source_file, created_at, embedding "
            "FROM facts WHERE topic = ? ORDER BY created_at DESC LIMIT ?",
            (topic, limit),
        )
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def recall_all(self, limit: int = 100) -> list[Fact]:
        """Recall all facts (most recent first)."""
        cursor = self._conn.execute(
            "SELECT id, topic, concept, fact, source_file, created_at, embedding "
            "FROM facts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def search_by_keyword(self, keyword: str, limit: int = 10) -> list[Fact]:
        """Simple keyword search across facts."""
        cursor = self._conn.execute(
            "SELECT id, topic, concept, fact, source_file, created_at, embedding "
            "FROM facts WHERE fact LIKE ? OR concept LIKE ? OR topic LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
        )
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def delete(self, fact_id: str) -> bool:
        """Delete a fact by ID."""
        cursor = self._conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def count(self) -> int:
        """Count total facts."""
        cursor = self._conn.execute("SELECT COUNT(*) FROM facts")
        return cursor.fetchone()[0]

    def topics(self) -> list[str]:
        """List all unique topics."""
        cursor = self._conn.execute("SELECT DISTINCT topic FROM facts ORDER BY topic")
        return [row[0] for row in cursor.fetchall()]

    def _row_to_fact(self, row: tuple) -> Fact:
        return Fact(
            id=row[0],
            topic=row[1],
            concept=row[2],
            fact=row[3],
            source_file=row[4],
            created_at=datetime.fromisoformat(row[5]),
            embedding=_deserialize_embedding(row[6]) if row[6] else None,
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()


def _serialize_embedding(embedding: Any) -> bytes:
    """Serialize numpy array to bytes for SQLite storage."""
    import numpy as np

    if isinstance(embedding, np.ndarray):
        return embedding.tobytes()
    return bytes(embedding)


def _deserialize_embedding(data: bytes) -> Any:
    """Deserialize bytes back to numpy array."""
    import numpy as np

    return np.frombuffer(data, dtype=np.float32)
