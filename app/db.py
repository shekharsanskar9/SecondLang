"""SQLite history of everything you refined, so you can review your mistakes later."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .refiner import word_diff
from .schemas import Correction, RefineResponse

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    tone        TEXT NOT NULL,
    context     TEXT,
    original    TEXT NOT NULL,
    refined     TEXT NOT NULL,
    corrections TEXT NOT NULL,
    tip         TEXT,
    provider    TEXT
);
"""


class HistoryStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def save(self, item: RefineResponse) -> RefineResponse:
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO history (created_at, tone, context, original, refined, corrections, tip, provider)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (created, item.tone, item.context, item.original, item.refined,
                 json.dumps([c.model_dump() for c in item.corrections]), item.tip, item.provider),
            )
        return item.model_copy(update={"id": cur.lastrowid, "created_at": created})

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> RefineResponse:
        return RefineResponse(
            id=row["id"],
            created_at=row["created_at"],
            tone=row["tone"],
            context=row["context"],
            original=row["original"],
            refined=row["refined"],
            corrections=[Correction(**c) for c in json.loads(row["corrections"])],
            tip=row["tip"] or "",
            provider=row["provider"] or "",
            diff=word_diff(row["original"], row["refined"]),
        )

    def list(self, limit: int = 50) -> list[RefineResponse]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_item(r) for r in rows]

    def delete(self, item_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM history WHERE id = ?", (item_id,)).rowcount > 0

    def clear(self) -> int:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM history").rowcount

    def stats(self) -> dict:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT corrections FROM history").fetchall()
        counts: Counter[str] = Counter()
        for r in rows:
            counts.update(c.get("type", "other") for c in json.loads(r["corrections"]))
        return {"total": len(rows), "by_type": dict(counts.most_common())}
