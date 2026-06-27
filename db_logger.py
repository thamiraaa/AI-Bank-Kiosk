"""
db_logger.py — SQLite Transaction Audit Logger

Stores ONLY audit fields — no personal customer data:
  transaction_id, timestamp, doc_type, form_type, language, status

Schema is auto-created on first run.
"""

import sqlite3
import uuid
import os
from datetime import datetime

import config


def _get_connection() -> sqlite3.Connection:
    """Return a connection to the kiosk database."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Create the transactions table if it doesn't already exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT    NOT NULL,
                timestamp      TEXT    NOT NULL,
                doc_type       TEXT,
                form_type      TEXT,
                language       TEXT,
                status         TEXT,
                ocr_confidence REAL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def log_transaction(
    doc_type: str = "",
    form_type: str = "",
    language: str = "en",
    status: str = "completed",
    ocr_confidence: float = 0.0,
) -> str:
    """
    Write an audit record and return the generated transaction_id.

    Args:
        doc_type       : e.g. 'Aadhaar Card', 'Bank Passbook', 'PAN Card'
        form_type      : e.g. 'Cash Deposit', 'Account Opening'
        language       : language code selected by user, e.g. 'ta'
        status         : 'completed' | 'cancelled' | 'error'
        ocr_confidence : mean OCR confidence score (0-100)

    Returns:
        The UUID transaction_id string.
    """
    transaction_id = str(uuid.uuid4()).upper()[:12]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO transactions
                (transaction_id, timestamp, doc_type, form_type, language, status, ocr_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (transaction_id, timestamp, doc_type, form_type, language, status, ocr_confidence))
        conn.commit()
    finally:
        conn.close()

    print(f"[DB] Transaction logged: {transaction_id} | {form_type} | {status}")
    return transaction_id


def get_recent_logs(limit: int = 50) -> list:
    """Return the most recent *limit* transaction audit records as dicts."""
    conn = _get_connection()
    try:
        cursor = conn.execute("""
            SELECT * FROM transactions
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
    return rows


# Auto-initialize when the module is imported
try:
    initialize_db()
except Exception as exc:
    print(f"[DB] Warning: could not initialize database: {exc}")
