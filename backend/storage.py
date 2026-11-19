import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .datasets import canonical_json


class Store:
    """Immutable JSON records in SQLite; writes are transactional and parameterized."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "lab.sqlite3"
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS records "
                "(kind TEXT NOT NULL, id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind: str, record: dict):
        with self.connection() as db:
            db.execute(
                "INSERT INTO records VALUES (?, ?, ?)", (kind, record["id"], canonical_json(record))
            )
        return record

    def get(self, kind: str, record_id: str) -> dict:
        with self.connection() as db:
            row = db.execute(
                "SELECT payload FROM records WHERE kind=? AND id=?", (kind, record_id)
            ).fetchone()
        if row is None:
            raise KeyError(f"{kind.capitalize()} not found")
        return json.loads(row[0])

    def list(self, kind: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT payload FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
