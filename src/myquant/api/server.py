from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover
    yf = None  # type: ignore

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

from myquant.execution.paper_broker import OrderSide, OrderType, PaperBroker
from myquant.model.schemas import ModelEvent, ModelEventType, ModelStatusView
from myquant.model.events import append_event, read_events
from myquant.model.monitor import summarize_status


def create_app() -> FastAPI:
    app = FastAPI(title="MyQuant API", version="0.1.0")

    # CORS: 开发期允许所有来源；上线请收紧
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api")

    # ---------------- Models ----------------
    class BarsResponse(BaseModel):
        symbol: str
        freq: str
        rows: List[Dict[str, Any]]

    class LastPriceResponse(BaseModel):
        symbol: str
        price: Optional[float]
        ts: Optional[str]

    class PositionModel(BaseModel):
        symbol: str
        qty: float
        avg_price: float

    class OrderModel(BaseModel):
        id: int
        ts: str
        symbol: str
        side: OrderSide
        qty: float
        order_type: OrderType
        price: Optional[float] = None
        status: str
        fill_price: Optional[float] = None

    class OrderRequest(BaseModel):
        symbol: str = Field(..., description="Ticker symbol")
        side: OrderSide
        qty: float = Field(..., gt=0)
        type: OrderType = Field(..., alias="type")
        price: Optional[float] = Field(None, gt=0)

        class Config:
            populate_by_name = True

    class AccountModel(BaseModel):
        equity: float
        cash: float
        positions_value: float
        positions: List[PositionModel]
        ts: str

    class ModelStatusResponse(ModelStatusView):
        pass

    class ModelEventsResponse(BaseModel):
        events: List[ModelEvent]

    # ---------------- State ----------------
    broker = PaperBroker()

    # ---------------- Helpers ----------------
    def _fetch_market_data(symbol: str, start: date, end: date, freq: str = "1d") -> pd.DataFrame:
        symbol = symbol.upper().strip()
        if yf is not None:
            try:
                df = yf.download(symbol, start=start, end=end, interval=freq, auto_adjust=False, progress=False)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df = df.rename(columns={c: c.title() for c in df.columns})
                    df = df.reset_index().rename(columns={"Date": "Date"})
                    return df
            except Exception:
                pass

        # Fallback synthetic data
        rng = pd.date_range(start, end, freq="B")
        if len(rng) == 0:
            return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])  # empty
        # ensure numpy
        import random
        seed = int.from_bytes(symbol.encode(), "little") % (2**32 - 1)
        if np is not None:
            rs = np.random.RandomState(seed)
            price = 100 + rs.randn(len(rng)).cumsum() * 0.8
            op = price + rs.randn(len(rng)) * 0.3
            hi = (op if isinstance(op, float) else op.copy())
            lo = (op if isinstance(op, float) else op.copy())
            hi = pd.Series(hi)  # type: ignore
            lo = pd.Series(lo)  # type: ignore
            hi = pd.Series(pd.concat([hi, pd.Series(price)], axis=1).max(axis=1))
            lo = pd.Series(pd.concat([lo, pd.Series(price)], axis=1).min(axis=1))
            hi = (hi + abs(pd.Series(rs.randn(len(rng))) * 0.5)).values
            lo = (lo - abs(pd.Series(rs.randn(len(rng))) * 0.5)).values
            vol = (rs.rand(len(rng)) * 1e6).astype(int)
        else:
            random.seed(seed)
            price = []
            p = 100.0
            for _ in range(len(rng)):
                p += random.gauss(0, 0.8)
                price.append(p)
            op = [v + random.gauss(0, 0.3) for v in price]
            hi = [max(o, c) + abs(random.gauss(0, 0.5)) for o, c in zip(op, price)]
            lo = [min(o, c) - abs(random.gauss(0, 0.5)) for o, c in zip(op, price)]
            vol = [int(random.random() * 1e6) for _ in range(len(rng))]
        df = pd.DataFrame({
            "Date": rng,
            "Open": op,
            "High": hi,
            "Low": lo,
            "Close": price,
            "Volume": vol,
        })
        return df

    @api.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "ts": datetime.now(timezone.utc).isoformat(),
            "service": "myquant-api",
        }

    @api.get("/market/bars", response_model=BarsResponse)
    def market_bars(
        symbol: str = Query(..., description="Ticker symbol"),
        start: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
        end: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
        freq: str = Query("1d", pattern="^(1d|1h|30m)$"),
    ) -> BarsResponse:
        try:
            d_end = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
            d_start = datetime.strptime(start, "%Y-%m-%d").date() if start else d_end - timedelta(days=180)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid date: {e}")

        df = _fetch_market_data(symbol, d_start, d_end, freq=freq)
        rows: List[Dict[str, Any]] = []
        if not df.empty:
            for _, r in df.iterrows():
                rows.append({
                    "ts": (r["Date"].isoformat() if hasattr(r["Date"], "isoformat") else str(r["Date"])),
                    "o": float(r["Open"]),
                    "h": float(r["High"]),
                    "l": float(r["Low"]),
                    "c": float(r["Close"]),
                    "v": float(r.get("Volume", 0)),
                })
        return BarsResponse(symbol=symbol.upper(), freq=freq, rows=rows)

    @api.get("/market/last", response_model=LastPriceResponse)
    def market_last(symbol: str = Query(...)) -> LastPriceResponse:
        d_end = date.today()
        d_start = d_end - timedelta(days=7)
        df = _fetch_market_data(symbol, d_start, d_end, freq="1d")
        if df.empty:
            return LastPriceResponse(symbol=symbol.upper(), price=None, ts=None)
        last = df.iloc[-1]
        ts = last["Date"].isoformat() if hasattr(last["Date"], "isoformat") else str(last["Date"])
        return LastPriceResponse(symbol=symbol.upper(), price=float(last["Close"]), ts=ts)

    @api.get("/positions", response_model=List[PositionModel])
    def positions() -> List[PositionModel]:
        return [
            PositionModel(symbol=p.symbol, qty=p.qty, avg_price=p.avg_price)
            for p in broker.get_positions()
        ]

    @api.get("/orders", response_model=List[OrderModel])
    def orders(limit: int = Query(50, ge=1, le=500)) -> List[OrderModel]:
        return [OrderModel(**o.__dict__) for o in broker.get_orders(limit=limit)]

    @api.get("/account", response_model=AccountModel)
    def account() -> AccountModel:
        # Minimal account summary for Phase A
        poss = broker.get_positions()
        positions_value = 0.0
        for p in poss:
            lp = market_last(p.symbol).price
            if lp is not None:
                positions_value += p.qty * lp
        cash = 0.0  # Phase A: cash not tracked yet
        equity = cash + positions_value
        return AccountModel(
            equity=equity,
            cash=cash,
            positions_value=positions_value,
            positions=[PositionModel(symbol=p.symbol, qty=p.qty, avg_price=p.avg_price) for p in poss],
            ts=datetime.now(timezone.utc).isoformat(),
        )

    @api.post("/orders", response_model=OrderModel)
    def create_order(req: OrderRequest) -> OrderModel:
        symbol = req.symbol.upper().strip()
        last = market_last(symbol)
        order = broker.place_order(
            symbol=symbol,
            side=req.side,
            qty=req.qty,
            order_type=req.type,
            price=req.price,
            last_price=last.price,
        )
        return OrderModel(**order.__dict__)

    # ---------------- Model monitor ----------------
    @api.get("/model/status", response_model=ModelStatusResponse)
    def model_status() -> ModelStatusResponse:
        return ModelStatusResponse(**summarize_status().model_dump())

    @api.get("/model/events", response_model=ModelEventsResponse)
    def model_events(limit: int = Query(100, ge=1, le=1000)) -> ModelEventsResponse:
        evts = read_events(limit=limit)
        return ModelEventsResponse(events=evts)

    app.include_router(api)
    return app


app = create_app()

# Seed demo model events if none exist (startup hook)
try:
    if not read_events(limit=1):
        now = datetime.now(timezone.utc).isoformat()
        append_event(ModelEvent(ts=now, type=ModelEventType.info, symbol="AAPL", reason="Model initialized"))
        append_event(ModelEvent(ts=now, type=ModelEventType.signal, symbol="AAPL", signal="HOLD", score=0.52, reason="Warmup"))
except Exception:
    pass

# 运行命令（开发）：
# uvicorn myquant.api.server:app --reload --port 8000
