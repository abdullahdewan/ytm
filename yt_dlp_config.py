"""
Centralized configuration for yt-dlp.
Handles YouTube authentication (cookies) from environment variables.
"""

import os
import yt_dlp
from pathlib import Path
from dotenv import load_dotenv

def load_config():
    """Load environment variables from .env file in the project root."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        # Fallback to default search if .env not in same dir
        load_dotenv()

def get_youtube_cookie_opts() -> dict:
    """
    Load YouTube authentication options from .env file.
    
    Returns:
        Dictionary with yt-dlp cookie options
    """
    load_config()
    
    ydl_opts = {}
    
    # Determine the target cookie file path (always set this so yt-dlp saves updated cookies back to it)
    cookie_file_env = os.getenv('YOUTUBE_COOKIE_FILE', 'cookies.txt')
    cookie_path = Path(__file__).parent / cookie_file_env if not os.path.isabs(cookie_file_env) else Path(cookie_file_env)
    
    ydl_opts['cookiefile'] = str(cookie_path)
    
    # Check if file exists, if not we will fall back to extracting from browser
    # and yt-dlp will save them into the cookiefile automatically.
    if not cookie_path.exists():
        # Option 2: Cookie string
        cookie_string = os.getenv('YOUTUBE_COOKIE')
        if cookie_string:
            ydl_opts['cookies'] = cookie_string
        else:
            # Option 3: Browser cookies
            browser = os.getenv('YOUTUBE_BROWSER')
            if browser:
                ydl_opts['cookiesfrombrowser'] = (browser,)

    return ydl_opts

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
