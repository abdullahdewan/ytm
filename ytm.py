#!/usr/bin/env python3
"""
ytm — YouTube Manager: PM2-like process manager for download/upload tasks.

Usage:
    python ytm.py start download <username> [--threads N]
    python ytm.py start upload <username> [--all]
    python ytm.py status
    python ytm.py logs <name> [--lines N] [--follow]
    python ytm.py stop <name>
    python ytm.py restart <name>
    python ytm.py delete <name>
    python ytm.py clean [username]
"""

import os
import sys
import json
import signal
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


LOGS_DIR = Path(__file__).parent / 'logs'
PROCESS_FILE = LOGS_DIR / 'processes.json'


def load_processes() -> dict:
    """Load process registry."""
    LOGS_DIR.mkdir(exist_ok=True)
    if PROCESS_FILE.exists():
        with open(PROCESS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_processes(processes: dict) -> None:
    """Save process registry."""
    LOGS_DIR.mkdir(exist_ok=True)
    with open(PROCESS_FILE, 'w') as f:
        json.dump(processes, f, indent=2)


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def refresh_statuses(processes: dict) -> dict:
    """Update status of all processes based on actual PID state."""
    for name, info in processes.items():
        pid = info.get('pid')
        if info.get('status') == 'running' and pid:
            if not is_process_running(pid):
                info['status'] = 'stopped'
    return processes


# ─── Commands ────────────────────────────────────────────────────

def cmd_start(args) -> None:
    """Start a background task."""
    task_type = args.task_type
    username = args.username.lstrip('@').lower()
    name = f"{task_type}-{username}"

    processes = load_processes()

    # Check if already running
    if name in processes and processes[name].get('status') == 'running':
        pid = processes[name].get('pid')
        if is_process_running(pid):
            print(f"⚠️  Process '{name}' is already running (PID {pid})")
            return

    # Build worker command
    worker = Path(__file__).parent / 'worker.py'
    cmd = [sys.executable, str(worker), task_type, username]

    if task_type == 'download' and hasattr(args, 'threads'):
        cmd += ['--threads', str(args.threads)]
    if task_type == 'upload' and hasattr(args, 'upload_all') and args.upload_all:
        cmd += ['--all']

    # Open log file
    log_file = LOGS_DIR / f"{name}.log"
    LOGS_DIR.mkdir(exist_ok=True)

    with open(log_file, 'a') as lf:
        lf.write(f"\n{'='*60}\n")
        lf.write(f"[{datetime.now().isoformat()}] Starting {task_type} for {username}\n")
        lf.write(f"{'='*60}\n\n")

    log_fd = open(log_file, 'a')

    # Spawn detached process with unbuffered output
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'

    proc = subprocess.Popen(
        cmd,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        cwd=str(Path(__file__).parent),
        env=env,
    )

    # Register
    processes[name] = {
        'pid': proc.pid,
        'type': task_type,
        'username': username,
        'started_at': datetime.now().isoformat(),
        'status': 'running',
        'log_file': str(log_file),
    }
    save_processes(processes)

    print(f"✅ Started '{name}' (PID {proc.pid})")
    print(f"   Log: {log_file}")
    print(f"\n   View logs:  python ytm.py logs {name}")
    print(f"   Follow:     python ytm.py logs {name} --follow")
    print(f"   Stop:       python ytm.py stop {name}")


def cmd_status(args) -> None:
    """Show status of all managed processes."""
    processes = load_processes()
    processes = refresh_statuses(processes)
    save_processes(processes)

    if not processes:
        print("No managed processes.")
        return

    # Header
    print(f"\n{'Name':<30} {'PID':<8} {'Status':<10} {'Type':<10} {'Started':<20}")
    print("─" * 78)

    for name, info in processes.items():
        pid = info.get('pid', '?')
        status = info.get('status', '?')
        task_type = info.get('type', '?')
        started = info.get('started_at', '?')[:19]

        # Color status
        if status == 'running':
            status_str = f"🟢 {status}"
        elif status == 'stopped':
            status_str = f"🔴 {status}"
        else:
            status_str = f"⚪ {status}"

        print(f"{name:<30} {pid:<8} {status_str:<10} {task_type:<10} {started:<20}")

    print()


def cmd_logs(args) -> None:
    """Show or follow logs for a process."""
    name = args.name
    processes = load_processes()

    if name not in processes:
        print(f"❌ Process '{name}' not found.")
        print(f"   Available: {', '.join(processes.keys()) or 'none'}")
        return

    log_file = processes[name].get('log_file')
    if not log_file or not Path(log_file).exists():
        print(f"❌ Log file not found for '{name}'.")
        return

    if args.follow:
        # Use tail -f for live following
        print(f"📋 Following logs for '{name}' (Ctrl+C to stop)...\n")
        try:
            proc = subprocess.Popen(['tail', '-f', log_file])
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            print("\n")
    else:
        # Show last N lines
        lines = args.lines or 50
        print(f"📋 Last {lines} lines of '{name}':\n")
        try:
            result = subprocess.run(
                ['tail', '-n', str(lines), log_file],
                capture_output=True, text=True
            )
            print(result.stdout)
        except Exception as e:
            print(f"Error reading log: {e}")


def cmd_stop(args) -> None:
    """Stop a running process."""
    name = args.name
    processes = load_processes()

    if name not in processes:
        print(f"❌ Process '{name}' not found.")
        return

    pid = processes[name].get('pid')
    if not pid or not is_process_running(pid):
        processes[name]['status'] = 'stopped'
        save_processes(processes)
        print(f"ℹ️  Process '{name}' is not running.")
        return

    try:
        # Kill the process group (includes child processes)
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        processes[name]['status'] = 'stopped'
        save_processes(processes)
        print(f"🛑 Stopped '{name}' (PID {pid})")
    except ProcessLookupError:
        processes[name]['status'] = 'stopped'
        save_processes(processes)
        print(f"ℹ️  Process '{name}' already stopped.")
    except PermissionError:
        print(f"❌ Permission denied to stop PID {pid}.")


def cmd_restart(args) -> None:
    """Restart a managed process."""
    name = args.name
    processes = load_processes()

    if name not in processes:
        print(f"❌ Process '{name}' not found.")
        return

    info = processes[name]

    # Stop if running
    pid = info.get('pid')
    if pid and is_process_running(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            print(f"🛑 Stopped '{name}' (PID {pid})")
        except Exception:
            pass

    # Re-start using saved config
    task_type = info.get('type')
    username = info.get('username')

    # Build a fake args object
    class RestartArgs:
        pass
    restart_args = RestartArgs()
    restart_args.task_type = task_type
    restart_args.username = username
    restart_args.threads = 3
    restart_args.upload_all = False

    cmd_start(restart_args)


def cmd_delete(args) -> None:
    """Remove a process from the registry."""
    name = args.name
    processes = load_processes()

    if name not in processes:
        print(f"❌ Process '{name}' not found.")
        return

    # Stop if running
    pid = processes[name].get('pid')
    if pid and is_process_running(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            pass

    # Remove log file
    log_file = processes[name].get('log_file')
    if log_file and Path(log_file).exists():
        Path(log_file).unlink()

    del processes[name]
    save_processes(processes)
    print(f"🗑️  Deleted '{name}'")


def cmd_clean(args) -> None:
    """Delete uploaded video files to free disk space."""
    from download_scanner import clean_uploaded_files

    username = getattr(args, 'username', None)

    if username:
        username = username.lstrip('@').lower()
        print(f"🧹 Cleaning uploaded videos for '{username}'...\n")
    else:
        print("🧹 Cleaning uploaded videos for all channels...\n")

    result = clean_uploaded_files(username)

    print(f"\n{'='*60}")
    print(f"🧹 CLEANUP SUMMARY")
    print(f"{'='*60}")
    print(f"🗑️  Deleted: {result['deleted']} files")
    print(f"💾 Freed: {result['freed_bytes'] / (1024*1024):.1f} MB")
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    print(f"{'='*60}")


# ─── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog='ytm',
        description='YouTube Manager — PM2-like process manager',
    )
    subparsers = parser.add_subparsers(dest='command')

    # start
    start_parser = subparsers.add_parser('start', help='Start a background task')
    start_parser.add_argument('task_type', choices=['download', 'upload'], help='Task type')
    start_parser.add_argument('username', help='YouTube channel username')
    start_parser.add_argument('--threads', type=int, default=3, help='Download threads (default: 3)')
    start_parser.add_argument('--all', dest='upload_all', action='store_true', help='Upload all videos')
    start_parser.set_defaults(func=cmd_start)

    # status
    status_parser = subparsers.add_parser('status', help='Show status of all processes')
    status_parser.set_defaults(func=cmd_status)

    # logs
    logs_parser = subparsers.add_parser('logs', help='Show logs for a process')
    logs_parser.add_argument('name', help='Process name')
    logs_parser.add_argument('--lines', '-n', type=int, default=50, help='Number of lines (default: 50)')
    logs_parser.add_argument('--follow', '-f', action='store_true', help='Follow log output')
    logs_parser.set_defaults(func=cmd_logs)

    # stop
    stop_parser = subparsers.add_parser('stop', help='Stop a running process')
    stop_parser.add_argument('name', help='Process name')
    stop_parser.set_defaults(func=cmd_stop)

    # restart
    restart_parser = subparsers.add_parser('restart', help='Restart a managed process')
    restart_parser.add_argument('name', help='Process name')
    restart_parser.set_defaults(func=cmd_restart)

    # delete
    delete_parser = subparsers.add_parser('delete', help='Remove a process from the list')
    delete_parser.add_argument('name', help='Process name')
    delete_parser.set_defaults(func=cmd_delete)

    # clean
    clean_parser = subparsers.add_parser('clean', help='Delete uploaded video files to free space')
    clean_parser.add_argument('username', nargs='?', default=None, help='Channel username (optional, cleans all if omitted)')
    clean_parser.set_defaults(func=cmd_clean)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == '__main__':
    main()
