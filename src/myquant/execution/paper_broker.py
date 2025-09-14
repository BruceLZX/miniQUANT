from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class Order:
    id: int
    ts: str
    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType
    price: Optional[float] = None
    status: str = "FILLED"  # SIMPLE: immediate fill
    fill_price: Optional[float] = None


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float


class PaperBroker:
    """Very simple file-backed paper broker for demo/UI.

    - Immediate fill at provided price (LIMIT) or last price (MARKET).
    - Maintains positions with average price.
    - Stores state in JSON file under `data/paper_trading_state.json`.
    """

    def __init__(self, state_path: Optional[Path] = None) -> None:
        base = Path.cwd()
        data_dir = base / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = state_path or (data_dir / "paper_trading_state.json")
        self._state = {
            "orders": [],
            "positions": {},  # symbol -> {qty, avg_price}
            "next_order_id": 1,
        }
        self._load()

    # ---------- State IO ----------
    def _load(self) -> None:
        if self.state_path.exists():
            try:
                self._state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                # Corrupt or empty file; keep defaults
                pass

    def _save(self) -> None:
        self.state_path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- Public API ----------
    def get_positions(self) -> List[Position]:
        return [
            Position(symbol=sym, qty=pos["qty"], avg_price=pos["avg_price"])  # type: ignore
            for sym, pos in self._state["positions"].items()
        ]

    def get_orders(self, limit: int = 50) -> List[Order]:
        orders = [Order(**o) for o in self._state.get("orders", [])]
        return list(reversed(orders))[:limit]

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        order_type: OrderType,
        price: Optional[float] = None,
        last_price: Optional[float] = None,
    ) -> Order:
        assert qty > 0, "qty must be > 0"

        order_id = int(self._state.get("next_order_id", 1))
        self._state["next_order_id"] = order_id + 1

        # Immediate fill logic
        fill_price = price if order_type == OrderType.LIMIT else last_price
        if fill_price is None:
            # As a fallback, require price; otherwise mark as REJECTED
            status = "REJECTED"
        else:
            status = "FILLED"
            self._apply_fill(symbol, side, qty, fill_price)

        order = Order(
            id=order_id,
            ts=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            symbol=symbol.upper(),
            side=side,
            qty=qty,
            order_type=order_type,
            price=price,
            status=status,
            fill_price=fill_price,
        )
        self._state.setdefault("orders", []).append(asdict(order))
        self._save()
        return order

    def cancel_order(self, order_id: int) -> bool:
        # Immediate-fill demo has nothing pending; keep API for compatibility
        return False

    # ---------- Internal ----------
    def _apply_fill(self, symbol: str, side: OrderSide, qty: float, price: float) -> None:
        sym = symbol.upper()
        pos = self._state["positions"].get(sym)
        if pos is None:
            pos = {"qty": 0.0, "avg_price": 0.0}

        if side == OrderSide.BUY:
            new_qty = pos["qty"] + qty
            new_avg = (
                (pos["avg_price"] * pos["qty"] + price * qty) / new_qty
                if new_qty > 0
                else price
            )
            pos["qty"], pos["avg_price"] = new_qty, new_avg
        else:  # SELL
            new_qty = pos["qty"] - qty
            if new_qty <= 1e-9:  # flat or negative -> close out
                pos = {"qty": 0.0, "avg_price": 0.0}
            else:
                pos["qty"] = new_qty
                # avg_price unchanged on sell

        if pos["qty"] <= 0:
            # remove flat positions
            self._state["positions"].pop(sym, None)
        else:
            self._state["positions"][sym] = pos

