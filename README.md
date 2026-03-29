# YouTube Channel Downloader & Telegram Uploader

A Python tool to bulk-download YouTube channel videos using `yt-dlp` and upload them to a Telegram channel via a local Telegram Bot API server. Includes a **PM2-like CLI** (`ytm`) for running tasks in the background.

---

## Features

- 🎬 **Bulk Download** — Download all videos, shorts, and streams from a YouTube channel
- 📤 **Telegram Upload** — Upload downloaded videos to a Telegram channel with thumbnails
- ⚡ **Multi-threaded** — Parallel downloads with configurable thread count
- 🔄 **Resume Support** — Automatically skips already-downloaded or uploaded videos
- 🍪 **Cookie Authentication** — Bypass YouTube bot detection with cookie support
- 📋 **Upload Logging** — Track upload history and detailed Telegram API responses
- 🖥️ **Background Mode** — PM2-like process manager to run tasks in the background

---

## Project Structure

```
.
├── app.py                      # Interactive CLI application
├── ytm.py                      # PM2-like background process manager
├── worker.py                   # Non-interactive task runner (used by ytm.py)
├── channel_extractor.py        # YouTube channel info extraction
├── video_downloader.py         # Video download logic with yt-dlp
├── download_scanner.py         # Download/upload tracking and queue management
├── telegram_uploader.py        # Telegram upload via local Bot API
├── yt_dlp_config.py            # Centralized yt-dlp cookie configuration
├── docker-compose.yml          # Local Telegram Bot API server
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .env.template               # Minimal env template
├── telegram_config.json.example # Telegram bot configuration template
├── docs/                       # Additional documentation
└── logs/                       # Runtime logs (gitignored)
```

---

## Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (for the local Telegram Bot API server)
- A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- A **Telegram API ID & Hash** (from [my.telegram.org](https://my.telegram.org))

---

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd resources
```

### 2. Create a Virtual Environment

```bash
python3 -m venv dl_env
source dl_env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### Environment Variables (`.env`)

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required — Telegram Bot API server credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# Optional — YouTube authentication (prevents bot detection)
YOUTUBE_COOKIE_FILE=/path/to/cookies.txt
```

#### YouTube Cookie Methods

YouTube may block automated downloads with a "Sign in to confirm you're not a bot" error. To fix this, configure **one** of these methods in `.env`:

| Variable | Description |
|---|---|
| `YOUTUBE_COOKIE_FILE` | **(Recommended)** Path to a Netscape-format cookie file exported with a browser extension like [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) |
| `YOUTUBE_COOKIE` | Raw cookie string |
| `YOUTUBE_BROWSER` | Browser name (`chrome`, `firefox`, `edge`, `safari`, `opera`) to extract cookies automatically |

### Telegram Bot Configuration

Copy the example and fill in your bot details:

```bash
cp telegram_config.json.example telegram_config.json
```

Edit `telegram_config.json`:

```json
{
  "local_api_url": "http://localhost:8081",
  "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "channel_id": "-1001234567890"
}
```

| Field | Description |
|---|---|
| `local_api_url` | URL of the local Telegram Bot API server (default: `http://localhost:8081`) |
| `bot_token` | Your bot token from [@BotFather](https://t.me/BotFather) |
| `channel_id` | Target Telegram channel ID (use `-100` prefix for supergroups/channels) |

> **Note:** The bot must be an **admin** in the target channel with permission to post messages.

---

## Usage

### Step 1: Start the Telegram Bot API Server

```bash
docker compose up -d
```

This starts a local Telegram Bot API server on port `8081`, which is required for uploading large files (up to 2GB).

### Step 2: Run the Application

#### Interactive Mode

```bash
python app.py
```

Follow the prompts to:
1. Enter a YouTube channel URL or username
2. Scan the channel for videos
3. Download videos (multi-threaded)
4. Upload to Telegram

#### Background Mode (PM2-like)

Use `ytm.py` to run tasks in the background and free the terminal:

```bash
# Start a background download
python ytm.py start download <username> --threads 3

# Start a background upload
python ytm.py start upload <username>

# Upload all (including previously uploaded)
python ytm.py start upload <username> --all
```

##### Process Management

```bash
# Check status of all tasks
python ytm.py status

# View logs (last 50 lines)
python ytm.py logs <process-name>

# Follow logs live (like tail -f)
python ytm.py logs <process-name> --follow

# Stop a running task
python ytm.py stop <process-name>

# Remove a task from the list (and delete its log)
python ytm.py delete <process-name>
```

Process names follow the pattern `<type>-<username>`, for example:
- `download-elainaaly`
- `upload-elainaaly`

##### Example Session

```bash
$ python ytm.py start download ElainaAly
✅ Started 'download-elainaaly' (PID 12345)
   Log: logs/download-elainaaly.log

$ python ytm.py status
Name                           PID      Status     Type       Started
──────────────────────────────────────────────────────────────────────
download-elainaaly             12345    🟢 running  download   2026-03-29T15:02:47

$ python ytm.py logs download-elainaaly -f
📋 Following logs for 'download-elainaaly' (Ctrl+C to stop)...
📥 Starting download of 42 videos with 3 threads...
[Thread 1] Downloading: Video Title...
...
```

---

## Data & Logs

| Directory / File | Description |
|---|---|
| `downloads/` | Downloaded video files, organized by `<username>/<type>/` |
| `channels_info/` | Cached channel metadata JSON files |
| `logs/` | Runtime logs and upload tracking |
| `logs/<user>_upload_log.json` | Tracks which videos have been uploaded |
| `logs/<user>_telegram_responses.json` | Detailed Telegram API responses (message IDs, file IDs, etc.) |
| `logs/<process-name>.log` | Background task output logs |
| `server-data/` | Telegram Bot API server data |

---

## Troubleshooting

### "Sign in to confirm you're not a bot"

Configure YouTube cookies in `.env`. See the [Cookie Methods](#youtube-cookie-methods) section above.

### Upload fails with "Connection refused"

Make sure the local Telegram Bot API server is running:

```bash
docker compose up -d
```

### Large file upload fails

The local Telegram Bot API server supports files up to **2GB**. If uploads still fail, check:
1. Available disk space in `server-data/`
2. Network connectivity
3. Bot permissions in the target channel

---

## License

This project is for personal use. Please respect YouTube's Terms of Service and only download content you have the right to access.
