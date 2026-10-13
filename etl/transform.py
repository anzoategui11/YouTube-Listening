"""Transform YouTube API responses into flat records for storage.

The functions here turn the dict-shaped API payloads from ``youtube_client``
into flat per-row dicts that map 1:1 onto the columns of the DuckDB tables
defined in ``load_db``.
"""

from datetime import date, datetime
from typing import Any


def transform_channel_stats(
    channel_id: str, channel_stats_dict: dict[str, Any]
) -> dict[str, Any]:
    """Flatten a channel statistics dictionary for persistence.

    A snapshot row: one record per (channel, date), tagged with the date
    the stats were fetched.
    """
    return {
        "channel_id": channel_id,
        "date": date.today().isoformat(),  # snapshot date (YYYY-MM-DD)
        "subscriber_count": channel_stats_dict["subscriber_count"],
        "view_count": channel_stats_dict["view_count"],
        "video_count": channel_stats_dict["video_count"],
    }


def transform_video_stats(
    channel_id: str, videos_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Flatten recent video dictionaries for persistence.

    Produces one snapshot row per video, all sharing today's snapshot
    date so repeated runs create a time series per video.
    """
    snapshot_date = date.today().isoformat()
    return [
        {
            "video_id": video["video_id"],
            "channel_id": channel_id,
            "date": snapshot_date,
            "title": video["title"],
            # API timestamps end in "Z" (UTC). Strip it before parsing so
            # this stores a naive datetime, formatted to second precision.
            "published_at": datetime.fromisoformat(
                video["published_at"].removesuffix("Z")
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "view_count": video["view_count"],
            "like_count": video["like_count"],
            "comment_count": video["comment_count"],
        }
        for video in videos_list
    ]
