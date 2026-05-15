"""SOMA Store — SQLite persistence for the triple graph.

Every triple (S, P, O) gets persisted with status (soup/code/ont),
event_id, and timestamp. On boot, all triples reload into Prolog.
OWL = schema definition. SQLite = data store. Prolog = ephemeral cache.
"""
import os
import sqlite3
import time
import logging
import traceback

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get("SOMA_DB_PATH", "/tmp/soma_data/soma.db")
_conn = None


def _ensure_db():
    global _conn
    if _conn is not None:
        return _conn
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS soma_triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            status TEXT DEFAULT 'soup',
            event_id TEXT,
            created_at REAL
        )
    """)
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_subj ON soma_triples(subject)")
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_pred ON soma_triples(predicate)")
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON soma_triples(status)")
    _conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_spo
        ON soma_triples(subject, predicate, object)
    """)
    _conn.commit()
    logger.info("SOMA store initialized at %s", _DB_PATH)
    return _conn


def save_triple(subject: str, predicate: str, obj: str,
                event_id: str = "", status: str = "soup") -> bool:
    conn = _ensure_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO soma_triples (subject, predicate, object, status, event_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (subject, predicate, obj, status, event_id, time.time())
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error("save_triple failed: %s\n%s", e, traceback.format_exc())
        return False


def save_triples_batch(triples: list, event_id: str = "") -> int:
    conn = _ensure_db()
    count = 0
    for s, p, o in triples:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO soma_triples (subject, predicate, object, status, event_id, created_at) VALUES (?, ?, ?, 'soup', ?, ?)",
                (s, p, o, event_id, time.time())
            )
            count += 1
        except sqlite3.Error as e:
            logger.debug("batch insert skip: %s\n%s", e, traceback.format_exc())
    conn.commit()
    return count


def load_all_triples() -> list:
    conn = _ensure_db()
    cursor = conn.execute("SELECT subject, predicate, object FROM soma_triples")
    return cursor.fetchall()


def update_status(subject: str, new_status: str):
    conn = _ensure_db()
    conn.execute(
        "UPDATE soma_triples SET status = ? WHERE subject = ?",
        (new_status, subject)
    )
    conn.commit()


def get_status(subject: str) -> str:
    conn = _ensure_db()
    cursor = conn.execute(
        "SELECT status FROM soma_triples WHERE subject = ? LIMIT 1",
        (subject,)
    )
    row = cursor.fetchone()
    return row[0] if row else "unknown"


def triple_count() -> int:
    conn = _ensure_db()
    cursor = conn.execute("SELECT COUNT(*) FROM soma_triples")
    return cursor.fetchone()[0]


def get_triples_for_subject(subject: str) -> list:
    conn = _ensure_db()
    cursor = conn.execute(
        "SELECT predicate, object FROM soma_triples WHERE subject = ?",
        (subject,)
    )
    return cursor.fetchall()
