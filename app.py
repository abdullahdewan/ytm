"""
Main application for YouTube Channel Video Downloader.
Handles user input and orchestrates the workflow:
1. Extract channel info
2. Scan existing downloads
3. Download missing videos with multi-threading
4. Upload to Telegram (optional)
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from channel_extractor import (
    scan_and_save_channel,
    load_channel_info,
    sanitize_username
)
from download_scanner import (
    scan_existing_downloads,
    create_download_queue,
    is_all_downloaded,
    check_video_uploaded,
    log_uploaded_video
)
from video_downloader import (
    download_queue_parallel,
    resume_download_if_needed
)
from telegram_uploader import (
    TelegramUploader,
    load_telegram_config
)


def print_banner():
    """Print application banner."""
    print("\n" + "=" * 60)
    print("🎬 YOUTUBE CHANNEL VIDEO DOWNLOADER")
    print("=" * 60)
    print()


def get_user_input() -> str:
    """
    Get YouTube channel URL or username from user.
    
    Returns:
        Channel URL or username string
    """
    print("Enter YouTube Channel URL or Username (with or without @)")
    print("Examples:")
    print("  - https://www.youtube.com/@ElainaAly")
    print("  - @ElainaAly")
    print("  - ElainaAly")
    print()
    
    user_input = input("➡️  Your input: ").strip()
    
    if not user_input:
        print("❌ Invalid input. Please try again.")
        return get_user_input()
    
    return user_input


def check_info_file_exists(username: str) -> bool:
    """
    Check if channel info file already exists.
    
    Args:
        username: Channel username (with or without @)
        
    Returns:
        True if info file exists, False otherwise
    """
    clean_username = sanitize_username(username)
    channels_info_dir = Path(__file__).parent / 'channels_info'
    info_file = channels_info_dir / f"{clean_username}.json"
    
    return info_file.exists()


def ask_rescan_or_download(username: str) -> str:
    """
    Ask user whether to rescan channel info or proceed to download.
    
    Args:
        username: Channel username
        
    Returns:
        User choice: 'rescan', 'download', or 'upload'
    """
    print(f"\n✅ Channel info found for: @{username}")
    print("\nWhat would you like to do?")
    print("  [R] Rescan channel info (update JSON file)")
    print("  [D] Download videos")
    print("  [U] Upload to Telegram")
    print("  [Q] Quit")
    print()
    
    while True:
        choice = input("➡️  Your choice (R/D/U/Q): ").strip().lower()
        
        if choice in ['r', 'rescan']:
            return 'rescan'
        elif choice in ['d', 'download']:
            return 'download'
        elif choice in ['u', 'upload']:
            return 'upload'
        elif choice in ['q', 'quit', 'exit']:
            return 'quit'
        else:
            print("Invalid choice. Please enter R, D, U, or Q.")


def ask_thread_count() -> int:
    """
    Ask user for number of download threads.
    
    Returns:
        Number of threads (default: 3)
    """
    try:
        threads = input("\nEnter number of parallel threads (default: 3): ").strip()
        if not threads:
            return 3
        
        threads = int(threads)
        if threads < 1:
            print("⚠️  Minimum 1 thread required. Using 3 threads.")
            return 3
        elif threads > 10:
            print("⚠️  Maximum 10 threads recommended. Using 10 threads.")
            return 10
        
        return threads
    except ValueError:
        print("Invalid number. Using 3 threads.")
        return 3


def ask_max_videos() -> int | None:
    """
    Ask user for maximum number of videos to extract from channel.
    
    Returns:
        Maximum number of videos or None for all
    """
    try:
        max_vid = input("\nEnter max videos to extract (Enter for all, 50 for quick test): ").strip()
        if not max_vid:
            return None
        
        max_vid = int(max_vid)
        if max_vid < 1:
            print("⚠️  Invalid number. Will extract all videos.")
            return None
        
        print(f"ℹ️  Will extract up to {max_vid} videos")
        return max_vid
    except ValueError:
        print("Invalid number. Will extract all videos.")
        return None


def handle_new_channel(channel_input: str) -> None:
    """
    Handle processing of a new channel (no existing info file).
    
    Args:
        channel_input: YouTube channel URL or username
    """
    print("\n📡 No existing channel info found. Scanning channel...")
    print()
    
    # Ask if user wants to limit videos for faster extraction
    max_videos = ask_max_videos()
    
    # Scan and save channel info
    result = scan_and_save_channel(channel_input, verbose=True, max_videos=max_videos)
    
    if not result:
        print("\n❌ Failed to extract channel information.")
        print("Please check the URL/username and try again.")
        return
    
    username, channel_data = result
    
    print(f"\n✅ Successfully processed channel: @{username}")
    total_videos = len(channel_data['videos']) + len(channel_data['shorts']) + len(channel_data['streams'])
    print(f"   Total videos found: {total_videos}")
    print()
    
    # Ask if user wants to download now
    download_now = input("Do you want to start downloading now? (Y/N): ").strip().lower()
    
    if download_now in ['y', 'yes']:
        handle_download(username, channel_data)
    else:
        print("\nℹ️  You can download later by running the app again.")
        print(f"   Channel info saved at: channels_info/{username}.json")


def handle_rescan(channel_input: str) -> None:
    """
    Handle rescanning of channel info.
    
    Args:
        channel_input: YouTube channel URL or username
    """
    print("\n🔄 Rescanning channel info...")
    print()
    
    # Ensure we have a proper URL format for yt-dlp
    if not channel_input.startswith('http'):
        # Convert username to URL format
        if channel_input.startswith('@'):
            channel_url = f"https://www.youtube.com/{channel_input}"
        else:
            channel_url = f"https://www.youtube.com/@{channel_input}"
    else:
        channel_url = channel_input
    
    # Ask if user wants to limit videos for faster extraction
    max_videos = ask_max_videos()
    
    # Scan and update channel info
    result = scan_and_save_channel(channel_url, verbose=True, max_videos=max_videos)
    
    if not result:
        print("\n❌ Failed to rescan channel information.")
        return
    
    username, channel_data = result
    
    print(f"\n✅ Channel info updated successfully!")
    total_videos = len(channel_data['videos']) + len(channel_data['shorts']) + len(channel_data['streams'])
    print(f"   Total videos: {total_videos}")
    print(f"   Saved at: channels_info/{username}.json")
    print("\nExiting. Run again to download videos.")


def handle_download(username: str, channel_data: dict) -> None:
    """
    Handle video download process.
    
    Args:
        username: Channel username
        channel_data: Channel information dictionary
    """
    print("\n🔍 Scanning for already downloaded videos...")
    print()
    
    # Clean username
    clean_username = sanitize_username(username)
    
    # Scan existing downloads
    missing_videos = scan_existing_downloads(clean_username, channel_data, verbose=True)
    
    # Check if all videos are already downloaded
    if is_all_downloaded(missing_videos):
        print("\n✅ All videos are already downloaded! Nothing to do.")
        # Ask if user wants to upload
        upload_now = input("Do you want to upload to Telegram? (Y/N): ").strip().lower()
        if upload_now in ['y', 'yes']:
            handle_upload(clean_username, channel_data)
        return
    
    # Create download queue
    queue = create_download_queue(missing_videos)
    
    print(f"\n📥 Ready to download {len(queue)} videos")
    
    # Get thread count from user
    max_threads = ask_thread_count()
    
    # Start downloads
    print("\n" + "=" * 60)
    print("🚀 STARTING DOWNLOADS")
    print("=" * 60)
    
    result = resume_download_if_needed(queue, clean_username, max_threads=max_threads, verbose=True)
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 DOWNLOAD SESSION COMPLETE")
    print("=" * 60)
    print(f"✅ Downloaded: {result.get('completed', 0)} videos")
    print(f"❌ Failed: {result.get('failed', 0)} videos")
    if result.get('skipped', 0) > 0:
        print(f"⏭️  Skipped: {result['skipped']} (already existed)")
    print(f"⏱️  Time taken: {result.get('elapsed_time', 0):.2f} seconds")
    print("=" * 60)
    
    # Ask if user wants to retry failed downloads
    if result.get('failed', 0) > 0:
        retry = input("\nDo you want to retry failed downloads? (Y/N): ").strip().lower()
        if retry in ['y', 'yes']:
            print("\n🔄 Retrying failed downloads...")
            # Re-scan to get failed videos
            missing_videos = scan_existing_downloads(clean_username, channel_data, verbose=False)
            queue = create_download_queue(missing_videos)
            if queue:
                download_queue_parallel(queue, clean_username, max_threads=max_threads)
    
    # Ask if user wants to upload now
    upload_now = input("\nDo you want to upload to Telegram now? (Y/N): ").strip().lower()
    if upload_now in ['y', 'yes']:
        handle_upload(clean_username, channel_data)


def handle_upload(username: str, channel_data: dict) -> None:
    """
    Handle video upload to Telegram.
    
    Args:
        username: Channel username
        channel_data: Channel information dictionary
    """
    print("\n📤 TELEGRAM UPLOAD")
    print("=" * 60)
    
    # Load Telegram configuration
    config = load_telegram_config()
    
    # Check if configured
    if not config.get('bot_token') or not config.get('channel_id'):
        print("⚠️  Telegram not configured!")
        print("\nTo configure Telegram upload:")
        print("1. Run: python telegram_uploader.py")
        print("2. Edit telegram_config.json with your credentials")
        print("   - bot_token: Your Telegram bot token")
        print("   - channel_id: Your channel ID")
        print("   - local_api_url: Local Telegram API server URL")
        print("\nMake sure the local Telegram API server is running.")
        return
    
    # Initialize uploader
    uploader = TelegramUploader(config)
    
    # Test connection
    print("Testing Telegram connection...")
    if not uploader.check_connection():
        print("\n❌ Cannot connect to Telegram API server.")
        print("Make sure it's running at:", config.get('local_api_url'))
        return
    
    # Ask upload options
    print("\n📋 Upload Options:")
    print("  [A] Upload all videos (that are downloaded)")
    print("  [N] Upload only new videos (not previously uploaded)")
    print("  [C] Cancel")
    print()
    
    while True:
        choice = input("➡️  Your choice (A/N/C): ").strip().lower()
        
        if choice in ['c', 'cancel', 'quit']:
            print("Upload cancelled.")
            return
        elif choice in ['a', 'all']:
            upload_all = True
            break
        elif choice in ['n', 'new']:
            upload_all = False
            break
        else:
            print("Invalid choice. Please enter A, N, or C.")
    
    # Prepare upload queue
    upload_queue = []
    clean_username = sanitize_username(username)
    
    # Collect all downloaded videos
    for video_type in ['videos', 'shorts', 'streams']:
        videos = channel_data.get(video_type, [])
        
        for video in videos:
            video_id = video.get('id')
            if not video_id:
                continue
            
            # Check if video file exists
            from download_scanner import check_video_exists
            if not check_video_exists(video_id, clean_username, video_type):
                continue  # Skip if not downloaded
            
            # Check if already uploaded (if not uploading all)
            if not upload_all:
                if check_video_uploaded(video_id, clean_username):
                    continue  # Skip if already uploaded
            
            # Add to queue
            upload_queue.append({
                'id': video_id,
                'title': video.get('title', 'Unknown'),
                'url': video.get('url', ''),
                'type': video_type
            })
    
    if not upload_queue:
        print("\n✅ No videos to upload!")
        if upload_all:
            print("   (All videos may already be uploaded, or none downloaded yet)")
        else:
            print("   (All downloaded videos have been uploaded)")
        return
    
    print(f"\n📦 Found {len(upload_queue)} videos to upload")
    
    # Confirm upload
    confirm = input("Start upload? (Y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Upload cancelled.")
        return
    
    # Start upload
    result = uploader.upload_queue(upload_queue, clean_username, verbose=True)
    
    # Log successful uploads
    print("\n📝 Logging upload results...")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 UPLOAD SESSION COMPLETE")
    print("=" * 60)
    print(f"✅ Uploaded: {result['uploaded']} videos")
    if result.get('skipped', 0) > 0:
        print(f"⏭️  Skipped (not found): {result['skipped']} videos")
    print(f"❌ Failed: {result['failed']} videos")
    print("=" * 60)


def main():
    """Main application entry point."""
    print_banner()
    
    # Get user input
    channel_input = get_user_input()
    
    # Check if info file exists
    if check_info_file_exists(channel_input):
        # Info exists, ask for action
        clean_username = sanitize_username(channel_input)
        action = ask_rescan_or_download(clean_username)
        
        if action == 'quit':
            print("\n👋 Goodbye!")
            return
        elif action == 'rescan':
            handle_rescan(channel_input)
        elif action == 'download':
            # Load existing channel data
            channel_data = load_channel_info(clean_username)
            if channel_data:
                handle_download(clean_username, channel_data)
            else:
                print("\n❌ Error loading channel data. Please rescan.")
        elif action == 'upload':
            # Load existing channel data
            channel_data = load_channel_info(clean_username)
            if channel_data:
                handle_upload(clean_username, channel_data)
            else:
                print("\n❌ Error loading channel data. Please rescan.")
    else:
        # New channel, no info file
        handle_new_channel(channel_input)
    
    print("\n✨ Thank you for using YouTube Channel Downloader!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)