"""
Module to scan existing downloads and identify missing videos.
Creates download queue for videos that haven't been downloaded yet.
"""

import os
import json
from pathlib import Path
from typing import TypedDict


class VideoInfo(TypedDict):
    """Type definition for video information."""
    id: str
    title: str
    url: str
    type: str  # 'videos', 'shorts', or 'streams'


def get_downloads_dir() -> Path:
    """Get the downloads directory path."""
    base_dir = Path(__file__).parent
    downloads_dir = base_dir / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    return downloads_dir


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    base_dir = Path(__file__).parent
    logs_dir = base_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def check_video_exists(video_id: str, username: str, video_type: str, extensions: list[str] = None) -> bool:
    """
    Check if a video file already exists in downloads folder.
    
    Args:
        video_id: YouTube video ID
        username: Channel username (folder name)
        video_type: Type of video ('videos', 'shorts', 'streams')
        extensions: List of possible file extensions to check
        
    Returns:
        True if video exists, False otherwise
    """
    if extensions is None:
        extensions = ['.mp4', '.mkv', '.webm', '.flv', '.avi']
    
    downloads_dir = get_downloads_dir()
    type_folder = {'videos': 'videos', 'shorts': 'shorts', 'streams': 'streams'}[video_type]
    
    # Check in both possible folder structures with each extension
    for ext in extensions:
        possible_paths = [
            downloads_dir / username / type_folder / f"{video_id}{ext}",
            downloads_dir / username.lower() / type_folder / f"{video_id}{ext}",
        ]
        
        for filepath in possible_paths:
            if filepath.exists():
                return True
    
    return False


def check_video_uploaded(video_id: str, username: str, upload_log_file: str = None) -> bool:
    """
    Check if a video has been uploaded to Telegram by checking upload log.
    
    Args:
        video_id: YouTube video ID
        username: Channel username
        upload_log_file: Path to upload log JSON file
        
    Returns:
        True if video was uploaded, False otherwise
    """
    if upload_log_file is None:
        upload_log_file = f'{username}_upload_log.json'
    
    log_path = get_logs_dir() / upload_log_file
    
    if not log_path.exists():
        return False
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            uploaded_ids = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(uploaded_ids, list):
            return str(video_id) in [str(id) for id in uploaded_ids]
        elif isinstance(uploaded_ids, dict):
            # Only return True if the value is explicitly True (successful upload)
            return uploaded_ids.get(str(video_id)) is True
        else:
            return False
    except Exception:
        return False


def get_channel_stats(username: str) -> dict:
    """
    Get download/upload statistics for a channel.
    
    Args:
        username: Channel username
        
    Returns:
        Dictionary with total, downloaded, uploaded, pending_download, pending_upload counts.
    """
    channels_dir = Path(__file__).parent / 'channels_info'
    info_file = channels_dir / f'{username.lower()}.json'
    
    stats = {
        'total': 0,
        'downloaded': 0,
        'uploaded': 0,
        'pending_download': 0,
        'pending_upload': 0,
        'by_type': {}
    }
    
    if not info_file.exists():
        return stats
    
    with open(info_file, 'r', encoding='utf-8') as f:
        channel_data = json.load(f)
    
    for video_type in ['videos', 'shorts', 'streams']:
        videos = channel_data.get(video_type, [])
        type_stats = {'total': 0, 'downloaded': 0, 'uploaded': 0}
        
        for video in videos:
            video_id = video.get('id')
            if not video_id:
                continue
            
            type_stats['total'] += 1
            
            if check_video_exists(video_id, username, video_type):
                type_stats['downloaded'] += 1
            
            if check_video_uploaded(video_id, username):
                type_stats['uploaded'] += 1
        
        stats['by_type'][video_type] = type_stats
        stats['total'] += type_stats['total']
        stats['downloaded'] += type_stats['downloaded']
        stats['uploaded'] += type_stats['uploaded']
    
    stats['pending_download'] = stats['total'] - stats['downloaded'] - (stats['uploaded'] - stats['downloaded'])
    # pending_download = total - downloaded - uploaded_but_cleaned
    # Simpler: anything not downloaded AND not uploaded
    stats['pending_download'] = sum(
        1 for vtype in ['videos', 'shorts', 'streams']
        for v in channel_data.get(vtype, [])
        if v.get('id') and not check_video_exists(v['id'], username, vtype) and not check_video_uploaded(v['id'], username)
    )
    stats['pending_upload'] = stats['downloaded'] - (stats['uploaded'] - stats['pending_download'])
    # Simpler: downloaded but not yet uploaded
    stats['pending_upload'] = sum(
        1 for vtype in ['videos', 'shorts', 'streams']
        for v in channel_data.get(vtype, [])
        if v.get('id') and check_video_exists(v['id'], username, vtype) and not check_video_uploaded(v['id'], username)
    )
    
    return stats


def scan_existing_downloads(username: str, channel_data: dict, verbose: bool = True,
                           check_upload_status: bool = False) -> dict[str, list[VideoInfo]]:
    """
    Scan channel data and identify which videos are already downloaded.
    
    Args:
        username: Channel username
        channel_data: Dictionary containing channel info from channel_extractor
        verbose: Print progress messages
        check_upload_status: Also check if videos were uploaded to Telegram
        
    Returns:
        Dictionary with keys 'videos', 'shorts', 'streams' containing lists of missing videos
    """
    missing_videos = {
        'videos': [],
        'shorts': [],
        'streams': []
    }
    
    total_found = {'videos': 0, 'shorts': 0, 'streams': 0}
    
    # Process each category
    for video_type in ['videos', 'shorts', 'streams']:
        videos_in_info = channel_data.get(video_type, [])
        
        if verbose:
            print(f"📊 Scanning {video_type}...")
        
        for video in videos_in_info:
            video_id = video.get('id')
            if not video_id:
                continue
            
            total_found[video_type] += 1
            
            # Check if video exists
            exists = check_video_exists(video_id, username, video_type)
            
            # Skip if already uploaded (no need to re-download cleaned files)
            is_uploaded = check_video_uploaded(video_id, username)
            if exists or is_uploaded:
                continue
            
            if not exists:
                # Add to missing list
                video_info = VideoInfo(
                    id=video_id,
                    title=video.get('title', 'Unknown'),
                    url=video.get('url', ''),
                    type=video_type
                )
                
                # Add upload status if checking
                if check_upload_status:
                    video_info['downloaded'] = exists
                    video_info['uploaded'] = is_uploaded
                
                missing_videos[video_type].append(video_info)
    
    if verbose:
        print("\n📋 Download Status:")
        for video_type in ['videos', 'shorts', 'streams']:
            total = total_found[video_type]
            missing = len(missing_videos[video_type])
            downloaded = total - missing
            print(f"   • {video_type.capitalize()}: {downloaded}/{total} downloaded ({missing} pending)")
        
        total_missing = sum(len(videos) for videos in missing_videos.values())
        print(f"\n💾 Total to download: {total_missing} videos")
        
        if check_upload_status:
            # Count uploaded
            total_uploaded = sum(
                1 for videos in missing_videos.values() 
                for v in videos if v.get('uploaded', False)
            )
            print(f"📤 Already uploaded to Telegram: {total_uploaded}")
    
    return missing_videos


def create_download_queue(missing_videos: dict[str, list[VideoInfo]]) -> list[VideoInfo]:
    """
    Create a flat download queue from categorized missing videos.
    
    Args:
        missing_videos: Dictionary with categorized missing videos
        
    Returns:
        List of VideoInfo dictionaries ready for download
    """
    queue = []
    
    # Add all categories to queue
    for video_type in ['videos', 'shorts', 'streams']:
        queue.extend(missing_videos.get(video_type, []))
    
    return queue


def get_queue_stats(queue: list[VideoInfo]) -> dict:
    """
    Get statistics about download queue.
    
    Args:
        queue: List of videos to download
        
    Returns:
        Dictionary with queue statistics
    """
    stats = {
        'total': len(queue),
        'videos': sum(1 for v in queue if v['type'] == 'videos'),
        'shorts': sum(1 for v in queue if v['type'] == 'shorts'),
        'streams': sum(1 for v in queue if v['type'] == 'streams'),
    }
    return stats


def is_all_downloaded(missing_videos: dict[str, list[VideoInfo]]) -> bool:
    """
    Check if all videos are already downloaded.
    
    Args:
        missing_videos: Dictionary with categorized missing videos
        
    Returns:
        True if all videos are downloaded, False otherwise
    """
    total_missing = sum(len(videos) for videos in missing_videos.values())
    return total_missing == 0


def log_uploaded_video(video_id: str, username: str, success: bool = True,
                      upload_log_file: str = None) -> bool:
    """
    Log an uploaded video to the upload log file.
    
    Args:
        video_id: YouTube video ID
        username: Channel username
        success: Whether upload was successful
        upload_log_file: Path to upload log JSON file
        
    Returns:
        True if logged successfully, False otherwise
    """
    if upload_log_file is None:
        upload_log_file = f'{username}_upload_log.json'
    
    log_path = get_logs_dir() / upload_log_file
    
    try:
        # Load existing log or create new
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                uploaded_ids = json.load(f)
        else:
            uploaded_ids = {}
        
        # Ensure it's a dict format
        if isinstance(uploaded_ids, list):
            uploaded_ids = {str(id): True for id in uploaded_ids}
        
        # Add new entry
        if success:
            uploaded_ids[str(video_id)] = True
        else:
            uploaded_ids[str(video_id)] = False
        
        # Save back
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(uploaded_ids, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error logging upload: {e}")
        return False


def clean_uploaded_files(username: str = None) -> dict:
    """
    Delete downloaded video files that have already been uploaded.
    
    Args:
        username: Optional channel username. If None, cleans all channels.
        
    Returns:
        Dictionary with 'deleted' count, 'freed_bytes', and 'errors'.
    """
    downloads_dir = get_downloads_dir()
    logs_dir = get_logs_dir()
    extensions = ['.mp4', '.mkv', '.webm', '.flv', '.avi']
    result = {'deleted': 0, 'freed_bytes': 0, 'errors': 0, 'channels': []}
    
    # Determine which channels to clean
    if username:
        usernames = [username.lower()]
    else:
        # Find all upload logs
        usernames = []
        for log_file in logs_dir.glob('*_upload_log.json'):
            name = log_file.stem.replace('_upload_log', '')
            usernames.append(name)
    
    for uname in usernames:
        log_path = logs_dir / f'{uname}_upload_log.json'
        if not log_path.exists():
            print(f"⚠️  No upload log found for '{uname}', skipping.")
            continue
        
        with open(log_path, 'r', encoding='utf-8') as f:
            uploaded_ids = json.load(f)
        
        # Get successfully uploaded IDs
        uploaded = [vid for vid, status in uploaded_ids.items() if status is True]
        if not uploaded:
            print(f"ℹ️  No uploaded videos for '{uname}'.")
            continue
        
        channel_deleted = 0
        channel_freed = 0
        
        for video_id in uploaded:
            for video_type in ['videos', 'shorts', 'streams']:
                paths = [
                    downloads_dir / uname / video_type,
                    downloads_dir / uname.lower() / video_type,
                ]
                for p_dir in paths:
                    if p_dir.exists():
                        for filepath in p_dir.glob(f"{video_id}*"):
                            if filepath.is_file():
                                try:
                                    size = filepath.stat().st_size
                                    filepath.unlink()
                                    channel_deleted += 1
                                    channel_freed += size
                                    print(f"  🗑️  {filepath.name} ({size / (1024*1024):.1f} MB)")
                                except Exception as e:
                                    print(f"  ❌ Error deleting {filepath.name}: {e}")
                                    result['errors'] += 1
        
        if channel_deleted > 0:
            print(f"  ✅ {uname}: Deleted {channel_deleted} files, freed {channel_freed / (1024*1024):.1f} MB")
            result['channels'].append(uname)
        
        result['deleted'] += channel_deleted
        result['freed_bytes'] += channel_freed
    
    return result


def log_telegram_response(video_id: str, username: str, response_data: dict,
                         response_log_file: str = None) -> bool:
    """
    Log detailed Telegram response for an uploaded video.
    
    Args:
        video_id: YouTube video ID
        username: Channel username
        response_data: Dictionary containing Telegram API response
        response_log_file: Path to response log JSON file
        
    Returns:
        True if logged successfully, False otherwise
    """
    if response_log_file is None:
        response_log_file = f'{username}_telegram_responses.json'
    
    log_path = get_logs_dir() / response_log_file
    
    try:
        # Load existing log or create new
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = {}
        
        # Add new entry (or update existing)
        # We only care about the 'result' part of the Telegram API response
        history[str(video_id)] = response_data.get('result', response_data)
        
        # Save back
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error logging Telegram response: {e}")
        return False


if __name__ == "__main__":
    # Test the module
    import json
    from channel_extractor import load_channel_info
    
    username = input("Enter username (with or without @): ")
    channel_data = load_channel_info(username)
    
    if channel_data:
        clean_username = username[1:] if username.startswith('@') else username
        missing = scan_existing_downloads(clean_username, channel_data)
        queue = create_download_queue(missing)
        
        if is_all_downloaded(missing):
            print("\n✅ All videos are already downloaded!")
        else:
            print(f"\n📥 Ready to download {len(queue)} videos")
    else:
        print("❌ Channel info not found. Please run channel_extractor first.")
