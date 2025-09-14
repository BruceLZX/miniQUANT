from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .schemas import ModelEvent


def log_dir() -> Path:
    p = Path.cwd() / "logs" / "model"
    p.mkdir(parents=True, exist_ok=True)
    return p


def events_path() -> Path:
    return log_dir() / "events.jsonl"


def append_event(event: ModelEvent) -> None:
    path = events_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")


def read_events(limit: int = 100) -> List[ModelEvent]:
    path = events_path()
    if not path.exists():
        return []
    # Simple approach: read all then slice from end
    lines = path.read_text(encoding="utf-8").splitlines()
    take = lines[-limit:] if limit > 0 else lines
    out: List[ModelEvent] = []
    for ln in take:
        try:
            obj = json.loads(ln)
            out.append(ModelEvent.model_validate(obj))
        except Exception:
            continue
    return list(reversed(out))  # latest first

