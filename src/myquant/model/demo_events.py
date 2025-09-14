from __future__ import annotations

import argparse
import random
import signal
import sys
import time
from datetime import datetime, timezone

from .events import append_event
from .schemas import ModelEvent, ModelEventType


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(symbol: str, interval: float, jitter: float, seed: int | None) -> None:
    rnd = random.Random(seed)
    print(f"[demo_events] writing events for {symbol} every ~{interval}s (jitter {jitter}s). Press Ctrl+C to stop.")

    def handle_sigint(signum, frame):  # type: ignore
        print("\n[demo_events] stopping...")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    # initial info
    append_event(ModelEvent(ts=now_iso(), type=ModelEventType.info, symbol=symbol, reason="demo runner started"))

    while True:
        # random signal HOLD/BUY/SELL with a score
        choice = rnd.choices(["BUY", "SELL", "HOLD"], weights=[0.35, 0.35, 0.30], k=1)[0]
        score = round(rnd.uniform(0.5, 0.95), 3)
        reason = rnd.choice([
            "momentum>threshold",
            "sentiment positive",
            "mean reversion",
            "risk reduced",
            "vol spike",
        ])
        append_event(
            ModelEvent(
                ts=now_iso(),
                type=ModelEventType.signal,
                symbol=symbol,
                signal=choice,
                score=score,
                reason=reason,
            )
        )

        # occasionally log a risk/info
        if rnd.random() < 0.15:
            append_event(
                ModelEvent(
                    ts=now_iso(),
                    type=ModelEventType.risk,
                    symbol=symbol,
                    reason=rnd.choice(["max position cap", "drawdown alert", "exposure limit"]),
                )
            )

        sleep_s = max(0.1, interval + rnd.uniform(-jitter, jitter))
        time.sleep(sleep_s)


def main() -> None:
    p = argparse.ArgumentParser(description="Demo generator for model events")
    p.add_argument("--symbol", default="AAPL", help="watch symbol, e.g., AAPL")
    p.add_argument("--interval", type=float, default=10.0, help="base interval seconds")
    p.add_argument("--jitter", type=float, default=2.0, help="random jitter seconds")
    p.add_argument("--seed", type=int, default=None, help="random seed")
    args = p.parse_args()
    run(args.symbol.upper(), args.interval, args.jitter, args.seed)


if __name__ == "__main__":
    main()

