import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "subscriptions.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        TEXT NOT NULL,
                discord_channel_id TEXT NOT NULL,
                yt_handle       TEXT NOT NULL,
                yt_channel_id   TEXT NOT NULL,
                added_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, yt_channel_id)
            );

            CREATE TABLE IF NOT EXISTS seen_videos (
                video_id    TEXT PRIMARY KEY,
                channel_id  TEXT NOT NULL,
                seen_at     DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)


def add_subscription(guild_id: str, discord_channel_id: str, yt_handle: str, yt_channel_id: str) -> bool:
    """Returns True if newly added, False if already existed."""
    with get_conn() as conn:
        try:
            conn.execute(
                """INSERT INTO subscriptions (guild_id, discord_channel_id, yt_handle, yt_channel_id)
                   VALUES (?, ?, ?, ?)""",
                (guild_id, discord_channel_id, yt_handle, yt_channel_id),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def remove_subscription(guild_id: str, yt_handle: str) -> bool:
    """Returns True if a row was deleted."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM subscriptions WHERE guild_id = ? AND LOWER(yt_handle) = LOWER(?)",
            (guild_id, yt_handle),
        )
        return cur.rowcount > 0


def get_subscriptions(guild_id: str = None):
    """Return all subscriptions, or just for one guild."""
    with get_conn() as conn:
        if guild_id:
            return conn.execute(
                "SELECT * FROM subscriptions WHERE guild_id = ?", (guild_id,)
            ).fetchall()
        return conn.execute("SELECT * FROM subscriptions").fetchall()


def is_seen(video_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        return row is not None


def mark_seen(video_id: str, channel_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_videos (video_id, channel_id) VALUES (?, ?)",
            (video_id, channel_id),
        )
