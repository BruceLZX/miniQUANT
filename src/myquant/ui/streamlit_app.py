from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# Optional imports
try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover - optional
    yf = None  # type: ignore

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    go = None  # type: ignore

from myquant.execution.paper_broker import PaperBroker, OrderSide, OrderType


# ------------------------------- Helpers -------------------------------
def _seed_from_symbol(symbol: str) -> int:
    h = hashlib.sha256(symbol.encode()).hexdigest()
    return int(h[:8], 16)


def fetch_market_data(symbol: str, start: date, end: date, freq: str = "1d") -> pd.DataFrame:
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

    # Fallback: generate deterministic synthetic data for demo
    rng = pd.date_range(start, end, freq="B")
    if len(rng) == 0:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])  # empty
    import numpy as np

    rs = np.random.RandomState(_seed_from_symbol(symbol))
    price = 100 + rs.randn(len(rng)).cumsum() * 0.8
    op = price + rs.randn(len(rng)) * 0.3
    hi = np.maximum(op, price) + np.abs(rs.randn(len(rng))) * 0.5
    lo = np.minimum(op, price) - np.abs(rs.randn(len(rng))) * 0.5
    vol = (rs.rand(len(rng)) * 1e6).astype(int)
    df = pd.DataFrame({
        "Date": rng,
        "Open": op,
        "High": hi,
        "Low": lo,
        "Close": price,
        "Volume": vol,
    })
    return df


def load_news(symbol: str, since: date) -> pd.DataFrame:
    # Try load from data/news/news.csv with columns: ts, symbol, title, summary, sentiment
    news_path = Path.cwd() / "data" / "news" / "news_sample.csv"
    if news_path.exists():
        try:
            df = pd.read_csv(news_path)
            df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
            df = df[df["ts"] >= pd.Timestamp(since)]
            if symbol:
                df = df[(df["symbol"].str.upper() == symbol.upper()) | (df["symbol"].isna())]
            return df.sort_values("ts", ascending=False).head(50)
        except Exception:
            pass

    # Fallback sample
    return pd.DataFrame([
        {
            "ts": pd.Timestamp(datetime.utcnow()),
            "symbol": symbol.upper(),
            "title": f"Sample headline for {symbol.upper()}",
            "summary": "Demo news summary. Replace with crawler output.",
            "sentiment": 0.1,
        }
    ])


def plot_candles(df: pd.DataFrame, symbol: str):
    if go is None or df.empty:
        st.info("暂无可视化或数据为空。")
        return
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["Date"],
                open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=symbol
            )
        ]
    )
    fig.update_layout(
        title=f"{symbol} K线",
        xaxis_title="Date",
        yaxis_title="Price",
        height=520,
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def ensure_dirs():
    (Path.cwd() / "data").mkdir(exist_ok=True)
    (Path.cwd() / "data" / "news").mkdir(parents=True, exist_ok=True)


# ------------------------------- UI App -------------------------------
def main():
    st.set_page_config(page_title="MyQuant - 下单面板", layout="wide")
    ensure_dirs()

    st.title("MyQuant 可视化交易面板（纸上交易）")

    # Sidebar controls
    with st.sidebar:
        st.header("参数")
        watchlist = st.text_input("自选列表(逗号分隔)", value="AAPL,MSFT,TSLA,BABA,0700.HK").split(",")
        watchlist = [s.strip() for s in watchlist if s.strip()]
        default_symbol = watchlist[0] if watchlist else "AAPL"
        symbol = st.selectbox("标的", options=watchlist or [default_symbol], index=0)

        end_date = st.date_input("结束日期", value=date.today())
        start_date = st.date_input("开始日期", value=end_date - timedelta(days=180))
        freq = st.selectbox("频率", options=["1d", "1h", "30m"], index=0)

    # Load data
    df = fetch_market_data(symbol, start_date, end_date, freq=freq)
    last_row = df.iloc[-1] if not df.empty else None
    last_price = float(last_row["Close"]) if last_row is not None else None

    # Broker
    broker = PaperBroker()

    # Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"{symbol} 价格图表")
        if last_price is not None and len(df) > 1:
            prev_close = float(df.iloc[-2]["Close"])
            chg = last_price - prev_close
            pct = chg / prev_close * 100 if prev_close else 0
            st.metric("最新价", f"{last_price:.2f}", f"{chg:+.2f} ({pct:+.2f}%)")
        plot_candles(df, symbol)

        st.subheader("下单面板")
        with st.form("order_form", clear_on_submit=False):
            side = st.radio("方向", options=[OrderSide.BUY.value, OrderSide.SELL.value], horizontal=True)
            qty = st.number_input("数量", min_value=1.0, step=1.0, value=10.0)
            order_type = st.selectbox("订单类型", options=[OrderType.MARKET.value, OrderType.LIMIT.value])
            price: Optional[float] = None
            if order_type == OrderType.LIMIT.value:
                default_px = last_price or 0.0
                price = st.number_input("限价", min_value=0.0, step=0.01, value=float(default_px))
            submitted = st.form_submit_button("提交订单")

        if submitted:
            order = broker.place_order(
                symbol=symbol,
                side=OrderSide(side),
                qty=float(qty),
                order_type=OrderType(order_type),
                price=price,
                last_price=last_price,
            )
            if order.status == "FILLED":
                st.success(f"订单#{order.id} 已成交 @ {order.fill_price}")
            else:
                st.error("订单被拒绝：请检查价格或行情数据")

        st.subheader("当前持仓")
        positions = broker.get_positions()
        pos_df = pd.DataFrame([p.__dict__ for p in positions]) if positions else pd.DataFrame(columns=["symbol", "qty", "avg_price"])
        st.dataframe(pos_df, use_container_width=True, height=180)

        st.subheader("最近订单")
        orders = broker.get_orders(limit=100)
        ord_df = pd.DataFrame([o.__dict__ for o in orders]) if orders else pd.DataFrame(columns=["id", "ts", "symbol", "side", "qty", "order_type", "price", "status", "fill_price"])
        st.dataframe(ord_df, use_container_width=True, height=220)

    with col2:
        st.subheader("新闻与情绪（样例）")
        news_df = load_news(symbol, since=start_date)
        if not news_df.empty:
            for _, r in news_df.iterrows():
                st.markdown(f"- [{r.get('ts')}] {r.get('title')} | 情绪: {r.get('sentiment', 'NA')}")
                if r.get("summary"):
                    with st.expander("摘要"):
                        st.write(str(r.get("summary")))
        else:
            st.info("暂无新闻数据。稍后接入爬虫/AI 管线。")


if __name__ == "__main__":
    main()

