"""Storage operations for paia-builder."""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models import PAIA


def get_storage_dir(storage_dir: Optional[str] = None) -> Path:
    """Get storage directory, creating if needed."""
    path = Path(storage_dir or os.environ.get(
        "PAIA_STORAGE_DIR",
        os.path.join(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "paias")
    ))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path(storage_dir: Path) -> Path:
    return storage_dir / "_config.json"


def get_paia_path(storage_dir: Path, name: str) -> Path:
    return storage_dir / f"{name}.json"


def load_current_name(storage_dir: Path) -> Optional[str]:
    config_path = get_config_path(storage_dir)
    if config_path.exists():
        return json.loads(config_path.read_text()).get("current")
    return None


def save_current_name(storage_dir: Path, name: str) -> None:
    config_path = get_config_path(storage_dir)
    config_path.write_text(json.dumps({"current": name}))


def load_paia(storage_dir: Path, name: str) -> Optional[PAIA]:
    path = get_paia_path(storage_dir, name)
    if path.exists():
        return PAIA.model_validate_json(path.read_text())
    return None


def list_all_paias(storage_dir: Path) -> List[Dict[str, Any]]:
    paias = []
    for path in storage_dir.glob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            paia = PAIA.model_validate_json(path.read_text())
            paias.append({
                "name": paia.name,
                "level": paia.gear_state.level,
                "phase": paia.gear_state.phase.value,
                "points": paia.gear_state.total_points,
                "constructed": paia.gear_state.is_constructed
            })
        except Exception:
            continue
    return paias


def delete_paia(storage_dir: Path, name: str) -> bool:
    path = get_paia_path(storage_dir, name)
    if path.exists():
        path.unlink()
        return True
    return False
