"""End-to-end test for fetching, transforming, and storing YouTube data."""

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


def main() -> None:
    if not CHANNEL_IDS:
        raise SystemExit("No channel IDs are configured in config.py.")

    channel_id = CHANNEL_IDS[0]

    init_db(DB_PATH)

    channel_stats = get_channel_stats(channel_id)
    recent_videos = get_recent_videos(channel_id)

    channel_stats_record = transform_channel_stats(channel_id, channel_stats)
    video_stats_records = transform_video_stats(channel_id, recent_videos)

    upsert_channel(DB_PATH, channel_id, channel_stats["channel_name"])
    upsert_channel_stats(DB_PATH, channel_stats_record)
    upsert_video_stats(DB_PATH, video_stats_records)

    print(
        f"Pipeline completed successfully for {channel_id}: "
        f"stored 1 channel snapshot and {len(video_stats_records)} video records."
    )


if __name__ == "__main__":
    main()
