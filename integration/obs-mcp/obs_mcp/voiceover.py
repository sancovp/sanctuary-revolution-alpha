#!/usr/bin/env python3
"""
ElevenLabs voiceover generation for content pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from .server import mcp

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
VOICEOVER_DIR = HEAVEN_DATA_DIR / "content_voiceover"
VOICEOVER_DIR.mkdir(parents=True, exist_ok=True)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Default voice - can be overridden
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel - clear female voice
DEFAULT_MODEL = "eleven_multilingual_v2"


@mcp.tool()
async def generate_voiceover(
    text: str,
    output_name: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate voiceover audio from text using ElevenLabs.

    Args:
        text: The script text to convert to speech
        output_name: Name for output file (without extension)
        voice_id: ElevenLabs voice ID (default: Rachel)
        model_id: Model to use (default: eleven_multilingual_v2)

    Returns:
        Dict with audio file path
    """
    if not ELEVENLABS_API_KEY:
        return {"error": "ELEVENLABS_API_KEY not set in environment"}

    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import save
    except ImportError:
        return {"error": "elevenlabs package not installed. Run: pip install elevenlabs"}

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    audio = client.text_to_speech.convert(
        voice_id=voice_id or DEFAULT_VOICE_ID,
        text=text,
        model_id=model_id or DEFAULT_MODEL,
        output_format="mp3_44100_128"
    )

    output_path = VOICEOVER_DIR / f"{output_name}.mp3"
    save(audio, str(output_path))

    return {
        "audio_path": str(output_path),
        "text_length": len(text),
        "voice_id": voice_id or DEFAULT_VOICE_ID,
        "model_id": model_id or DEFAULT_MODEL
    }


@mcp.tool()
async def list_voices() -> Dict[str, Any]:
    """
    List available ElevenLabs voices.

    Returns:
        Dict with available voices
    """
    if not ELEVENLABS_API_KEY:
        return {"error": "ELEVENLABS_API_KEY not set in environment"}

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        return {"error": "elevenlabs package not installed"}

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    voices = client.voices.get_all()

    return {
        "voices": [
            {"voice_id": v.voice_id, "name": v.name}
            for v in voices.voices
        ]
    }
