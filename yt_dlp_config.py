"""
Centralized configuration for yt-dlp.
Handles YouTube authentication (cookies) from environment variables.
"""

import os
import yt_dlp
from dotenv import load_dotenv

def load_config():
    """Load environment variables."""
    load_dotenv()

def get_youtube_cookie_opts() -> dict:
    """
    Load YouTube authentication options from .env file.
    
    Returns:
        Dictionary with yt-dlp cookie options
    """
    load_config()
    
    ydl_opts = {}
    
    # Option 1: Cookie file path
    cookie_file = os.getenv('YOUTUBE_COOKIE_FILE')
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file
        # Note: We don't print here to keep logs clean for library usage
        return ydl_opts
    
    # Option 2: Cookie string
    cookie_string = os.getenv('YOUTUBE_COOKIE')
    if cookie_string:
        ydl_opts['cookies'] = cookie_string
        return ydl_opts
    
    # Option 3: Browser cookies
    browser = os.getenv('YOUTUBE_BROWSER')
    if browser:
        ydl_opts['cookiesfrombrowser'] = (browser,)
        return ydl_opts
    
    return {}

def get_common_ydl_opts(extra_opts: dict = None) -> dict:
    """
    Get common yt-dlp options with authentication.
    
    Args:
        extra_opts: Additional options to merge
        
    Returns:
        Consolidated yt-dlp options dictionary
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    
    # Add auth
    opts.update(get_youtube_cookie_opts())
    
    # Add extras
    if extra_opts:
        opts.update(extra_opts)
        
    return opts
