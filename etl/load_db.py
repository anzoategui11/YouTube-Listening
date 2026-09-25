"""SQLite persistence helpers for transformed YouTube data."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "yt_social_listening.db"


@contextmanager
def _connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db(db_path: str | Path = DB_PATH) -> None:
    """Create the database and all required tables if they do not exist."""
    with _connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS dim_channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT
            );

            CREATE TABLE IF NOT EXISTS fact_channel_stats (
                channel_id TEXT,
                date TEXT,
                subscriber_count INTEGER,
                view_count INTEGER,
                video_count INTEGER,
                PRIMARY KEY (channel_id, date)
            );

            CREATE TABLE IF NOT EXISTS fact_video_stats (
                video_id TEXT,
                channel_id TEXT,
                date TEXT,
                title TEXT,
                published_at TEXT,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                PRIMARY KEY (video_id, date)
            );
            """
        )


def upsert_channel(
    db_path: str | Path,
    channel_id: str,
    channel_name: str,
) -> None:
    """Insert a channel or update its name when the channel already exists."""
    with _connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO dim_channels (channel_id, channel_name)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_name = excluded.channel_name
            """,
            (channel_id, channel_name),
        )


def upsert_channel_stats(
    db_path: str | Path, stats_dict: dict[str, Any]
) -> None:
    """Insert or replace a channel statistics snapshot."""
    with _connection(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO fact_channel_stats (
                channel_id,
                date,
                subscriber_count,
                view_count,
                video_count
            )
            VALUES (
                :channel_id,
                :date,
                :subscriber_count,
                :view_count,
                :video_count
            )
            """,
            stats_dict,
        )


def upsert_video_stats(
    db_path: str | Path, video_stats_list: list[dict[str, Any]]
) -> None:
    """Insert or replace multiple video statistics snapshots."""
    with _connection(db_path) as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO fact_video_stats (
                video_id,
                channel_id,
                date,
                title,
                published_at,
                view_count,
                like_count,
                comment_count
            )
            VALUES (
                :video_id,
                :channel_id,
                :date,
                :title,
                :published_at,
                :view_count,
                :like_count,
                :comment_count
            )
            """,
            video_stats_list,
        )
