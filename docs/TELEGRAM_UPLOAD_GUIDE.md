# 📤 Telegram Upload Feature Guide

## Overview

The system now includes a complete Telegram upload feature that allows you to automatically upload downloaded YouTube videos to your Telegram channel.

## Features

✅ Upload downloaded videos to Telegram channel  
✅ Track uploaded videos (avoid re-uploading)  
✅ Resume interrupted uploads  
✅ Upload all or only new videos  
✅ Organized by video type (videos, shorts, streams)  
✅ Uses local Telegram Bot API server  

## Prerequisites

### 1. Local Telegram Bot API Server

You need to run a local Telegram Bot API server. This is required for uploading large files.

**Download and setup:**
```bash
# Clone Telegram Bot API server
git clone https://github.com/tdorgachev/telegram-bot-api.git
cd telegram-bot-api

# Build (requires C++ compiler)
cmake .
make

# Run the server
./telegram-bot-api --api-id YOUR_API_ID --api-hash YOUR_API_HASH
```

**Or use pre-built binaries** from: https://github.com/tdorgachev/telegram-bot-api/releases

**Get API ID and Hash:**
1. Go to https://my.telegram.org
2. Login with your phone number
3. Create a new application
4. Get `api_id` and `api_hash`

### 2. Create Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the bot token (e.g., `8720403014:AAEqXFNoSAPDIu5nDacVj4M5znODRtSP950`)

### 3. Add Bot to Channel

1. Create a Telegram channel (or use existing)
2. Add your bot as an **administrator** with full permissions
3. Get the channel ID:
   - For public channels: `@channelname`
   - For private channels: `-100xxxxxxxxx` (numeric ID)

## Configuration

### Step 1: Create Config File

Run this to create a sample config:
```bash
python telegram_uploader.py
```

This creates `telegram_config.json`:
```json
{
  "local_api_url": "http://localhost:8081",
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "channel_id": "YOUR_CHANNEL_ID_HERE"
}
```

### Step 2: Edit Config

Edit `telegram_config.json` with your credentials:

- **local_api_url**: URL of your local Telegram Bot API server (default: `http://localhost:8081`)
- **bot_token**: Your bot token from @BotFather
- **channel_id**: Your channel ID (e.g., `-1003778665734`)

## Usage

### Method 1: Through Main App (Recommended)

```bash
python app.py
```

1. Enter channel URL or username
2. Choose **[U]pload to Telegram**
3. Select upload option:
   - **[A]** Upload all downloaded videos
   - **[N]** Upload only new (not previously uploaded)
   - **[C]** Cancel
4. Confirm and start upload

### Method 2: Standalone Upload

```bash
python telegram_uploader.py
```

This tests connection and allows test upload.

## Workflow Integration

### Complete Download + Upload Flow

```bash
# Start the app
python app.py

# Enter channel
➡️  @ElainaAly

# Choose download
➡️  D

# Downloads complete
# Then asks: Do you want to upload to Telegram now?
➡️  Y

# Choose upload option
➡️  N  (upload only new videos)

# Upload starts...
```

### Upload Only (After Download)

```bash
python app.py
➡️  @ElainaAly

# Info file exists
➡️  U  (upload)

# Upload options appear
```

## Upload Options Explained

### [A] Upload All Videos
- Uploads ALL downloaded videos
- Ignores previous upload history
- Use for fresh start or re-upload

### [N] Upload Only New Videos
- Checks upload log (`{username}_upload_log.json`)
- Skips already uploaded videos
- **Recommended** for regular use

### Tracking Uploaded Videos

The system maintains `{username}_upload_log.json`:
```json
{
  "video_id_1": true,
  "video_id_2": true,
  "video_id_3": false  // failed upload
}
```

## File Organization

Uploaded videos are organized in Telegram channel by their original structure:

```
downloads/
└── elainaaly/
    ├── videos/      → Uploaded to channel
    ├── shorts/      → Uploaded to channel
    └── streams/     → Uploaded to channel
```

Each video is sent as:
- **Video file** (MP4/MKV/WebM)
- **Caption**: Video title
- **Streaming enabled**: Yes

## Troubleshooting

### "Cannot connect to Telegram API server"

**Solution:**
1. Make sure server is running: `./telegram-bot-api ...`
2. Check URL in config matches server address
3. Test with: `curl http://localhost:8081/bot<TOKEN>/getMe`

### "Bot is not admin in channel"

**Solution:**
1. Go to your channel
2. Channel settings → Administrators
3. Add your bot with full permissions
4. Ensure bot can post messages

### "File not found" during upload

**Solution:**
1. Verify video was downloaded completely
2. Check folder structure: `downloads/username/type/video_id.ext`
3. Re-download if missing

### Upload fails for large files

**Solution:**
1. Increase timeout in `telegram_uploader.py` (line 67)
2. Check disk space on server
3. Reduce concurrent uploads

### "Channel ID invalid"

**Solution:**
- Private channels: Must be numeric like `-1003778665734`
- Public channels: Can use `@channelname`
- Try forwarding a message from channel to @userinfobot to get ID

## Advanced Usage

### Manual Upload Queue

Use in your own scripts:

```python
from telegram_uploader import TelegramUploader, load_telegram_config
from channel_extractor import load_channel_info
from download_scanner import create_download_queue

# Load config
config = load_telegram_config()
uploader = TelegramUploader(config)

# Load channel data
channel_data = load_channel_info("elainaaly")

# Create queue
queue = create_download_queue(channel_data['videos'])

# Upload
result = uploader.upload_queue(queue, "elainaaly")
print(f"Uploaded: {result['uploaded']}")
```

### Custom Upload Logging

```python
from download_scanner import log_uploaded_video

# Log successful upload
log_uploaded_video("VIDEO_ID", "username", success=True)

# Log failed upload
log_uploaded_video("VIDEO_ID", "username", success=False)
```

### Batch Processing Multiple Channels

```python
channels = ["@ElainaAly", "@Channel2", "@Channel3"]

for channel in channels:
    print(f"Processing {channel}...")
    # Download first
    # Then upload
```

## Performance Tips

1. **Run server with cache**: 
   ```bash
   ./telegram-bot-api --api-id XXX --api-hash YYY --tmp /tmp/telegram
   ```

2. **Upload during off-peak hours**: Better bandwidth

3. **Batch uploads**: Download multiple channels, then upload in batches

4. **Monitor disk space**: Videos take significant storage

## Security Notes

⚠️ **Important:**
- Keep bot token secret
- Don't commit `telegram_config.json` to Git
- Use `.gitignore` for config files
- Bot should only have necessary permissions

## Best Practices

1. **Test first**: Upload 1-2 videos before bulk upload
2. **Check content**: Ensure videos comply with Telegram ToS
3. **Respect copyright**: Only upload content you have rights to
4. **Monitor uploads**: Watch for failed uploads and retry
5. **Backup logs**: Keep upload logs for tracking

## Example Session

```bash
$ python app.py

============================================================
🎬 YOUTUBE CHANNEL VIDEO DOWNLOADER
============================================================

Enter YouTube Channel URL or Username: @ElainaAly

✅ Channel info found for: @elainaaly

What would you like to do?
  [R] Rescan channel info
  [D] Download videos
  [U] Upload to Telegram
  [Q] Quit

➡️  U

📤 TELEGRAM UPLOAD
============================================================
Testing Telegram connection...
✅ Connected to Telegram bot: @MyUploadBot

📋 Upload Options:
  [A] Upload all videos
  [N] Upload only new videos
  [C] Cancel

➡️  N

📦 Found 45 videos to upload
Start upload? (Y/N): Y

============================================================
📤 TELEGRAM UPLOAD STARTED
============================================================
[UPLOADING] Video Title 1... (ID: abc123)
[SUCCESS] Uploaded: Video Title 1...
[UPLOADING] Video Title 2... (ID: def456)
[SUCCESS] Uploaded: Video Title 2...
...

============================================================
🎉 UPLOAD SESSION COMPLETE
============================================================
✅ Uploaded: 45 videos
❌ Failed: 0 videos
============================================================
```

## Integration with Existing upload.py

Your existing `upload.py` is still available and works independently. The new system:
- Is more integrated with downloader
- Tracks uploaded videos
- Offers better error handling
- Provides interactive options

Both can coexist! Use whichever suits your workflow.

---

**Need Help?**  
Check main documentation: `README_DOWNLOADER.md`
