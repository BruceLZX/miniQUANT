from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .events import read_events
from .schemas import ModelEvent, ModelEventType, ModelStatus, ModelStatusView


def summarize_status() -> ModelStatusView:
    evts = read_events(limit=1)
    if not evts:
        return ModelStatusView(status=ModelStatus.idle, version="0.1.0")
    last: ModelEvent = evts[0]
    status = ModelStatus.running if last.type != ModelEventType.error else ModelStatus.error
    last_run = last.ts
    last_signal = last.signal
    last_error = last.reason if last.type == ModelEventType.error else None
    # naive latency: now - last.ts
    latency_sec: Optional[float] = None
    try:
        t = datetime.fromisoformat(last.ts.replace("Z", "+00:00"))
        latency_sec = (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        pass
    return ModelStatusView(
        status=status,
        last_run=last_run,
        watch_symbol=last.symbol,
        latency_sec=latency_sec,
        last_signal=last_signal,
        last_error=last_error,
        version="0.1.0",
    )

