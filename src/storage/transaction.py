import sqlite3
from contextlib import contextmanager
from typing import Generator

@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """Execute within an atomic SQLite transaction using BEGIN IMMEDIATE."""
    conn.execute("BEGIN IMMEDIATE;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

