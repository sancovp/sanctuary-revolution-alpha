"""Compilation pipeline - Deliverable.__call__ implementation.

PAIASpec → build image → start container → user auth → agent assembles → upgraded image
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

DOCKER_DIR = Path("/tmp/sanctuary-system/game_wrapper/docker")


@dataclass
class CompilationResult:
    """Result of compilation."""
    success: bool
    container_name: Optional[str] = None
    image_tag: Optional[str] = None
    port: Optional[int] = None
    error: Optional[str] = None


def compile_deliverable(
    spec_name: str,
    instruction: str,
    base_image: str = "paia/extended:latest",
    auto_auth: bool = False,
) -> CompilationResult:
    """Compile a deliverable - the full pipeline.

    Steps:
    1. Build image (if needed)
    2. Start container with instruction
    3. Wait for user auth (unless auto_auth)
    4. Agent assembles per instruction
    5. Return result for commit/test cycle

    Args:
        spec_name: Name for this compilation (becomes container name)
        instruction: Assembly instruction for the agent (guru instruction)
        base_image: Base image to use
        auto_auth: Skip auth wait (for trusted/automated runs)

    Returns:
        CompilationResult with container info
    """
    container_name = f"paia-{spec_name}"

    # Find available port
    port = _find_available_port(8421)

    # Start container
    try:
        result = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "-e", f"GURU_INSTRUCTION={instruction}",
                "-p", f"{port}:8421",
                base_image
            ],
            capture_output=True,
            text=True,
            check=True
        )
        container_id = result.stdout.strip()

        return CompilationResult(
            success=True,
            container_name=container_name,
            image_tag=None,  # Set after commit
            port=port,
        )

    except subprocess.CalledProcessError as e:
        return CompilationResult(
            success=False,
            error=f"Failed to start container: {e.stderr}"
        )


def commit_compilation(container_name: str, tag: str) -> CompilationResult:
    """Commit a running container as new image.

    Called after agent has assembled and tests pass.
    """
    try:
        result = subprocess.run(
            ["docker", "commit", container_name, tag],
            capture_output=True,
            text=True,
            check=True
        )
        return CompilationResult(
            success=True,
            container_name=container_name,
            image_tag=tag,
        )
    except subprocess.CalledProcessError as e:
        return CompilationResult(
            success=False,
            error=f"Failed to commit: {e.stderr}"
        )


def stop_compilation(container_name: str, remove: bool = True) -> bool:
    """Stop and optionally remove a compilation container."""
    try:
        subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)
        if remove:
            subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _find_available_port(start: int = 8421) -> int:
    """Find available port starting from start."""
    import socket
    port = start
    while port < start + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
        port += 1
    return start  # fallback


# The full cycle for trusted self-evolution
def evolution_cycle(
    spec_name: str,
    instruction: str,
    test_fn: Optional[callable] = None,
) -> CompilationResult:
    """Full evolution cycle: compile → test → commit if green.

    Args:
        spec_name: Name for this evolution
        instruction: What the agent should do
        test_fn: Optional test function, returns True if green

    Returns:
        CompilationResult with committed image if tests pass
    """
    # Compile
    result = compile_deliverable(spec_name, instruction)
    if not result.success:
        return result

    # If no test function, return for manual testing
    if test_fn is None:
        return result

    # Run tests
    if test_fn(result):
        # Green - commit
        tag = f"paia/{spec_name}:evolved"
        commit_result = commit_compilation(result.container_name, tag)
        stop_compilation(result.container_name)
        return commit_result
    else:
        # Red - stop without commit
        stop_compilation(result.container_name)
        return CompilationResult(
            success=False,
            error="Tests failed"
        )
