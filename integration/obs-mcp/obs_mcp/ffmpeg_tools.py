#!/usr/bin/env python3
"""
ffmpeg post-processing tools for content pipeline.
Reads marks file, cuts video, assembles final output.
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from .server import mcp

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
OUTPUT_DIR = HEAVEN_DATA_DIR / "content_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _run_ffmpeg(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run ffmpeg command."""
    cmd = ["ffmpeg", "-y"] + args  # -y = overwrite output
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


@mcp.tool()
async def process_marks(video_path: str, marks_file: str) -> Dict[str, Any]:
    """
    Process video using marks file - cut into segments.

    Args:
        video_path: Path to the recorded video
        marks_file: Path to the marks JSON file

    Returns:
        Dict with segment paths and metadata
    """
    video = Path(video_path)
    if not video.exists():
        return {"error": f"Video not found: {video_path}"}

    marks_data = json.loads(Path(marks_file).read_text())
    marks = marks_data.get("marks", [])
    session = marks_data.get("session", "unknown")

    if len(marks) < 2:
        return {"error": "Need at least 2 marks (start + end)"}

    # Create segments directory
    segments_dir = OUTPUT_DIR / f"segments_{session}"
    segments_dir.mkdir(parents=True, exist_ok=True)

    segments = []
    good_segments = []

    # Cut video at each mark
    for i in range(len(marks) - 1):
        start_mark = marks[i]
        end_mark = marks[i + 1]

        start_t = start_mark["t"]
        end_t = end_mark["t"]
        duration = end_t - start_t
        label = end_mark.get("label", "unknown")

        segment_path = segments_dir / f"segment_{i:03d}_{label}.mp4"

        # ffmpeg cut
        _run_ffmpeg([
            "-i", str(video),
            "-ss", str(start_t),
            "-t", str(duration),
            "-c", "copy",  # fast copy, no re-encode
            str(segment_path)
        ])

        segment_info = {
            "index": i,
            "path": str(segment_path),
            "start": start_t,
            "end": end_t,
            "duration": duration,
            "label": label
        }
        segments.append(segment_info)

        if label == "good":
            good_segments.append(segment_info)

    return {
        "session": session,
        "segments_dir": str(segments_dir),
        "total_segments": len(segments),
        "good_segments": len(good_segments),
        "segments": segments,
        "good_segment_paths": [s["path"] for s in good_segments]
    }


@mcp.tool()
async def assemble_video(
    segment_paths: List[str],
    output_name: str,
    intro_path: Optional[str] = None,
    outro_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Concatenate segments into final video.

    Args:
        segment_paths: List of video segment paths to concatenate
        output_name: Name for output file (without extension)
        intro_path: Optional intro video to prepend
        outro_path: Optional outro video to append

    Returns:
        Dict with output path
    """
    if not segment_paths:
        return {"error": "No segments provided"}

    # Build concat list
    all_paths = []
    if intro_path and Path(intro_path).exists():
        all_paths.append(intro_path)
    all_paths.extend(segment_paths)
    if outro_path and Path(outro_path).exists():
        all_paths.append(outro_path)

    # Create concat file
    concat_file = OUTPUT_DIR / f"concat_{output_name}.txt"
    with open(concat_file, "w") as f:
        for path in all_paths:
            f.write(f"file '{path}'\n")

    output_path = OUTPUT_DIR / f"{output_name}.mp4"

    # ffmpeg concat
    _run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ])

    # Cleanup concat file
    concat_file.unlink()

    return {
        "output_path": str(output_path),
        "segments_used": len(all_paths),
        "has_intro": intro_path is not None,
        "has_outro": outro_path is not None
    }


@mcp.tool()
async def add_voiceover(
    video_path: str,
    audio_path: str,
    output_name: str,
    mix_original: bool = False,
    original_volume: float = 0.1
) -> Dict[str, Any]:
    """
    Add voiceover audio to video.

    Args:
        video_path: Path to input video
        audio_path: Path to voiceover audio
        output_name: Name for output file
        mix_original: If True, mix with original audio; if False, replace
        original_volume: Volume level for original audio if mixing (0.0-1.0)

    Returns:
        Dict with output path
    """
    video = Path(video_path)
    audio = Path(audio_path)

    if not video.exists():
        return {"error": f"Video not found: {video_path}"}
    if not audio.exists():
        return {"error": f"Audio not found: {audio_path}"}

    output_path = OUTPUT_DIR / f"{output_name}_voiced.mp4"

    if mix_original:
        # Mix voiceover with original audio
        _run_ffmpeg([
            "-i", str(video),
            "-i", str(audio),
            "-filter_complex",
            f"[0:a]volume={original_volume}[a0];[1:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=longest",
            "-c:v", "copy",
            str(output_path)
        ])
    else:
        # Replace audio entirely
        _run_ffmpeg([
            "-i", str(video),
            "-i", str(audio),
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path)
        ])

    return {
        "output_path": str(output_path),
        "mixed_original": mix_original
    }


@mcp.tool()
async def full_pipeline(
    video_path: str,
    marks_file: str,
    output_name: str,
    voiceover_path: Optional[str] = None,
    intro_path: Optional[str] = None,
    outro_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run full post-processing pipeline: marks → segments → assemble → voiceover.

    Args:
        video_path: Path to recorded video
        marks_file: Path to marks JSON
        output_name: Name for final output
        voiceover_path: Optional voiceover audio
        intro_path: Optional intro video
        outro_path: Optional outro video

    Returns:
        Dict with final output path and pipeline stats
    """
    # Step 1: Process marks → segments
    segments_result = await process_marks(video_path, marks_file)
    if "error" in segments_result:
        return segments_result

    good_paths = segments_result["good_segment_paths"]
    if not good_paths:
        return {"error": "No good segments found"}

    # Step 2: Assemble
    assemble_result = await assemble_video(
        good_paths,
        f"{output_name}_assembled",
        intro_path,
        outro_path
    )
    if "error" in assemble_result:
        return assemble_result

    assembled_path = assemble_result["output_path"]

    # Step 3: Voiceover (if provided)
    if voiceover_path and Path(voiceover_path).exists():
        voice_result = await add_voiceover(
            assembled_path,
            voiceover_path,
            output_name,
            mix_original=True,
            original_volume=0.1
        )
        if "error" in voice_result:
            return voice_result
        final_path = voice_result["output_path"]
    else:
        final_path = assembled_path

    return {
        "final_output": final_path,
        "segments_processed": segments_result["total_segments"],
        "good_segments_used": segments_result["good_segments"],
        "has_voiceover": voiceover_path is not None
    }
