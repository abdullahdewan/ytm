"""
Multi-threaded download module for YouTube videos.
Downloads videos to organized folders: downloads/username/videos|shorts|streams/id.ext
"""

import yt_dlp
import threading
from pathlib import Path
from typing import TypedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from dotenv import load_dotenv
from yt_dlp_config import get_youtube_cookie_opts


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




def create_download_path(username: str, video_type: str) -> Path:
    """
    Create the download directory structure for a specific video type.
    
    Args:
        username: Channel username (folder name)
        video_type: Type of video ('videos', 'shorts', 'streams')
        
    Returns:
        Path to the download directory
    """
    downloads_dir = get_downloads_dir()
    type_folder = {'videos': 'videos', 'shorts': 'shorts', 'streams': 'streams'}[video_type]
    
    download_path = downloads_dir / username / type_folder
    download_path.mkdir(parents=True, exist_ok=True)
    
    return download_path


def download_single_video(video_info: VideoInfo, username: str, progress_callback=None) -> bool:
    """
    Download a single YouTube video.
    
    Args:
        video_info: Dictionary with video information
        username: Channel username for folder organization
        progress_callback: Optional callback function for progress updates
        
    Returns:
        True if download successful, False otherwise
    """
    video_id = video_info['id']
    video_title = video_info.get('title', 'Unknown')
    video_url = video_info['url']
    video_type = video_info['type']
    
    try:
        # Create download path
        download_path = create_download_path(username, video_type)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'outtmpl': str(download_path / f'{video_id}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        # Add YouTube authentication (cookies)
        auth_opts = get_youtube_cookie_opts()
        ydl_opts.update(auth_opts)
        
        if progress_callback:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes', 0)
                    eta = d.get('eta', 0)
                    
                    if total > 0:
                        percent = (downloaded / total) * 100
                        progress_callback(video_id, percent, eta)
                elif d['status'] == 'finished':
                    progress_callback(video_id, 100, 0)
            
            ydl_opts['progress_hooks'] = [progress_hook]
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error downloading '{video_title}' ({video_id}): {e}")
        return False


def download_worker(video_info: VideoInfo, username: str, thread_id: int, 
                   completed: list, failed: list, lock: threading.Lock,
                   verbose: bool = True) -> None:
    """
    Worker function for multi-threaded downloads.
    
    Args:
        video_info: Video information dictionary
        username: Channel username
        thread_id: Thread identifier
        completed: List to track completed downloads
        failed: List to track failed downloads
        lock: Thread lock for safe list operations
        verbose: Print progress messages
    """
    video_title = video_info.get('title', 'Unknown')
    video_id = video_info['id']
    
    if verbose:
        print(f"\n🧵 Thread-{thread_id}: Starting download - {video_title[:50]}...")
    
    success = download_single_video(video_info, username)
    
    with lock:
        if success:
            completed.append(video_id)
            if verbose:
                print(f"✅ Thread-{thread_id}: Completed - {video_title[:50]}...")
        else:
            failed.append(video_id)
            if verbose:
                print(f"❌ Thread-{thread_id}: Failed - {video_title[:50]}...")


def download_queue_parallel(queue: list[VideoInfo], username: str, 
                           max_threads: int = 3, verbose: bool = True) -> dict:
    """
    Download videos from queue using multiple threads.
    
    Args:
        queue: List of videos to download
        username: Channel username for folder organization
        max_threads: Maximum number of parallel threads
        verbose: Print progress messages
        
    Returns:
        Dictionary with download statistics
    """
    if not queue:
        return {'completed': 0, 'failed': 0, 'total': 0}
    
    completed = []
    failed = []
    lock = threading.Lock()
    total_videos = len(queue)
    
    if verbose:
        print(f"\n🚀 Starting download with {max_threads} threads")
        print(f"📦 Total videos in queue: {total_videos}")
        print(f"👤 Channel: {username}")
        print("=" * 60)
    
    start_time = time.time()
    
    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {}
        
        # Submit all download tasks
        for idx, video_info in enumerate(queue):
            thread_id = idx % max_threads
            future = executor.submit(
                download_worker,
                video_info,
                username,
                thread_id,
                completed,
                failed,
                lock,
                verbose
            )
            futures[future] = video_info
        
        # Wait for all downloads to complete
        for future in as_completed(futures):
            # Exceptions will be raised here if any occurred
            try:
                future.result()
            except Exception as e:
                video_info = futures[future]
                print(f"\n❌ Download failed for {video_info['title']}: {e}")
                with lock:
                    failed.append(video_info['id'])
    
    elapsed_time = time.time() - start_time
    
    if verbose:
        print("\n" + "=" * 60)
        print("📊 DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"✅ Completed: {len(completed)}/{total_videos}")
        print(f"❌ Failed: {len(failed)}/{total_videos}")
        print(f"⏱️  Total time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        print(f"📈 Success rate: {(len(completed)/total_videos*100):.1f}%")
        print("=" * 60)
    
    return {
        'completed': len(completed),
        'failed': len(failed),
        'total': total_videos,
        'elapsed_time': elapsed_time,
        'success_rate': len(completed) / total_videos * 100 if total_videos > 0 else 0
    }


def resume_download_if_needed(queue: list[VideoInfo], username: str,
                             max_threads: int = 3, verbose: bool = True) -> dict:
    """
    Resume downloads that were interrupted or failed.
    Checks which videos are already downloaded and skips them.
    
    Args:
        queue: Original download queue
        username: Channel username
        max_threads: Maximum number of parallel threads
        verbose: Print progress messages
        
    Returns:
        Dictionary with download statistics
    """
    from download_scanner import check_video_exists
    
    # Filter out already downloaded videos
    remaining_queue = []
    skipped_count = 0
    
    for video_info in queue:
        video_id = video_info['id']
        video_type = video_info['type']
        
        if check_video_exists(video_id, username, video_type):
            if verbose:
                print(f"⏭️  Skipping (already exists): {video_info['title'][:50]}...")
            skipped_count += 1
        else:
            remaining_queue.append(video_info)
    
    if verbose:
        print(f"\n⏭️  Skipped {skipped_count} already downloaded videos")
        print(f"📥 Remaining to download: {len(remaining_queue)} videos\n")
    
    if not remaining_queue:
        print("✅ All videos are already downloaded!")
        return {'completed': 0, 'failed': 0, 'total': len(queue), 'skipped': skipped_count}
    
    # Download remaining videos
    result = download_queue_parallel(remaining_queue, username, max_threads, verbose)
    result['skipped'] = skipped_count
    
    return result


if __name__ == "__main__":
    # Test the module
    from channel_extractor import load_channel_info
    from download_scanner import scan_existing_downloads, create_download_queue
    
    username = input("Enter username (with or without @): ")
    channel_data = load_channel_info(username)
    
    if channel_data:
        clean_username = username[1:] if username.startswith('@') else username
        missing = scan_existing_downloads(clean_username, channel_data, verbose=True)
        queue = create_download_queue(missing)
        
        if queue:
            threads = int(input("\nEnter number of threads (default 3): ") or "3")
            download_queue_parallel(queue, clean_username, max_threads=threads)
        else:
            print("\n✅ All videos are already downloaded!")
    else:
        print("❌ Channel info not found. Please run channel_extractor first.")
