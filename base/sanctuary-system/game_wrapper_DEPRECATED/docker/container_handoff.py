#!/usr/bin/env python3
"""
Container Handoff Server

Runs inside each agent container.
- Receives commands from orchestrator
- Executes bash/python
- Reports state back to orchestrator
- Checks inbox and injects into Claude context

Spawned by container entrypoint.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration from environment
# ============================================================================

AGENT_ID = os.environ.get("AGENT_ID", "unknown")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://host.docker.internal:8420")
INBOX_DIR = Path(os.environ.get("INBOX_DIR", "/shared/inboxes/unknown"))
HANDOFF_PORT = int(os.environ.get("HANDOFF_PORT", "8421"))
PERSONA = os.environ.get("PERSONA")

# ============================================================================
# Models
# ============================================================================

class ExecuteRequest(BaseModel):
    """Code execution request."""
    code: str
    language: str = "python"  # python or bash
    timeout: int = 60


class ExecuteResponse(BaseModel):
    """Code execution response."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class SendMessageRequest(BaseModel):
    """Request to send message to another agent."""
    to_agent: str
    content: str
    message_type: str = "default"
    priority: int = 5
    metadata: dict = {}


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title=f"PAIA Agent Handoff - {AGENT_ID}",
    description="Container-side handoff server for agent execution",
    version="0.1.0"
)


@app.on_event("startup")
async def startup():
    """Report ready to orchestrator."""
    await report_state("running")
    logger.info(f"Agent {AGENT_ID} handoff server ready on port {HANDOFF_PORT}")


@app.on_event("shutdown")
async def shutdown():
    """Report shutdown to orchestrator."""
    await report_state("stopped")


# ============================================================================
# State Reporting
# ============================================================================

async def report_state(status: str, task: str | None = None):
    """Report state back to orchestrator."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{ORCHESTRATOR_URL}/callback/state",
                params={"agent_id": AGENT_ID, "status": status, "task": task},
                timeout=5.0
            )
    except httpx.RequestError as e:
        logger.warning(f"Failed to report state: {e}")


# ============================================================================
# Code Execution
# ============================================================================

@app.post("/execute")
async def execute(request: ExecuteRequest) -> ExecuteResponse:
    """Execute code in this container."""
    start = datetime.now()

    try:
        if request.language == "python":
            result = subprocess.run(
                [sys.executable, "-c", request.code],
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd="/agent"
            )
        elif request.language == "bash":
            result = subprocess.run(
                ["bash", "-c", request.code],
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd="/agent"
            )
        else:
            raise HTTPException(400, f"Unsupported language: {request.language}")

        duration = int((datetime.now() - start).total_seconds() * 1000)

        return ExecuteResponse(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            duration_ms=duration
        )

    except subprocess.TimeoutExpired:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        return ExecuteResponse(
            success=False,
            stdout="",
            stderr=f"Execution timed out after {request.timeout}s",
            exit_code=-1,
            duration_ms=duration
        )


# ============================================================================
# Inbox Management
# ============================================================================

@app.get("/inbox")
async def get_inbox() -> list[dict]:
    """Get pending messages in inbox."""
    if not INBOX_DIR.exists():
        return []

    messages = []
    for msg_file in sorted(INBOX_DIR.glob("*.json")):
        try:
            messages.append(json.loads(msg_file.read_text()))
        except json.JSONDecodeError:
            logger.warning(f"Invalid message file: {msg_file}")

    return messages


@app.get("/inbox/count")
async def inbox_count() -> dict:
    """Get inbox message count."""
    if not INBOX_DIR.exists():
        return {"count": 0}
    return {"count": len(list(INBOX_DIR.glob("*.json")))}


@app.delete("/inbox/{message_id}")
async def ack_message(message_id: str) -> dict:
    """Acknowledge (delete) a message."""
    msg_file = INBOX_DIR / f"{message_id}.json"
    if msg_file.exists():
        msg_file.unlink()
        return {"acknowledged": True}
    raise HTTPException(404, "Message not found")


@app.get("/inbox/pop")
async def pop_message() -> dict | None:
    """Pop oldest message from inbox (read and delete)."""
    if not INBOX_DIR.exists():
        return None

    files = sorted(INBOX_DIR.glob("*.json"))
    if not files:
        return None

    msg_file = files[0]
    try:
        message = json.loads(msg_file.read_text())
        msg_file.unlink()
        return message
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to pop message: {e}")
        return None


# ============================================================================
# Send Messages (to other agents via orchestrator)
# ============================================================================

@app.post("/send")
async def send_message(request: SendMessageRequest) -> dict:
    """Send message to another agent via orchestrator."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ORCHESTRATOR_URL}/messages/send",
                json={
                    "from_agent": AGENT_ID,
                    "to_agent": request.to_agent,
                    "content": request.content,
                    "message_type": request.message_type,
                    "priority": request.priority,
                    "metadata": request.metadata,
                },
                timeout=10.0
            )
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(500, f"Failed to send message: {e}")


# ============================================================================
# Claude Integration Helpers
# ============================================================================

@app.get("/inject/pending")
async def get_pending_injections() -> list[dict]:
    """Get messages formatted for Claude context injection."""
    messages = await get_inbox()

    # Format for PAIA injection hook
    injections = []
    for msg in messages:
        injections.append({
            "source": "world",
            "event": f"message_from_{msg['from']}",
            "message": msg["content"],
            "priority": msg.get("priority", 5),
            "metadata": {
                "message_id": msg["id"],
                "from_agent": msg["from"],
                "type": msg.get("type", "default"),
            }
        })

    return injections


@app.post("/claude/start")
async def start_claude(prompt: str | None = None) -> dict:
    """Start Claude CLI in this container."""
    cmd = ["claude"]
    if prompt:
        cmd.extend(["--prompt", prompt])

    try:
        # Start claude as background process
        process = subprocess.Popen(
            cmd,
            cwd="/agent",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        await report_state("running", "claude_active")
        return {"status": "started", "pid": process.pid}
    except FileNotFoundError:
        raise HTTPException(500, "Claude CLI not found in container")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "agent_id": AGENT_ID,
        "status": "healthy",
        "inbox_count": len(list(INBOX_DIR.glob("*.json"))) if INBOX_DIR.exists() else 0,
        "persona": PERSONA,
    }


# ============================================================================
# Interrupt (Send Esc to Claude)
# ============================================================================

@app.post("/interrupt")
async def interrupt(double: bool = False) -> dict:
    """Send Esc key to Claude via tmux (cancel current operation)."""
    try:
        subprocess.run(["tmux", "send-keys", "-t", "claude", "Escape"], check=True)
        if double:
            await asyncio.sleep(0.05)
            subprocess.run(["tmux", "send-keys", "-t", "claude", "Escape"], check=True)
        return {"sent": "Escape", "double": double, "agent_id": AGENT_ID}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Failed to send Esc: {e}")


@app.post("/exit")
async def exit_claude() -> dict:
    """Type /exit to gracefully exit Claude."""
    try:
        subprocess.run(["tmux", "send-keys", "-t", "claude", "/exit", "Enter"], check=True)
        return {"sent": "/exit", "agent_id": AGENT_ID}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Failed to send /exit: {e}")


@app.post("/force_exit")
async def force_exit_claude() -> dict:
    """Send Ctrl+C to force exit Claude."""
    try:
        subprocess.run(["tmux", "send-keys", "-t", "claude", "C-c"], check=True)
        return {"sent": "C-c", "agent_id": AGENT_ID}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Failed to send C-c: {e}")


@app.post("/kill_agent_process")
async def kill_agent_process() -> dict:
    """Kill the claude process but keep container/tmux alive."""
    try:
        # Find claude PIDs using ps + grep (pkill may not be available)
        ps_result = subprocess.run(
            ["sh", "-c", "ps aux | grep '[c]laude' | awk '{print $2}'"],
            capture_output=True, text=True
        )
        pids = ps_result.stdout.strip().split('\n')
        pids = [p for p in pids if p]

        if not pids:
            return {"killed": None, "message": "No claude process found", "agent_id": AGENT_ID}

        for pid in pids:
            subprocess.run(["kill", "-9", pid], capture_output=True)

        return {"killed": pids, "agent_id": AGENT_ID}
    except Exception as e:
        raise HTTPException(500, f"Failed to kill process: {e}")


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Run the handoff server."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=HANDOFF_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
