import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional


DB_PATH = os.getenv("TV2_DB_PATH", str(Path(__file__).resolve().parents[1] / "tv2.db"))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS pull_requests (
                pr_id TEXT PRIMARY KEY, author_id TEXT NOT NULL, repository TEXT NOT NULL,
                changed_files TEXT NOT NULL, quality_score REAL, risk_score REAL,
                required_reviewers INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS reviewers (
                reviewer_id TEXT PRIMARY KEY, expertise TEXT NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 1, current_load INTEGER NOT NULL DEFAULT 0,
                max_load INTEGER NOT NULL DEFAULT 3
            );
            CREATE TABLE IF NOT EXISTS assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_id TEXT NOT NULL REFERENCES pull_requests(pr_id),
                reviewer_id TEXT NOT NULL REFERENCES reviewers(reviewer_id),
                status TEXT NOT NULL, score REAL NOT NULL, matched_files TEXT NOT NULL,
                reasons TEXT NOT NULL
            );
            """
        )
        schema = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='assignments'"
        ).fetchone()["sql"]
        if "UNIQUE(pr_id, reviewer_id, status)" in schema:
            db.executescript(
                """
                BEGIN;
                ALTER TABLE assignments RENAME TO assignments_old;
                CREATE TABLE assignments (
                    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pr_id TEXT NOT NULL REFERENCES pull_requests(pr_id),
                    reviewer_id TEXT NOT NULL REFERENCES reviewers(reviewer_id),
                    status TEXT NOT NULL, score REAL NOT NULL, matched_files TEXT NOT NULL,
                    reasons TEXT NOT NULL
                );
                INSERT INTO assignments
                    (assignment_id, pr_id, reviewer_id, status, score, matched_files, reasons)
                SELECT assignment_id, pr_id, reviewer_id, status, score, matched_files, reasons
                FROM assignments_old;
                DROP TABLE assignments_old;
                COMMIT;
                """
            )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS one_active_reviewer_per_pr "
            "ON assignments(pr_id, reviewer_id) WHERE status='assigned'"
        )


def row_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    return dict(row) if row else None


def decode(row: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(row)
    for key in ("changed_files", "expertise", "matched_files", "reasons"):
        if key in result and isinstance(result[key], str):
            result[key] = json.loads(result[key])
    return result


def json_value(value: Iterable[str]) -> str:
    return json.dumps(list(value), ensure_ascii=True)

