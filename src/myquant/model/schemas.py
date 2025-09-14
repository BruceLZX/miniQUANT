from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelStatus(str, Enum):
    idle = "idle"
    running = "running"
    error = "error"


class ModelEventType(str, Enum):
    signal = "signal"
    order = "order"
    risk = "risk"
    info = "info"
    error = "error"


class ModelEvent(BaseModel):
    ts: str
    type: ModelEventType
    symbol: Optional[str] = None
    signal: Optional[str] = Field(None, description="e.g., BUY/SELL/HOLD or label")
    score: Optional[float] = Field(None, description="signal score or confidence [0,1]")
    reason: Optional[str] = None
    order_id: Optional[int] = None
    risk_flags: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class ModelStatusView(BaseModel):
    status: ModelStatus
    last_run: Optional[str] = None
    watch_symbol: Optional[str] = None
    latency_sec: Optional[float] = None
    last_signal: Optional[str] = None
    last_error: Optional[str] = None
    version: Optional[str] = None

