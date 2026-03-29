# YouTube Channel Video Downloader

A comprehensive multi-threaded YouTube channel video downloader system with modular architecture.

## Features

✅ Extract channel information (videos, shorts, live streams)
✅ Save channel info to organized JSON files
✅ Scan existing downloads and identify missing videos
✅ Multi-threaded parallel downloads
✅ Resume interrupted downloads
✅ Organized folder structure by video type
✅ Skip already downloaded videos

## System Architecture

### Modules

1. **`channel_extractor.py`** - Extracts channel information from YouTube
   - Fetches all video metadata
   - Categorizes videos into: videos, shorts, streams
   - Saves to `channels_info/username.json`

2. **`download_scanner.py`** - Scans existing downloads
   - Checks which videos are already downloaded
   - Creates download queue for missing videos
   - Tracks download progress

3. **`video_downloader.py`** - Multi-threaded download engine
   - Downloads videos in parallel using configurable threads
   - Saves to `downloads/username/videos|shorts|streams/id.ext`
   - Resumes failed/interrupted downloads

4. **`app.py`** - Main application orchestrator
   - User interface (CLI)
   - Coordinates all modules
   - Handles user choices

## Installation

Make sure you have the required dependencies:

```bash
pip install yt-dlp
```

## Usage

### Quick Start

Run the main application:

```bash
python app.py
```

The app will guide you through the process:

1. Enter YouTube channel URL or username (with or without @)
2. If channel info exists, choose to rescan or download
3. If new channel, it will scan and ask to download
4. Configure number of parallel threads (default: 3)
5. Downloads start automatically

### Input Examples

You can enter channel information in multiple formats:
- Full URL: `https://www.youtube.com/@ElainaAly`
- Username with @: `@ElainaAly`
- Username only: `ElainaAly`

### Workflow

#### First Time Download

1. Run `python app.py`
2. Enter channel URL/username
3. App scans the channel and saves info to `channels_info/`
4. App asks if you want to download now
5. Choose number of threads
6. Downloads begin

#### Subsequent Downloads

1. Run `python app.py`
2. Enter channel URL/username
3. App finds existing info file
4. Choose: **R**escan or **D**ownload
   - **Rescan**: Updates channel info, exits
   - **Download**: Scans for missing videos, downloads them

#### Rescan Option

Use rescan when:
- New videos have been uploaded
- You want to update video metadata
- Channel info needs refreshing

## Folder Structure

```
resources/
├── app.py                      # Main application
├── channel_extractor.py        # Channel info extraction
├── download_scanner.py         # Download scanning
├── video_downloader.py         # Video download engine
├── channels_info/              # Channel info JSON files
│   ├── ElainaAly.json
│   └── ...
└── downloads/                  # Downloaded videos
    └── username/
        ├── videos/             # Regular videos
        │   ├── VIDEO_ID.mp4
        │   └── ...
        ├── shorts/             # Short videos
        │   ├── SHORT_ID.mp4
        │   └── ...
        └── streams/            # Live streams
            ├── STREAM_ID.mp4
            └── ...
```

## Configuration

### Thread Count

- Default: 3 threads
- Minimum: 1 thread
- Maximum: 10 threads (recommended)
- More threads = faster downloads but more bandwidth/CPU usage

### Download Format

Videos are downloaded in best quality available:
- Best video + best audio merged
- Output format: MP4
- Filename: `VIDEO_ID.mp4`

## Advanced Usage

### Using Modules Directly

You can use individual modules in your own scripts:

```python
from channel_extractor import scan_and_save_channel, load_channel_info
from download_scanner import scan_existing_downloads, create_download_queue
from video_downloader import download_queue_parallel

# Extract channel info
result = scan_and_save_channel("https://www.youtube.com/@ElainaAly")
username, channel_data = result

# Scan for missing videos
missing = scan_existing_downloads(username, channel_data)

# Create download queue
queue = create_download_queue(missing)

# Download with 5 threads
download_queue_parallel(queue, username, max_threads=5)
```

### Custom Download Paths

Modify `get_downloads_dir()` in modules to change download location.

## Troubleshooting

### Common Issues

**"Failed to extract channel info"**
- Check if URL/username is correct
- Ensure internet connection
- Try again (temporary network issue)

**"Channel info not found"**
- Run app first time to scan channel
- Or choose rescan option

**Download fails**
- Check internet connection
- Video might be private/deleted
- Retry failed downloads when prompted

**Slow downloads**
- Increase thread count (up to 10)
- Check internet speed
- Reduce quality settings in code

### Dependencies

Required packages:
- `yt-dlp` - YouTube downloader library
- Python 3.12+

Install: `pip install yt-dlp`

## Tips

1. **First run takes longer** - Channel info extraction may take time for large channels
2. **Use 3-5 threads** - Good balance between speed and resource usage
3. **Resume downloads** - Interrupted downloads can be resumed safely
4. **Check disk space** - Videos take significant storage space
5. **Organized folders** - Each video type has separate folder for easy management

## File Naming

Videos are saved by their YouTube ID:
- Format: `VIDEO_ID.mp4`
- Example: `dQw4w9WgXcQ.mp4`

This ensures:
- No duplicate filenames
- Easy to track downloaded videos
- Consistent naming across platforms

## License & Credits

Built with yt-dlp library.
For educational purposes only.
Please respect YouTube's Terms of Service.
