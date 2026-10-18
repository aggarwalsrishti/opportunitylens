import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("opportunitylens.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT,
                snippet TEXT,
                score INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'Interested',
                saved_at TEXT NOT NULL
            )
        """)

def save_opportunity(title, url, snippet, score, reason):
    with connect() as conn:
        conn.execute("""
            INSERT INTO saved_opportunities(title, url, snippet, score, reason, status, saved_at)
            VALUES (?, ?, ?, ?, ?, 'Interested', ?)
        """, (title, url, snippet, int(score), reason, datetime.now().strftime("%Y-%m-%d %H:%M")))

def get_saved():
    with connect() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM saved_opportunities ORDER BY id DESC"
        ).fetchall()]

def update_status(item_id, status):
    with connect() as conn:
        conn.execute("UPDATE saved_opportunities SET status=? WHERE id=?", (status, item_id))

def remove_saved(item_id):
    with connect() as conn:
        conn.execute("DELETE FROM saved_opportunities WHERE id=?", (item_id,))
