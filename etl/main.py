"""Run the YouTube ETL pipeline for all configured channels."""

import logging
from typing import Any

from config import CHANNEL_IDS
from etl.load_db import (
    DB_PATH,
    init_db,
    upsert_channel,
    upsert_channel_stats,
    upsert_video_stats,
)
from etl.transform import transform_channel_stats, transform_video_stats
from etl.youtube_client import get_channel_stats, get_recent_videos


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_channel(channel_id: str) -> int:
    """Fetch, transform, and store data for one channel."""
    logger.info("Processing channel %s", channel_id)

    channel_stats: dict[str, Any] = get_channel_stats(channel_id)
    recent_videos = get_recent_videos(channel_id)

    channel_stats_record = transform_channel_stats(channel_id, channel_stats)
    video_stats_records = transform_video_stats(channel_id, recent_videos)

    upsert_channel(DB_PATH, channel_id, channel_stats["channel_name"])
    upsert_channel_stats(DB_PATH, channel_stats_record)
    upsert_video_stats(DB_PATH, video_stats_records)

    logger.info(
        "Success for channel %s: stored 1 channel snapshot and %d video records",
        channel_id,
        len(video_stats_records),
    )
    return len(video_stats_records)


def main() -> None:
    """Initialize the database and process every configured channel."""
    init_db(DB_PATH)
    logger.info("Initialized database at %s", DB_PATH)

    if not CHANNEL_IDS:
        logger.warning("No channel IDs are configured in config.py.")
        return

    for channel_id in CHANNEL_IDS:
        try:
            process_channel(channel_id)
        except Exception as exc:
            logger.exception("Failed for channel %s: %s", channel_id, exc)


if __name__ == "__main__":
    main()
