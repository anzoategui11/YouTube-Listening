"""Helpers for retrieving channel and video data from the YouTube Data API v3."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import Error as GoogleClientError, HttpError


class YouTubeAPIError(RuntimeError):
    """Raised when a YouTube Data API request fails."""


class YouTubeQuotaError(YouTubeAPIError):
    """Raised when the YouTube API reports a quota or rate-limit failure."""


_QUOTA_REASONS = {
    "dailyLimitExceeded",
    "quotaExceeded",
    "rateLimitExceeded",
    "userRateLimitExceeded",
}


def _get_youtube_service() -> Any:
    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise YouTubeAPIError(
            "YOUTUBE_API_KEY is not set. Add it to the environment or .env file."
        )

    try:
        return build(
            "youtube",
            "v3",
            developerKey=api_key,
            cache_discovery=False,
        )
    except GoogleClientError as exc:
        raise YouTubeAPIError("Unable to initialize the YouTube API client.") from exc


def _execute(request: Any, operation: str) -> dict[str, Any]:
    try:
        return request.execute()
    except HttpError as exc:
        status = getattr(exc.resp, "status", None)
        message = getattr(exc, "error_details", None) or str(exc)
        reasons: set[str] = set()

        try:
            payload = json.loads(exc.content)
            error_payload = payload.get("error", {})
            message = error_payload.get("message", message)
            reasons = {
                detail["reason"]
                for detail in error_payload.get("errors", [])
                if detail.get("reason")
            }
        except (AttributeError, TypeError, ValueError):
            pass

        normalized_message = str(message).lower()
        if (
            status == 429
            or reasons.intersection(_QUOTA_REASONS)
            or "quota" in normalized_message
            or "rate limit" in normalized_message
            or "rate-limit" in normalized_message
        ):
            raise YouTubeQuotaError(
                f"YouTube API quota or rate limit exceeded while {operation}: "
                f"{message}"
            ) from exc

        status_text = f" (HTTP {status})" if status is not None else ""
        raise YouTubeAPIError(
            f"YouTube API request failed while {operation}{status_text}: {message}"
        ) from exc
    except GoogleClientError as exc:
        raise YouTubeAPIError(f"YouTube API request failed while {operation}: {exc}") from exc


def _validate_channel_id(channel_id: str) -> str:
    if not isinstance(channel_id, str) or not channel_id.strip():
        raise ValueError("channel_id must be a non-empty string.")
    return channel_id.strip()


def _validate_max_results(max_results: int) -> int:
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise TypeError("max_results must be an integer.")
    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50.")
    return max_results


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_channel_stats(channel_id: str) -> dict[str, Any]:
    """Return the name and aggregate statistics for a YouTube channel.

    Args:
        channel_id: The YouTube channel ID to query.

    Raises:
        ValueError: If ``channel_id`` is empty.
        YouTubeQuotaError: If the API quota or rate limit is exceeded.
        YouTubeAPIError: If the API key is missing or the request fails.
    """
    channel_id = _validate_channel_id(channel_id)
    youtube = _get_youtube_service()

    response = _execute(
        youtube.channels().list(
            part="snippet,statistics",
            id=channel_id,
            maxResults=1,
        ),
        operation="retrieving channel statistics",
    )
    items = response.get("items", [])
    if not items:
        raise YouTubeAPIError(f"YouTube channel not found: {channel_id}")

    channel = items[0]
    snippet = channel.get("snippet", {})
    statistics = channel.get("statistics", {})

    return {
        "channel_name": snippet.get("title", ""),
        "subscriber_count": _as_int(statistics.get("subscriberCount")),
        "view_count": _as_int(statistics.get("viewCount")),
        "video_count": _as_int(statistics.get("videoCount")),
    }


def get_recent_videos(channel_id: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Return a channel's most recently published videos and their statistics.

    Search results determine the recency order; the returned list preserves that
    order even if the videos endpoint returns items in a different order.

    Args:
        channel_id: The YouTube channel ID to query.
        max_results: Number of videos to return, from 1 through 50.

    Raises:
        ValueError: If the channel ID or result count is invalid.
        YouTubeQuotaError: If the API quota or rate limit is exceeded.
        YouTubeAPIError: If the API key is missing or either request fails.
    """
    channel_id = _validate_channel_id(channel_id)
    max_results = _validate_max_results(max_results)
    youtube = _get_youtube_service()

    search_response = _execute(
        youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=max_results,
            order="date",
            type="video",
        ),
        operation="searching for recent channel videos",
    )
    video_ids = [
        item["id"]["videoId"]
        for item in search_response.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return []

    videos_response = _execute(
        youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids),
            maxResults=len(video_ids),
        ),
        operation="retrieving recent video statistics",
    )
    videos_by_id = {video["id"]: video for video in videos_response.get("items", [])}

    recent_videos: list[dict[str, Any]] = []
    for video_id in video_ids:
        video = videos_by_id.get(video_id)
        if video is None:
            continue

        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        recent_videos.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt"),
                "view_count": _as_int(statistics.get("viewCount")),
                "like_count": _as_int(statistics.get("likeCount")),
                "comment_count": _as_int(statistics.get("commentCount")),
            }
        )

    return recent_videos
