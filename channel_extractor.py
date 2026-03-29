"""
Module to extract channel information from YouTube and save to JSON files.
Saves channel info in channels_info/ folder without @ in username.
"""

import yt_dlp
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from yt_dlp_config import get_youtube_cookie_opts


def sanitize_username(username: str) -> str:
    """Remove @ symbol and sanitize username for filename."""
    if username.startswith('@'):
        username = username[1:]
    # Replace spaces and special chars with underscores
    sanitized = ''.join(c if c.isalnum() else '_' for c in username)
    return sanitized.lower()


def get_channels_info_dir() -> Path:
    """Get the channels_info directory path."""
    base_dir = Path(__file__).parent
    channels_info_dir = base_dir / 'channels_info'
    channels_info_dir.mkdir(exist_ok=True)
    return channels_info_dir




def extract_channel_info(channel_url: str, verbose: bool = True, max_videos: int = None) -> dict | None:
    """
    Extract comprehensive channel information from YouTube.
    Uses hybrid approach: fast flat extraction + targeted detail extraction.
    
    Args:
        channel_url: YouTube channel URL or username
        verbose: Print progress messages
        max_videos: Maximum number of videos to extract (None for all)
        
    Returns:
        Dictionary containing channel info or None if extraction fails
    """
    # Use extractor_args to get more data even with extract_flat
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extractor_args': {
            'youtube': {
                'skip': 'hls,dash'  # Skip heavy formats
            }
        },
    }
    
    # Add YouTube authentication (cookies)
    auth_opts = get_youtube_cookie_opts()
    ydl_opts.update(auth_opts)
    
    # Only add playlistend if we want to limit videos
    if max_videos:
        ydl_opts['playlistend'] = max_videos
    
    try:
        if verbose:
            print(f"🔍 Extracting channel info from: {channel_url}")
            print("⏳ This may take a moment for large channels...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            channel_info = ydl.extract_info(channel_url, download=False)
            
            if not channel_info:
                if verbose:
                    print("❌ Failed to extract channel info")
                return None
            
            # Get username/channel name
            uploader_id = channel_info.get('uploader_id', '')
            channel_name = channel_info.get('channel', channel_info.get('uploader', 'unknown_channel'))
            
            # Sanitize username for filename (remove @)
            username = sanitize_username(uploader_id) if uploader_id else sanitize_username(channel_name)
            
            if verbose:
                print(f"📺 Channel: {channel_name}")
                print(f"👤 Username: @{username}")
            
            # Initialize categorized data
            categorized_data = {
                'channel_info': {
                    'id': channel_info.get('id'),
                    'channel': channel_name,
                    'channel_id': channel_info.get('channel_id'),
                    'title': channel_info.get('title'),
                    'description': channel_info.get('description'),
                    'uploader_id': uploader_id,
                    'uploader_url': channel_info.get('uploader_url'),
                    'channel_url': channel_info.get('channel_url'),
                    'channel_follower_count': channel_info.get('channel_follower_count'),
                    'playlist_count': channel_info.get('playlist_count'),
                    'view_count': channel_info.get('view_count'),
                    'thumbnails': channel_info.get('thumbnails'),
                    'tags': channel_info.get('tags'),
                },
                'videos': [],
                'shorts': [],
                'streams': []
            }
            
            # Check if we got playlists or direct entries
            entries = channel_info.get('entries', [])
            
            if verbose:
                print(f"   ℹ️  Found {len(entries) if entries else 0} entries")
                if entries and len(entries) > 0:
                    for i, e in enumerate(entries[:3], 1):
                        url = e.get('url', 'NO_URL')
                        title = e.get('title', 'NO_TITLE')
                        print(f"   Entry {i}: {title[:40]}... -> {url[:60] if url else 'None'}")
            
            # If entries are playlists (videos, shorts, streams), extract each
            if entries and len(entries) > 0:
                # Check if this looks like a playlist container
                first_entry = entries[0]
                is_playlist_container = False
                
                # Check various indicators
                if first_entry.get('url'):
                    if any(x in first_entry.get('url', '') for x in ['/videos', '/shorts', '/streams', '/live']):
                        is_playlist_container = True
                elif first_entry.get('_type') == 'playlist' or first_entry.get('extractor_key') == 'YoutubeTab':
                    is_playlist_container = True
                
                if is_playlist_container:
                    if verbose:
                        print(f"📋 Found playlist structure, extracting individual videos...")
                    
                    # Extract from each playlist type
                    all_videos = []
                    
                    for entry in entries:
                        playlist_url = entry.get('url') or entry.get('webpage_url')
                        playlist_title = entry.get('title', '')
                        
                        # If no URL, try to construct it from channel URL
                        if not playlist_url:
                            # Try to get the tab type and construct URL
                            base_channel_url = channel_info.get('channel_url') or channel_info.get('uploader_url')
                            if base_channel_url:
                                # Remove trailing slash
                                base_channel_url = base_channel_url.rstrip('/')
                                # Determine tab from title
                                if 'short' in playlist_title.lower():
                                    playlist_url = f"{base_channel_url}/shorts"
                                elif 'live' in playlist_title.lower() or 'stream' in playlist_title.lower():
                                    playlist_url = f"{base_channel_url}/streams"
                                else:
                                    playlist_url = f"{base_channel_url}/videos"
                            
                            if not playlist_url:
                                if verbose:
                                    print(f"   ⚠️  Skipping entry (no URL): {playlist_title}")
                                continue
                        
                        # Determine type from URL
                        is_shorts_list = '/shorts' in playlist_url
                        is_streams_list = '/streams' in playlist_url or '/live' in playlist_url
                        
                        if verbose:
                            print(f"   📥 Extracting from: {playlist_title[:50]}...")
                        
                        # Extract videos from this playlist with limit
                        try:
                            pl_ydl_opts = ydl_opts.copy()
                            if max_videos:
                                # Divide limit among playlists
                                pl_ydl_opts['playlistend'] = max(1, max_videos // len(entries))
                            
                            with yt_dlp.YoutubeDL(pl_ydl_opts) as pl_ydl:
                                playlist_info = pl_ydl.extract_info(playlist_url, download=False)
                                
                                if playlist_info:
                                    playlist_entries = playlist_info.get('entries', [])
                                    
                                    for vid in playlist_entries:
                                        if vid and vid.get('id'):
                                            video_data = {
                                                'id': vid.get('id'),
                                                'title': vid.get('title'),
                                                'url': vid.get('url') or f"https://www.youtube.com/watch?v={vid.get('id')}",
                                                'thumbnail': vid.get('thumbnail'),
                                                'duration': vid.get('duration'),
                                                'view_count': vid.get('view_count'),
                                                'upload_date': vid.get('upload_date'),
                                                'live_status': vid.get('live_status'),
                                            }
                                            categorized_data['shorts' if is_shorts_list else ('streams' if is_streams_list else 'videos')].append(video_data)
                                            all_videos.append(video_data)
                                    
                                    if verbose:
                                        print(f"      ✅ Got {len(playlist_entries)} items from this playlist")
                                
                        except Exception as e:
                            if verbose:
                                print(f"   ⚠️  Could not extract {playlist_title}: {e}")
                    
                    if verbose:
                        print(f"✅ Extracted {len(all_videos)} total videos from all playlists")
            
            if verbose:
                print(f"📊 Found:")
                print(f"   • Videos: {len(categorized_data['videos'])}")
                print(f"   • Shorts: {len(categorized_data['shorts'])}")
                print(f"   • Streams: {len(categorized_data['streams'])}")
                print(f"   • Total: {len(categorized_data['videos']) + len(categorized_data['shorts']) + len(categorized_data['streams'])}")
            
            return categorized_data
            
    except Exception as e:
        if verbose:
            print(f"❌ Error extracting channel info: {e}")
        return None


def save_channel_info(channel_data: dict, username: str, verbose: bool = True) -> str | None:
    """
    Save channel information to JSON file in channels_info folder.
    
    Args:
        channel_data: Dictionary containing channel info
        username: Username (without @) for filename
        verbose: Print progress messages
        
    Returns:
        Path to saved file or None if failed
    """
    try:
        channels_info_dir = get_channels_info_dir()
        filename = f"{username}.json"
        filepath = channels_info_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(channel_data, f, ensure_ascii=False, indent=2)
        
        if verbose:
            print(f"✅ Saved channel info to: {filepath}")
        
        return str(filepath)
        
    except Exception as e:
        if verbose:
            print(f"❌ Error saving channel info: {e}")
        return None


def load_channel_info(username: str, verbose: bool = True) -> dict | None:
    """
    Load existing channel info from JSON file.
    
    Args:
        username: Username (with or without @)
        verbose: Print progress messages
        
    Returns:
        Dictionary containing channel info or None if not found
    """
    try:
        # Remove @ if present
        clean_username = username[1:] if username.startswith('@') else username
        clean_username = sanitize_username(clean_username)
        
        channels_info_dir = get_channels_info_dir()
        filepath = channels_info_dir / f"{clean_username}.json"
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if verbose:
                print(f"✅ Loaded existing channel info: {filepath}")
            return data
        else:
            if verbose:
                print(f"ℹ️  No existing info found for: {clean_username}")
            return None
            
    except Exception as e:
        if verbose:
            print(f"❌ Error loading channel info: {e}")
        return None


def scan_and_save_channel(channel_url: str, verbose: bool = True, max_videos: int = None) -> tuple[str, dict] | None:
    """
    Complete workflow: extract channel info and save to file.
    
    Args:
        channel_url: YouTube channel URL or username
        verbose: Print progress messages
        max_videos: Maximum number of videos to extract (None for all)
        
    Returns:
        Tuple of (username, channel_data) or None if failed
    """
    # Ensure we have a proper URL format
    if not channel_url.startswith('http'):
        # Convert username to URL format
        if channel_url.startswith('@'):
            full_url = f"https://www.youtube.com/{channel_url}"
        else:
            full_url = f"https://www.youtube.com/@{channel_url}"
        
        if verbose:
            print(f"ℹ️  Converting '{channel_url}' to: {full_url}")
        
        channel_url = full_url
    
    # Extract info
    channel_data = extract_channel_info(channel_url, verbose, max_videos)
    if not channel_data:
        return None
    
    # Get username from data
    uploader_id = channel_data['channel_info'].get('uploader_id', '')
    username = sanitize_username(uploader_id) if uploader_id else sanitize_username(channel_data['channel_info']['channel'])
    
    # Save to file
    saved_path = save_channel_info(channel_data, username, verbose)
    if not saved_path:
        return None
    
    return (username, channel_data)


if __name__ == "__main__":
    # Test the module
    url = input("Enter YouTube channel URL or username: ")
    result = scan_and_save_channel(url)
    if result:
        username, data = result
        print(f"\n✅ Successfully processed channel: @{username}")
        print(f"   Total videos: {len(data['videos']) + len(data['shorts']) + len(data['streams'])}")
