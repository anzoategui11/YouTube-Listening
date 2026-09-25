"""Transform YouTube API responses into flat records for storage."""

from datetime import date
from typing import Any


def transform_channel_stats(
    channel_id: str, channel_stats_dict: dict[str, Any]
) -> dict[str, Any]:
    """Flatten a channel statistics dictionary for persistence."""
    return {
        "channel_id": channel_id,
        "date": date.today().isoformat(),
        "subscriber_count": channel_stats_dict["subscriber_count"],
        "view_count": channel_stats_dict["view_count"],
        "video_count": channel_stats_dict["video_count"],
    }


def transform_video_stats(
    channel_id: str, videos_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Flatten recent video dictionaries for persistence."""
    snapshot_date = date.today().isoformat()
    return [
        {
            "video_id": video["video_id"],
            "channel_id": channel_id,
            "date": snapshot_date,
            "title": video["title"],
            "published_at": video["published_at"],
            "view_count": video["view_count"],
            "like_count": video["like_count"],
            "comment_count": video["comment_count"],
        }
        for video in videos_list
    ]
