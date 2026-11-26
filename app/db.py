import os
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
 salt BLOB NOT NULL, digest BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token TEXT PRIMARY KEY, owner INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
 key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
 id INTEGER PRIMARY KEY, owner INTEGER NOT NULL REFERENCES users(id),
 day TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('in','out')),
 category TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount BETWEEN 1 AND 999999999999),
 note TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
 request_id TEXT NOT NULL, UNIQUE(owner, request_id)
);
CREATE INDEX IF NOT EXISTS entries_month ON entries(owner, day DESC, id DESC);
CREATE TABLE IF NOT EXISTS budgets (
 owner INTEGER REFERENCES users(id), month TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount >= 0),
 PRIMARY KEY(owner, month)
);
"""

def search_text(value):
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(c for c in normalized if not unicodedata.combining(c))

@contextmanager
def connection():
    path = Path(os.getenv("LEDGER_DB", "data/ledger.sqlite3"))
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.create_function("search_text", 1, search_text, deterministic=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
