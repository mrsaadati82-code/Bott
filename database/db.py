# ============================================================
# database/db.py - Database abstraction layer
# ============================================================
# Provides a thin wrapper around sqlite3 that mimics the
# minimum surface we need so we can later swap to PostgreSQL
# by changing DB_BACKEND in config.py.
#
# Usage:
#   from database.db import db
#   db.execute("INSERT INTO users(...) VALUES (?, ?)", (1, "ali"))
#   row  = db.fetchone("SELECT * FROM users WHERE id=?", (1,))
#   rows = db.fetchall("SELECT * FROM users")
# ============================================================

import sqlite3
import threading
from contextlib import contextmanager

from config import DB_BACKEND, DB_PATH, DB_DSN


class Database:
    """
    Thread-safe minimal DB wrapper.
    All access goes through the singleton `db` instance below.
    """

    def __init__(self):
        self._backend = DB_BACKEND
        self._lock = threading.RLock()
        self._conn = None
        self._connect()

    # --------------------------------------------------------
    # Connection management
    # --------------------------------------------------------
    def _connect(self):
        if self._backend == "sqlite":
            self._conn = sqlite3.connect(
                DB_PATH,
                check_same_thread=False,
                isolation_level=None,   # autocommit; we use explicit transactions
                timeout=30,
            )
            self._conn.row_factory = sqlite3.Row
            # Pragmas for safety + speed on Pydroid/Termux
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        elif self._backend == "postgres":
            # Lazy import so SQLite-only installs don't need psycopg2.
            import psycopg2
            import psycopg2.extras
            self._conn = psycopg2.connect(DB_DSN)
            self._conn.autocommit = True
        else:
            raise RuntimeError("Unknown DB_BACKEND: {}".format(self._backend))

    # --------------------------------------------------------
    # Placeholder helper
    # --------------------------------------------------------
    @property
    def ph(self) -> str:
        """Returns the correct parameter placeholder for the active backend."""
        return "?" if self._backend == "sqlite" else "%s"

    def q(self, sql: str) -> str:
        """
        Convert '?' placeholders to backend's placeholder.
        Lets us write portable SQL using '?'.
        """
        if self._backend == "sqlite":
            return sql
        return sql.replace("?", "%s")

    # --------------------------------------------------------
    # Core execute helpers
    # --------------------------------------------------------
    def execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(self.q(sql), params)
            return cur

    def executemany(self, sql: str, seq):
        with self._lock:
            cur = self._conn.cursor()
            cur.executemany(self.q(sql), seq)
            return cur

    def executescript(self, sql: str):
        """Run a multi-statement script (SQLite only)."""
        with self._lock:
            if self._backend == "sqlite":
                self._conn.executescript(sql)
            else:
                cur = self._conn.cursor()
                cur.execute(sql)

    def fetchone(self, sql: str, params: tuple = ()):
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row is not None and self._backend == "sqlite" else row

    def fetchall(self, sql: str, params: tuple = ()):
        cur = self.execute(sql, params)
        rows = cur.fetchall()
        if self._backend == "sqlite":
            return [dict(r) for r in rows]
        return rows

    def insert(self, sql: str, params: tuple = ()) -> int:
        """Run an INSERT and return the new row id (SQLite lastrowid)."""
        cur = self.execute(sql, params)
        return cur.lastrowid if self._backend == "sqlite" else None

    @contextmanager
    def transaction(self):
        """
        Context manager for an explicit transaction.
        Usage:
            with db.transaction():
                db.execute(...)
                db.execute(...)
        """
        with self._lock:
            try:
                self._conn.execute("BEGIN") if self._backend == "sqlite" else None
                yield
                self._conn.execute("COMMIT") if self._backend == "sqlite" else None
            except Exception:
                if self._backend == "sqlite":
                    self._conn.execute("ROLLBACK")
                raise

    def close(self):
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


# Singleton instance used everywhere.
db = Database()
