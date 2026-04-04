"""Sanctum MiniCLI — ritual management via Discord channel.

Commands:
    done <ritual>   — Complete a ritual
    status          — Show today's ritual status
    skip <ritual>   — Skip a ritual for today
    help            — Show available commands

Notifications:
    Ritual reminders, completions, streak milestones.

This is the first MiniCLI instance. The pattern is reusable for
any module that wants a Discord channel with commands.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from .mini_cli import MiniCLI
from .sanctum_source import SanctumRitualSource

logger = logging.getLogger(__name__)

HEAVEN_DATA = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
SANCTUM_CHANNEL_ID = None  # Set from discord_config.json


def _load_sanctum_channel_id() -> str:
    from .discord_config import load_discord_config
    cfg = load_discord_config()
    return cfg.get("sanctum_channel_id", "")


def _get_active_sanctum():
    config_path = HEAVEN_DATA / "sanctums" / "_config.json"
    if not config_path.exists():
        return None, None
    config = json.loads(config_path.read_text())
    name = config.get("current", "")
    if not name:
        return None, None
    sanctum_path = HEAVEN_DATA / "sanctums" / f"{name}.json"
    if not sanctum_path.exists():
        return name, None
    return name, json.loads(sanctum_path.read_text())


def _matches_today(frequency: str, day_name: str) -> bool:
    """Check if a ritual's frequency matches today."""
    freq = frequency.lower()
    if freq == "daily":
        return True
    if freq == day_name or freq == day_name[:3]:
        return True
    if freq.startswith("weekly:") and day_name in freq:
        return True
    return False


def _resolve_alias(name: str) -> str:
    """Resolve ritual aliases (reuses organ_daemon logic)."""
    from .organ_daemon import _resolve_ritual_alias
    return _resolve_ritual_alias(name)


def handle_done(argument: str) -> str:
    """Complete a ritual."""
    if not argument:
        return "Usage: done <ritual_name>"

    ritual_name = _resolve_alias(argument)
    sanctum_name, sanctum = _get_active_sanctum()
    if not sanctum:
        return "No active sanctum"

    # Find the ritual
    rituals = sanctum.get("rituals", [])
    ritual = next((r for r in rituals if r["name"] == ritual_name), None)
    if not ritual:
        available = [r["name"] for r in rituals if r.get("active", True)]
        return f"Ritual '{ritual_name}' not found. Available: {', '.join(available)}"

    # Check if already done today
    today = datetime.now().strftime("%Y-%m-%d")
    completions = ritual.get("completions", [])
    if any(c.get("date", "").startswith(today) for c in completions):
        return f"'{ritual_name}' already done today"

    # Add completion
    completions.append({"date": today, "timestamp": datetime.now().isoformat()})
    ritual["completions"] = completions

    # Save
    sanctum_path = HEAVEN_DATA / "sanctums" / f"{sanctum_name}.json"
    sanctum_path.write_text(json.dumps(sanctum, indent=2))

    # Count today's progress (filtered by frequency)
    day_name = datetime.now().strftime("%A").lower()
    todays_rituals = [r for r in rituals if r.get("active", True) and
                      _matches_today(r.get("frequency", "daily"), day_name)]
    done_today = sum(1 for r in todays_rituals if
                     any(c.get("date", "").startswith(today) for c in r.get("completions", [])))
    total = len(todays_rituals)

    return f"✓ {ritual_name} — {done_today}/{total} done today"


def handle_status(argument: str) -> str:
    """Show today's ritual status with scheduled times."""
    sanctum_name, sanctum = _get_active_sanctum()
    if not sanctum:
        return "No active sanctum"

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()
    day_name = now.strftime("%A").lower()  # "monday", "tuesday", etc

    # Filter by frequency — only show rituals that apply today
    all_rituals = [r for r in sanctum.get("rituals", []) if r.get("active", True)]
    rituals = []
    for r in all_rituals:
        freq = r.get("frequency", "daily").lower()
        if freq == "daily":
            rituals.append(r)
        elif freq == day_name or freq == day_name[:3]:  # "saturday" or "sat"
            rituals.append(r)
        elif freq.startswith("weekly:") and day_name in freq.lower():
            rituals.append(r)
        # Skip rituals whose frequency doesn't match today

    # Compute sequential schedule from morning anchor
    morning_time = "09:00"
    journal_config = HEAVEN_DATA / "sanctuary" / "journal_config.json"
    if journal_config.exists():
        try:
            jc = json.loads(journal_config.read_text())
            morning_time = jc.get("morning_time", "09:00")
        except Exception:
            pass

    h, m = map(int, morning_time.split(":"))
    current_time = now.replace(hour=h, minute=m, second=0, microsecond=0)

    done_count = 0
    lines = [f"**{sanctum_name}** — {now.strftime('%A %b %d')}"]
    lines.append("")

    for r in rituals:
        name = r["name"]
        duration = r.get("duration_minutes", 30)
        scheduled = current_time.strftime("%H:%M")
        completions = r.get("completions", [])
        is_done = any(c.get("date", "").startswith(today) for c in completions)
        is_skipped = any(c.get("date", "").startswith(today) and c.get("skipped") for c in completions)

        if is_skipped:
            lines.append(f"⏭ `{scheduled}` ~~{name}~~ *(skipped)*")
            done_count += 1
        elif is_done:
            lines.append(f"✅ `{scheduled}` **{name}**")
            done_count += 1
        elif now >= current_time:
            lines.append(f"🔴 `{scheduled}` {name} *(overdue)*")
        else:
            lines.append(f"⬜ `{scheduled}` {name}")

        current_time = current_time + timedelta(minutes=duration)

    lines.append("")
    lines.append(f"**{done_count}/{len(rituals)}** complete")

    return "\n".join(lines)


def handle_skip(argument: str) -> str:
    """Skip a ritual for today."""
    if not argument:
        return "Usage: skip <ritual_name>"
    ritual_name = _resolve_alias(argument)
    # Mark as skipped (completion with skip flag)
    sanctum_name, sanctum = _get_active_sanctum()
    if not sanctum:
        return "No active sanctum"

    ritual = next((r for r in sanctum.get("rituals", []) if r["name"] == ritual_name), None)
    if not ritual:
        return f"Ritual '{ritual_name}' not found"

    today = datetime.now().strftime("%Y-%m-%d")
    completions = ritual.get("completions", [])
    completions.append({"date": today, "timestamp": datetime.now().isoformat(), "skipped": True})
    ritual["completions"] = completions

    sanctum_path = HEAVEN_DATA / "sanctums" / f"{sanctum_name}.json"
    sanctum_path.write_text(json.dumps(sanctum, indent=2))

    return f"⏭ {ritual_name} skipped"


def create_sanctum_cli() -> MiniCLI:
    """Factory: create the sanctum MiniCLI from discord config."""
    channel_id = _load_sanctum_channel_id()
    if not channel_id:
        logger.warning("No sanctum_channel_id in discord_config.json — sanctum CLI disabled")
        return None

    cli = (MiniCLI.builder("sanctum", discord_id=channel_id)
           .command("done", handle_done, "Complete a ritual")
           .command("status", handle_status, "Show today's status")
           .command("skip", handle_skip, "Skip a ritual")
           .build())

    # Register help command that uses the CLI's own help_text
    cli.register_command("help", lambda _: cli.help_text(), "Show commands")

    logger.info("Sanctum MiniCLI created on channel %s", channel_id)
    return cli
