import os
import sys
import subprocess
import telebot
from pathlib import Path

from telegram_uploader import load_telegram_config

# Load configuration
config = load_telegram_config()
BOT_TOKEN = config.get('bot_token')
ADMIN_IDS = config.get('admin_ids', [])

if not BOT_TOKEN:
    print("❌ Bot token is missing in telegram_config.json")
    sys.exit(1)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Helper function to check admin
def is_admin(user_id):
    if not ADMIN_IDS:
        return True # If no admins configured, allow anyone
    return user_id in ADMIN_IDS

def restricted(func):
    """Decorator to restrict command access to admins only."""
    def wrapper(message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "⛔ You are not authorized to use this bot.")
            return
        return func(message, *args, **kwargs)
    return wrapper

def run_ytm_command(cmd_args):
    """Run a ytm.py command and return its output."""
    try:
        base_cmd = [sys.executable, str(Path(__file__).parent / 'ytm.py')]
        full_cmd = base_cmd + cmd_args
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=30 # Prevent hanging
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing command: {e}"

@bot.message_handler(commands=['start', 'help'])
@restricted
def send_welcome(message):
    help_text = (
        "🎬 *YTM Telegram Manager*\n\n"
        "Manage your YouTube Downloader via Telegram:\n\n"
        "🟢 *Control Commands:*\n"
        "`/download <username>` - Start download task\n"
        "`/upload <username>` - Start upload task\n"
        "`/upload_all <username>` - Start upload all task\n"
        "`/stop <name>` - Stop a running task\n"
        "`/restart <name>` - Restart a task\n"
        "`/delete <name>` - Delete a task from list\n"
        "`/clean [username]` - Clean uploaded files\n\n"
        "📊 *Status Commands:*\n"
        "`/status` - Show status of all tasks\n"
        "`/info <username>` - Show stats for a channel\n"
        "`/logs <name>` - View last 50 log lines\n\n"
        "🛠️ *Raw Command:*\n"
        "`/ytm <args>` - Run raw ytm.py command"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
@restricted
def handle_status(message):
    bot.reply_to(message, "⏳ Fetching status...")
    output = run_ytm_command(['status'])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['info'])
@restricted
def handle_info(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/info <username>`", parse_mode='Markdown')
        return
    bot.reply_to(message, f"⏳ Fetching info for {args[0]}...")
    output = run_ytm_command(['info', args[0]])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['download'])
@restricted
def handle_download(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/download <username>`", parse_mode='Markdown')
        return
    bot.reply_to(message, f"⏳ Starting download task for {args[0]}...")
    output = run_ytm_command(['start', 'download', args[0]])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['upload'])
@restricted
def handle_upload(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/upload <username>`", parse_mode='Markdown')
        return
    bot.reply_to(message, f"⏳ Starting upload task for {args[0]}...")
    output = run_ytm_command(['start', 'upload', args[0]])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['upload_all'])
@restricted
def handle_upload_all(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/upload_all <username>`", parse_mode='Markdown')
        return
    bot.reply_to(message, f"⏳ Starting upload all task for {args[0]}...")
    output = run_ytm_command(['start', 'upload', args[0], '--all'])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['logs'])
@restricted
def handle_logs(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/logs <name>`", parse_mode='Markdown')
        return
    bot.reply_to(message, f"⏳ Fetching logs for {args[0]}...")
    output = run_ytm_command(['logs', args[0], '-n', '20']) # limit to 20 lines for TG
    # Split output if too long
    if len(output) > 4000:
        output = "...[truncated]...\n" + output[-3900:]
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['stop'])
@restricted
def handle_stop(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/stop <name>`", parse_mode='Markdown')
        return
    output = run_ytm_command(['stop', args[0]])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['restart'])
@restricted
def handle_restart(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/restart <name>`", parse_mode='Markdown')
        return
    output = run_ytm_command(['restart', args[0]])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['delete'])
@restricted
def handle_delete(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/delete <name>`", parse_mode='Markdown')
        return
    output = run_ytm_command(['delete', args[0]])
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['clean'])
@restricted
def handle_clean(message):
    args = message.text.split()[1:]
    cmd = ['clean']
    if args:
        cmd.append(args[0])
    output = run_ytm_command(cmd)
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['ytm'])
@restricted
def handle_ytm_raw(message):
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "⚠️ Usage: `/ytm <args>`", parse_mode='Markdown')
        return
    output = run_ytm_command(args)
    if len(output) > 4000:
        output = "...[truncated]...\n" + output[-3900:]
    bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')

if __name__ == '__main__':
    print("🤖 Telegram Bot is running...")
    bot.infinity_polling()
