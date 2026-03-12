#!/usr/bin/env python3
"""
OMNISANC Router - Thin client that routes hook requests to the daemon.

Auto-starts daemon if not running and kill switch is not set.
"""
import socket
import subprocess
import sys
import json
import os
import time
import logging

# Set up minimal logging to stderr for debugging
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("OMNISANC_DEBUG") else logging.WARNING,
    format="[omnisanc_router] %(levelname)s: %(message)s",
    stream=sys.stderr
)

SOCKET_PATH = "/tmp/omnisanc.sock"
KILL_SWITCH_FILE = "/tmp/heaven_data/omnisanc_core/.omnisanc_disabled"
DAEMON_PATH = "/home/GOD/omnisanc_core_daemon/daemon.py"
PID_FILE = "/tmp/omnisanc_daemon.pid"


def is_daemon_running():
    """Check if daemon process is alive."""
    if not os.path.exists(PID_FILE):
        logging.debug("PID file does not exist")
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        logging.debug(f"Daemon running with PID {pid}")
        return True
    except (OSError, ValueError, FileNotFoundError):
        logging.debug("Daemon not running", exc_info=True)
        return False


def start_daemon():
    """Start the daemon process and wait for socket."""
    subprocess.Popen(
        ["python3", DAEMON_PATH, "start"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    # Wait for socket to appear (max 10 seconds)
    for _ in range(100):
        if os.path.exists(SOCKET_PATH):
            return True
        time.sleep(0.1)
    return False


def send_to_daemon(hook_data: dict) -> dict:
    """Send hook data to daemon and return response."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(SOCKET_PATH)
    sock.send(json.dumps(hook_data).encode())
    response_data = sock.recv(65536).decode()
    sock.close()
    return json.loads(response_data)


def handle_pre_response(response: dict):
    """Handle PreToolUse response - may block."""
    if not response.get("allowed", True):
        error_msg = response.get("error_message", "OMNISANC blocked tool")
        sys.stderr.write(f"🚫 {error_msg}\n")
        sys.exit(2)
    reason = response.get("reason", "")
    if reason:
        sys.stderr.write(f"✅ {reason}\n")
    sys.exit(0)


def main():
    # Fast path: kill switch = pass through
    if os.path.exists(KILL_SWITCH_FILE):
        sys.exit(0)

    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_data = {}

    # Auto-start daemon if not running
    if not os.path.exists(SOCKET_PATH) and not is_daemon_running():
        sys.stderr.write("🚀 Starting OMNISANC daemon...\n")
        if not start_daemon():
            sys.stderr.write("⚠️ Failed to start daemon, passing through\n")
            sys.exit(0)

    try:
        response = send_to_daemon(hook_data)
        if response.get("hook_type") == "pre":
            handle_pre_response(response)
        sys.exit(0)
    except (FileNotFoundError, ConnectionRefusedError, json.JSONDecodeError):
        # Daemon not running or bad response = pass through
        sys.exit(0)
    except socket.timeout:
        sys.stderr.write("⚠️ OMNISANC daemon timeout\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
