from __future__ import annotations

import json
import os
from pathlib import Path

from yatzy.models import AppState

DATA_FILE = "yatzy_state.json"


def data_dir() -> Path:
    configured = os.environ.get("FLET_APP_STORAGE_DATA")
    if configured:
        path = Path(configured)
    else:
        path = Path.home() / ".yatzy"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_path() -> Path:
    return data_dir() / DATA_FILE


def load_state() -> AppState:
    path = state_path()
    if not path.exists():
        return AppState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppState()
    if not isinstance(payload, dict):
        return AppState()
    return AppState.from_dict(payload)


def save_state(state: AppState) -> None:
    path = state_path()
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
