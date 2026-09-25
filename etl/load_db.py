"""DuckDB persistence helpers for transformed YouTube data."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "yt_social_listening.duckdb"
)


@contextmanager
def _connection(db_path: str | Path) -> Iterator[duckdb.DuckDBPyConnection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path))
    try:
        connection.execute("BEGIN TRANSACTION")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
    finally:
        connection.close()


def init_db(db_path: str | Path = DB_PATH) -> None:
    """Create the database and all required tables if they do not exist."""
    statements = (
        """
        CREATE TABLE IF NOT EXISTS dim_channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_channel_stats (
            channel_id TEXT,
            date TEXT,
            subscriber_count INTEGER,
            view_count INTEGER,
            video_count INTEGER,
            PRIMARY KEY (channel_id, date)
        )
        """,
        """
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
        )
        """,
    )

    with _connection(db_path) as connection:
        for statement in statements:
            connection.execute(statement)


def upsert_channel(
    db_path: str | Path,
    channel_id: str,
    channel_name: str,
) -> None:
    """Insert a channel or replace its row when the primary key exists."""
    with _connection(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO dim_channels (channel_id, channel_name)
            VALUES (?, ?)
            """,
            (channel_id, channel_name),
        )


def upsert_channel_stats(
    db_path: str | Path, stats_dict: dict[str, Any]
) -> None:
    """Insert or replace a channel statistics snapshot by primary key."""
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
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                stats_dict["channel_id"],
                stats_dict["date"],
                stats_dict["subscriber_count"],
                stats_dict["view_count"],
                stats_dict["video_count"],
            ),
        )


def upsert_video_stats(
    db_path: str | Path, video_stats_list: list[dict[str, Any]]
) -> None:
    """Insert or replace multiple video statistics snapshots by primary key."""
    rows = [
        (
            video["video_id"],
            video["channel_id"],
            video["date"],
            video["title"],
            video["published_at"],
            video["view_count"],
            video["like_count"],
            video["comment_count"],
        )
        for video in video_stats_list
    ]

    if not rows:
        return

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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
