#!/usr/bin/env python3
"""
OMNISANC Daemon - Long-running process that handles hook requests via unix socket.

Start: python3 daemon.py start
Stop: python3 daemon.py stop
Status: python3 daemon.py status

The daemon loads all heavy imports once, then handles hook requests instantly.
"""
import socket
import os
import sys
import json
import signal
import traceback
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/omnisanc.sock"
PID_FILE = "/tmp/omnisanc_daemon.pid"

def write_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def read_pid():
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, 'r') as f:
            content = f.read().strip()
            if not content.isdigit():
                return None
            return int(content)
    except (IOError, OSError) as e:
        logger.debug(f"Could not read PID file: {e}\n{traceback.format_exc()}")
        return None

def is_running():
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        # Process doesn't exist - expected case
        logger.debug(f"Process {pid} not found")
        return False
    except PermissionError as e:
        # Process exists but we can't signal it
        logger.debug(f"Permission denied for PID {pid}: {e}\n{traceback.format_exc()}")
        return True

def stop_daemon():
    pid = read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Stopped daemon (PID {pid})")
        except ProcessLookupError:
            logger.info("Daemon already stopped")
        except PermissionError as e:
            logger.error(f"Cannot stop daemon: {e}\n{traceback.format_exc()}")
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

def handle_request(data: dict) -> dict:
    """Process a hook request and return response."""
    try:
        from strata_unwrap import get_actual_tool_name, get_actual_tool_input
        from omnisanc_logic import on_tool_use, on_tool_result

        tool_name = get_actual_tool_name(data)
        arguments = get_actual_tool_input(data)

        # Detect PostToolUse: prefer hook_event_name, fallback to field presence
        is_post = data.get("hook_event_name") == "PostToolUse" or "tool_response" in data or "tool_result" in data

        if is_post:
            # PostToolUse - accept both field names (Claude Code uses tool_response)
            tool_result = data.get("tool_response") or data.get("tool_result")
            raw_tool_name = data.get("tool_name", "")
            post_result = on_tool_result(tool_name, arguments, tool_result, raw_tool_name=raw_tool_name)
            response = {"hook_type": "post", "success": True}
            if isinstance(post_result, dict) and post_result.get("narration"):
                response["narration"] = post_result["narration"]
            return response
        else:
            # PreToolUse - may block
            result = on_tool_use(tool_name, arguments)
            return {
                "hook_type": "pre",
                "allowed": result.get("allowed", True),
                "error_message": result.get("error_message", ""),
                "reason": result.get("reason", "")
            }
    except Exception as e:
        return {
            "hook_type": "unknown",
            "allowed": True,
            "error_message": "",
            "reason": f"daemon_error: {e}",
            "traceback": traceback.format_exc()
        }

def run_server():
    """Main server loop."""
    # Clean up old socket
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    write_pid()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(10)

    # Allow all users to connect
    os.chmod(SOCKET_PATH, 0o777)

    logger.info(f"OMNISANC Daemon running (PID {os.getpid()})")
    logger.info("Loading heavy imports...")

    # Pre-load imports so first request is fast
    try:
        from strata_unwrap import get_actual_tool_name, get_actual_tool_input
        from omnisanc_logic import on_tool_use, on_tool_result
        logger.info("Imports loaded, ready for requests")
    except Exception as e:
        logger.warning(f"Import error (will retry on request): {e}\n{traceback.format_exc()}")

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        try:
            conn, _ = server.accept()
            conn.settimeout(10.0)

            # Recv loop for full message (large tool responses exceed 64KB)
            chunks = []
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks).decode()
            if data:
                request = json.loads(data)
                response = handle_request(request)
                conn.sendall(json.dumps(response).encode())

            conn.close()
        except Exception as e:
            logger.error(f"Request error: {e}\n{traceback.format_exc()}")

def main():
    if len(sys.argv) < 2:
        logger.error("Usage: daemon.py [start|stop|status]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        if is_running():
            logger.info("Daemon already running")
            sys.exit(0)
        run_server()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "status":
        if is_running():
            logger.info(f"Daemon running (PID {read_pid()})")
        else:
            logger.info("Daemon not running")
    else:
        logger.error(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
