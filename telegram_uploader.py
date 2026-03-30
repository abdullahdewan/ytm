"""
Telegram Upload Module for YouTube videos.
Uploads downloaded videos to Telegram channel using local bot API server.
"""

import os
import requests
import json
import time
from pathlib import Path
from typing import TypedDict


class VideoInfo(TypedDict):
    """Type definition for video information."""
    id: str
    title: str
    url: str
    type: str  # 'videos', 'shorts', or 'streams'


class TelegramUploader:
    """Handles uploading videos to Telegram channel."""
    
    def __init__(self, config: dict = None):
        """
        Initialize Telegram uploader with configuration.
        
        Args:
            config: Dictionary with Telegram configuration
                   {local_api_url, bot_token, channel_id}
        """
        self.config = config or {
            'local_api_url': "http://localhost:8081",
            'bot_token': "",
            'channel_id': ""
        }
        
        self.local_api_url = self.config.get('local_api_url', "http://localhost:8081")
        self.bot_token = self.config.get('bot_token', "")
        self.channel_id = self.config.get('channel_id', "")
        
        # Validate configuration
        if not self.bot_token or not self.channel_id:
            print("⚠️  Warning: Telegram bot_token or channel_id not configured")
    
    def find_video_file(self, video_id: str, username: str, video_type: str) -> Path | None:
        """
        Find the video file in downloads directory.
        
        Args:
            video_id: YouTube video ID
            username: Channel username
            video_type: Type of video ('videos', 'shorts', 'streams')
            
        Returns:
            Path to video file or None if not found
        """
        base_dir = Path(__file__).parent
        downloads_dir = base_dir / 'downloads'
        type_folder = {'videos': 'videos', 'shorts': 'shorts', 'streams': 'streams'}[video_type]
        
        # Check possible extensions
        extensions = ['.mp4', '.mkv', '.webm', '.flv']
        
        for ext in extensions:
            # Check both username variations
            possible_paths = [
                downloads_dir / username / type_folder / f"{video_id}{ext}",
                downloads_dir / username.lower() / type_folder / f"{video_id}{ext}",
            ]
            
            for path in possible_paths:
                if path.exists():
                    return path
        
        return None
    
    def upload_single_video(self, video_info: VideoInfo, username: str, 
                           verbose: bool = True) -> bool:
        """
        Upload a single video to Telegram channel.
        
        Args:
            video_info: Dictionary with video information
            username: Channel username
            verbose: Print progress messages
            
        Returns:
            True if upload successful, False otherwise
        """
        video_id = str(video_info.get('id'))
        title = video_info.get('title', 'No Title')
        video_type = video_info.get('type', 'videos')
        
        # Find the video file
        file_path = self.find_video_file(video_id, username, video_type)
        
        if not file_path:
            if verbose:
                print(f"[SKIPPED] File for ID {video_id} not found in downloads/")
            return False
        
        if verbose:
            print(f"[UPLOADING] {title[:50]}... (ID: {video_id})")
        
        # Prepare Telegram API request
        url = f"{self.local_api_url}/bot{self.bot_token}/sendVideo"
        
        # Create enhanced caption with short URL
        short_url = f"https://youtu.be/{video_id}"
        caption = f"{title}\n\n🔗 {short_url}"
        
        # Get thumbnail (mqdefault is safer and fits Telegram's 320x320 requirement)
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
        
        # Download thumbnail to memory
        thumbnail_data = None
        try:
            thumb_response = requests.get(thumbnail_url, timeout=10)
            if thumb_response.status_code == 200:
                thumbnail_data = thumb_response.content
        except Exception as e:
            if verbose:
                print(f"⚠️  Could not download thumbnail for {video_id}: {e}")
        
        data = {
            'chat_id': self.channel_id,
            'caption': caption,
            'supports_streaming': 'true',
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(file_path, 'rb') as f:
                    files = {'video': (file_path.name, f)}
                    
                    # Add thumbnail to multipart if downloaded
                    if thumbnail_data:
                        files['thumbnail'] = ('thumb.jpg', thumbnail_data)

                    response = requests.post(
                        url,
                        data=data,
                        files=files,
                        timeout=600  # 10 minutes timeout for large files
                    )

                    if response.status_code == 200:
                        if verbose:
                            print(f"[SUCCESS] Uploaded: {title[:50]}...")
                        return response.json()

                    elif response.status_code == 429:
                        # Handle Rate Limit
                        error_data = response.json()
                        retry_after = error_data.get('parameters', {}).get('retry_after', 5)
                        if verbose:
                            print(f"⚠️  Rate limited by Telegram (429). Sleeping for {retry_after} seconds...")
                        time.sleep(retry_after + 1)  # Add 1s buffer
                        continue # Retry

                    else:
                        if verbose:
                            print(f"[FAILED] Error {response.status_code}: {response.text}")
                        return None

            except requests.exceptions.Timeout:
                if verbose:
                    print(f"[ERROR] Timeout uploading: {title[:50]}...")
                return False
            except requests.exceptions.ConnectionError:
                if verbose:
                    print(f"[ERROR] Connection failed. Is local Telegram API server running?")
                return False
            except Exception as e:
                if verbose:
                    print(f"[ERROR] Upload failed for {title[:50]}...: {e}")
                return False

        # If we exhausted retries
        if verbose:
            print(f"[FAILED] Exhausted retries for {title[:50]}...")
        return False
    
    def upload_queue(self, queue: list[VideoInfo], username: str, 
                    start_from_beginning: bool = True, verbose: bool = True) -> dict:
        """
        Upload multiple videos from queue.
        
        Args:
            queue: List of videos to upload
            username: Channel username
            start_from_beginning: If True, start from first video; if False, resume
            verbose: Print progress messages
            
        Returns:
            Dictionary with upload statistics
        """
        if not queue:
            return {'uploaded': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        
        uploaded = []
        failed = []
        skipped = []
        
        total_videos = len(queue)
        
        if verbose:
            print("\n" + "=" * 60)
            print("📤 TELEGRAM UPLOAD STARTED")
            print("=" * 60)
            print(f"📦 Total videos in queue: {total_videos}")
            print(f"👤 Channel: {username}")
            print(f"🤖 Bot API: {self.local_api_url}")
            print("=" * 60)
        
        # Sort by ID if starting from beginning
        if start_from_beginning:
            try:
                queue = sorted(queue, key=lambda x: int(x['id']))
            except (ValueError, KeyError):
                # If ID is not numeric, sort alphabetically
                queue = sorted(queue, key=lambda x: str(x['id']))
        
        for idx, video_info in enumerate(queue, 1):
            video_id = str(video_info.get('id'))
            
            if verbose:
                print(f"\n[{idx}/{total_videos}] Processing...")
            
            # Proactive delay to avoid hitting Telegram rate limits (except for first video)
            if idx > 1:
                time.sleep(3)

            result = self.upload_single_video(video_info, username, verbose)
            
            if result:
                uploaded.append(video_id)
                # Log successful upload
                from download_scanner import log_uploaded_video, log_telegram_response
                log_uploaded_video(video_id, username, success=True)
                log_telegram_response(video_id, username, result)

                # Delete successfully uploaded file
                file_path = self.find_video_file(
                    video_id,
                    username,
                    video_info.get('type', 'videos')
                )
                if file_path and file_path.exists():
                    try:
                        file_path.unlink()
                        if verbose:
                            print(f"[CLEANUP] Deleted local file: {file_path.name}")
                    except Exception as e:
                        if verbose:
                            print(f"[CLEANUP ERROR] Could not delete {file_path.name}: {e}")
            elif result is None:
                # Check if file was not found (skip) or upload failed
                file_path = self.find_video_file(
                    video_id, 
                    username, 
                    video_info.get('type', 'videos')
                )
                if not file_path:
                    skipped.append(video_id)
                else:
                    failed.append(video_id)
                    # Log failed upload
                    from download_scanner import log_uploaded_video
                    log_uploaded_video(video_id, username, success=False)
        
        if verbose:
            print("\n" + "=" * 60)
            print("📊 UPLOAD SUMMARY")
            print("=" * 60)
            print(f"✅ Uploaded: {len(uploaded)}/{total_videos}")
            if skipped:
                print(f"⏭️  Skipped (not found): {len(skipped)}/{total_videos}")
            print(f"❌ Failed: {len(failed)}/{total_videos}")
            print("=" * 60)
        
        return {
            'uploaded': len(uploaded),
            'failed': len(failed),
            'skipped': len(skipped),
            'total': total_videos
        }
    
    def check_connection(self) -> bool:
        """
        Check if Telegram local API server is accessible.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_url = f"{self.local_api_url}/bot{self.bot_token}/getMe"
            response = requests.get(test_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    print(f"✅ Connected to Telegram bot: @{data.get('result', {}).get('username', 'unknown')}")
                    return True
            
            return False
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to Telegram API server at {self.local_api_url}")
            print("   Make sure the local Telegram API server is running.")
            return False
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


def load_telegram_config(config_file: str = 'telegram_config.json') -> dict:
    """
    Load Telegram configuration from JSON file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Dictionary with configuration
    """
    config_path = Path(__file__).parent / config_file
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Default configuration
    return {
        'local_api_url': "http://localhost:8081",
        'bot_token': "",
        'channel_id': "",
        'admin_ids': []
    }


def save_telegram_config(config: dict, config_file: str = 'telegram_config.json') -> bool:
    """
    Save Telegram configuration to JSON file.
    
    Args:
        config: Configuration dictionary
        config_file: Path to configuration file
        
    Returns:
        True if saved successfully, False otherwise
    """
    config_path = Path(__file__).parent / config_file
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def create_sample_config() -> bool:
    """
    Create a sample Telegram configuration file.
    
    Returns:
        True if created successfully, False otherwise
    """
    config = {
        'local_api_url': "http://localhost:8081",
        'bot_token': "YOUR_BOT_TOKEN_HERE",
        'channel_id': "YOUR_CHANNEL_ID_HERE",
        'admin_ids': [123456789]
    }
    
    return save_telegram_config(config)


if __name__ == "__main__":
    # Test the module
    import sys
    
    print("=" * 60)
    print("🧪 TELEGRAM UPLOADER - TEST")
    print("=" * 60)
    
    # Check if config exists
    config_path = Path(__file__).parent / 'telegram_config.json'
    
    if not config_path.exists():
        print("\n⚠️  No configuration file found.")
        print("Creating sample telegram_config.json...")
        create_sample_config()
        print(f"\n✅ Created: {config_path}")
        print("\n📝 Edit this file with your Telegram credentials:")
        print("   - bot_token: Your Telegram bot token")
        print("   - channel_id: Your channel ID (e.g., -100xxxxxxxxx)")
        print("   - local_api_url: Local Telegram API server URL")
        sys.exit(0)
    
    # Load config
    config = load_telegram_config()
    
    # Test connection
    print("\nTesting Telegram connection...")
    uploader = TelegramUploader(config)
    
    if uploader.check_connection():
        print("\n✅ Connection successful!")
        
        # Ask if user wants to test upload
        test = input("\nDo you want to test upload? (Y/N): ").strip().lower()
        if test == 'y':
            # Load a test video from existing downloads
            from download_scanner import load_channel_info
            from download_scanner import create_download_queue
            
            username = input("Enter username: ")
            channel_data = load_channel_info(username)
            
            if channel_data:
                # Get first video for test
                test_video = channel_data.get('videos', [None])[0]
                if test_video:
                    queue = [test_video]
                    result = uploader.upload_queue(queue, username)
                    print(f"\nTest upload complete: {result}")
                else:
                    print("No videos found in channel data")
            else:
                print("Channel info not found")
    else:
        print("\n❌ Connection failed. Check your configuration.")
        print("\nMake sure:")
        print("   1. Local Telegram API server is running")
        print("   2. Bot token is correct")
        print("   3. Channel ID is correct")
        print("   4. Bot is admin in the channel")
