"""DuckDB persistence helpers for transformed YouTube data.

The schema follows a small star-style layout:
  * dim_channels        - one row per channel (name kept up to date)
  * fact_channel_stats  - daily snapshots of channel-level counters
  * fact_video_stats    - daily snapshots per video

All writes use INSERT OR REPLACE keyed on the primary key, so re-running
the pipeline on the same day is idempotent (the snapshot is overwritten).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb


# Resolved relative to this file, so the path stays valid regardless of
# the current working directory when the pipeline is invoked.
DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "yt_social_listening.duckdb"
)


@contextmanager
def _connection(db_path: str | Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a DuckDB connection wrapped in a transaction.

    Commits on success, rolls back on any error, and always closes the
    connection so no file handles leak.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)  # ensure the data dir exists
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
    # One statement per table; CREATE TABLE IF NOT EXISTS makes this safe
    # to call on every pipeline run.
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
    # Project records into row tuples up front so the executemany call below
    # stays a simple ?-placeholder statement.
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
        return  # nothing to write; skip the (wasted) transaction

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
