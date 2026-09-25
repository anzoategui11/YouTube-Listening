"""Quick manual test for the YouTube API client."""

from pprint import pprint

from config import CHANNEL_IDS
from etl.youtube_client import get_channel_stats, get_recent_videos


def main() -> None:
    if not CHANNEL_IDS:
        raise SystemExit("No channel IDs are configured in config.py.")

    channel_id = CHANNEL_IDS[0]
    print(f"Channel ID: {channel_id}")

    print("\nChannel statistics:")
    pprint(get_channel_stats(channel_id), sort_dicts=False)

    print("\nRecent videos:")
    pprint(get_recent_videos(channel_id), sort_dicts=False)


if __name__ == "__main__":
    main()
