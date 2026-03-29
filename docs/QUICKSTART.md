# 🚀 QUICK START GUIDE

## Installation (One-time)

```bash
# Make sure yt-dlp is installed
pip install yt-dlp
```

## Running the System

### Option 1: Interactive Mode (Recommended)

```bash
python app.py
```

The app will guide you through:
1. Enter channel URL or username
2. Choose action (rescan/download)
3. Set thread count
4. Automatic download

### Option 2: Test First

```bash
# Verify everything works
python test_system.py
```

## Example Session

```
$ python app.py

============================================================
🎬 YOUTUBE CHANNEL VIDEO DOWNLOADER
============================================================

Enter YouTube Channel URL or Username (with or without @)
Examples:
  - https://www.youtube.com/@ElainaAly
  - @ElainaAly
  - ElainaAly

➡️  Your input: @ElainaAly

✅ Channel info found for: @elainaaly

What would you like to do?
  [R] Rescan channel info (update JSON file)
  [D] Download videos
  [Q] Quit

➡️  Your choice (R/D/Q): D

🔍 Scanning for already downloaded videos...

📊 Scanning videos...
📊 Scanning shorts...
📊 Scanning streams...

📋 Download Status:
   • Videos: 50/100 downloaded (50 pending)
   • Shorts: 10/20 downloaded (10 pending)
   • Streams: 0/5 downloaded (5 pending)

💾 Total to download: 65 videos

📥 Ready to download 65 videos

Enter number of parallel threads (default: 3): 

============================================================
🚀 STARTING DOWNLOADS
============================================================
...
```

## Common Commands

| Task | Command |
|------|---------|
| Start download | `python app.py` |
| Test system | `python test_system.py` |
| Extract channel only | `python channel_extractor.py` |
| Scan downloads | `python download_scanner.py` |
| Download only | `python video_downloader.py` |

## Folder Structure Created

```
resources/
├── channels_info/       # Auto-created
│   └── elainaaly.json   # Channel metadata
└── downloads/          # Auto-created
    └── elainaaly/
        ├── videos/     # Regular videos
        ├── shorts/     # Short videos
        └── streams/    # Live streams
```

## Tips

1. **First run**: Takes longer to scan the channel
2. **Subsequent runs**: Much faster, only downloads new videos
3. **Thread count**: 3-5 is optimal for most users
4. **Rescan**: Use when new videos are uploaded
5. **Interrupted?**: Just run again, it resumes automatically

## Troubleshooting

**Problem**: yt-dlp not found  
**Solution**: `pip install yt-dlp`

**Problem**: Channel not found  
**Solution**: Check URL/username spelling

**Problem**: Download fails  
**Solution**: Video might be private/deleted, skip and continue

## Next Steps

1. Run `python test_system.py` to verify setup
2. Run `python app.py` to start downloading
3. Check `downloads/` folder for videos
4. Read `README_DOWNLOADER.md` for advanced features

---

**Need Help?**  
Check `README_DOWNLOADER.md` for detailed documentation.
