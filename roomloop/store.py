import sqlite3

DB_PATH = "roomloop.db"


def get_conn(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rooms (
               id INTEGER PRIMARY KEY,
               name TEXT NOT NULL,
               capacity INTEGER NOT NULL DEFAULT 4)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS bookings (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               room_id INTEGER NOT NULL REFERENCES rooms(id),
               user_name TEXT NOT NULL,
               series_id TEXT,
               start_local TEXT NOT NULL,
               end_local TEXT NOT NULL,
               start_utc TEXT NOT NULL,
               end_utc TEXT NOT NULL,
               timezone TEXT NOT NULL,
               status TEXT NOT NULL DEFAULT 'active',
               created_at TEXT NOT NULL)"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_b_room ON "
        "bookings(room_id, status, start_utc, end_utc)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_b_series ON "
        "bookings(series_id, status)"
    )
    conn.commit()
