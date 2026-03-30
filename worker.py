"""
Non-interactive worker for background download/upload tasks.
Called by ytm.py — not intended to be run directly by users.
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from channel_extractor import load_channel_info, sanitize_username, scan_and_save_channel
from download_scanner import (
    scan_existing_downloads,
    create_download_queue,
    is_all_downloaded,
    check_video_uploaded,
    check_video_exists,
)
from video_downloader import download_queue_parallel, resume_download_if_needed
from telegram_uploader import TelegramUploader, load_telegram_config


def run_download(username: str, threads: int = 3) -> None:
    """Run download task for a channel (non-interactive)."""
    clean_username = sanitize_username(username)

    # Load channel info
    channel_data = load_channel_info(clean_username)
    if not channel_data:
        # Try scanning first
        print(f"📡 No channel info found for {clean_username}. Scanning...")
        result = scan_and_save_channel(username, verbose=True)
        if not result:
            print("❌ Failed to extract channel information.")
            sys.exit(1)
        clean_username, channel_data = result

    print(f"✅ Loaded channel info for: @{clean_username}")

    # Scan existing downloads
    print("\n🔍 Scanning for already downloaded videos...")
    missing_videos = scan_existing_downloads(clean_username, channel_data, verbose=True)

    if is_all_downloaded(missing_videos):
        print("\n✅ All videos are already downloaded!")
        return

    queue = create_download_queue(missing_videos)
    print(f"\n📥 Starting download of {len(queue)} videos with {threads} threads...")

    result = resume_download_if_needed(queue, clean_username, max_threads=threads, verbose=True)

    print("\n" + "=" * 60)
    print("🎉 DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"✅ Downloaded: {result.get('completed', 0)}")
    print(f"❌ Failed: {result.get('failed', 0)}")
    print(f"⏱️  Time: {result.get('elapsed_time', 0):.2f}s")
    print("=" * 60)


def run_upload(username: str, upload_all: bool = False) -> None:
    """Run upload task for a channel (non-interactive)."""
    clean_username = sanitize_username(username)

    # Load channel info
    channel_data = load_channel_info(clean_username)
    if not channel_data:
        print(f"❌ No channel info found for {clean_username}.")
        print("   Run a download first or scan the channel.")
        sys.exit(1)

    print(f"✅ Loaded channel info for: @{clean_username}")

    # Load Telegram config
    config = load_telegram_config()
    if not config.get('bot_token') or not config.get('channel_id'):
        print("❌ Telegram not configured! Edit telegram_config.json.")
        sys.exit(1)

    uploader = TelegramUploader(config)

    print("Testing Telegram connection...")
    if not uploader.check_connection():
        print("❌ Cannot connect to Telegram API server.")
        sys.exit(1)

    import time
    
    polling_delays = [60, 120, 240]
    delay_idx = 0

    print(f"\n🔄 Starting upload polling (checks at {', '.join(map(str, polling_delays))}s intervals)...")
    
    while True:
        # Build upload queue by checking local files
        upload_queue = []
        for video_type in ['videos', 'shorts', 'streams']:
            videos = channel_data.get(video_type, [])
            for video in videos:
                video_id = video.get('id')
                if not video_id:
                    continue
                # Check if it was successfully downloaded
                if not check_video_exists(video_id, clean_username, video_type):
                    continue
                # Check if it was already uploaded
                if not upload_all:
                    if check_video_uploaded(video_id, clean_username):
                        continue
                        
                upload_queue.append({
                    'id': video_id,
                    'title': video.get('title', 'Unknown'),
                    'url': video.get('url', ''),
                    'type': video_type
                })

        if upload_queue:
            print(f"\n📦 Found {len(upload_queue)} new videos to upload...")
            result = uploader.upload_queue(upload_queue, clean_username, verbose=True)

            print("\n" + "=" * 60)
            print("✅ BATCH UPLOAD COMPLETE")
            print("=" * 60)
            print(f"✅ Uploaded: {result['uploaded']}")
            print(f"❌ Failed: {result['failed']}")
            print("=" * 60)
            
            # Reset polling delay on successful find
            delay_idx = 0
        else:
            if delay_idx >= len(polling_delays):
                print("\n🛑 No new videos found after final check. Stopping upload process.")
                break

        # Get current delay and sleep
        current_delay = polling_delays[delay_idx]

        if not upload_queue:
            print(f"⏳ No new videos found. Waiting {current_delay}s before next check (Attempt {delay_idx + 1}/{len(polling_delays)})...")
            delay_idx += 1
        else:
            print(f"⏳ Waiting {current_delay}s before next check...")

        time.sleep(current_delay)


def main():
    parser = argparse.ArgumentParser(description="Background worker for download/upload tasks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Download command
    dl_parser = subparsers.add_parser("download", help="Download videos")
    dl_parser.add_argument("username", help="YouTube channel username")
    dl_parser.add_argument("--threads", type=int, default=3, help="Number of threads (default: 3)")

    # Upload command
    ul_parser = subparsers.add_parser("upload", help="Upload videos to Telegram")
    ul_parser.add_argument("username", help="YouTube channel username")
    ul_parser.add_argument("--all", dest="upload_all", action="store_true", help="Upload all (including previously uploaded)")

    args = parser.parse_args()

    if args.command == "download":
        run_download(args.username, args.threads)
    elif args.command == "upload":
        run_upload(args.username, args.upload_all)


if __name__ == "__main__":
    main()
