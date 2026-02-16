"""
数据收集模块 - 收集市场数据、新闻等
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.base_models import Evidence, MarketData, WhaleFlow
import aiohttp
import random
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import html
import re


class DataCollector:
    """数据收集器"""

    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

    # 仅用于行业关键词和 symbol->sector 的基础映射（可继续扩展）
    SECTOR_KEYWORDS = {
        "technology": "technology sector stocks",
        "semiconductor": "semiconductor sector stocks",
        "software": "software sector enterprise AI",
        "financial": "banking financial sector stocks",
        "energy": "energy oil gas sector stocks",
        "healthcare": "healthcare pharma biotech sector stocks",
        "consumer": "consumer discretionary retail sector stocks",
        "industrial": "industrial manufacturing logistics sector",
        "utilities": "utilities power grid sector stocks",
        "communication": "communication services media internet stocks",
        "materials": "materials chemicals mining sector stocks",
        "real_estate": "real estate reit sector stocks"
    }

    SYMBOL_SECTOR_HINTS = {
        "AAPL": "technology", "MSFT": "technology", "NVDA": "semiconductor", "AMD": "semiconductor",
        "AMZN": "consumer", "GOOGL": "communication", "META": "communication", "TSLA": "consumer",
        "JPM": "financial", "BAC": "financial", "GS": "financial", "XOM": "energy", "CVX": "energy",
        "LLY": "healthcare", "UNH": "healthcare", "JNJ": "healthcare", "PFE": "healthcare",
        "CAT": "industrial", "DE": "industrial", "NKE": "consumer", "WMT": "consumer",
        "PLTR": "software", "CRWD": "software", "SNOW": "software", "DDOG": "software",
        "AMAT": "semiconductor", "LRCX": "semiconductor", "ASML": "semiconductor", "QCOM": "semiconductor"
    }

    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, datetime] = {}

    async def collect_macro_news(self) -> List[Evidence]:
        """收集宏观新闻（真实 RSS）"""
        query_groups = [
            "Federal Reserve inflation interest rates when:7d",
            "US treasury yields macro economy when:7d",
            "crude oil dollar index macro risk when:7d",
        ]
        evidence: List[Evidence] = []

        for q in query_groups:
            rss_items = await self._fetch_google_news_rss(q, limit=4)
            for item in rss_items:
                evidence.append(Evidence(
                    content=item["title"],
                    timestamp=item["timestamp"],
                    source_id=item["source_id"],
                    reliability_score=item["reliability_score"],
                    summary=item["summary"],
                    metadata={
                        "query": q,
                        "source": item.get("source"),
                        "link": item.get("link")
                    }
                ))

        # 去重并限制条数
        uniq = {}
        for e in evidence:
            uniq[e.source_id] = e
        merged = sorted(uniq.values(), key=lambda x: x.timestamp, reverse=True)
        return merged[:12]

    async def collect_industry_news(self, sector: str) -> List[Evidence]:
        """收集行业新闻（真实 RSS）"""
        sector_key = (sector or "technology").lower().strip()
        q = self.SECTOR_KEYWORDS.get(sector_key, f"{sector_key} sector stocks")

        rss_items = await self._fetch_google_news_rss(f"{q} when:7d", limit=8)
        evidence = [
            Evidence(
                content=item["title"],
                timestamp=item["timestamp"],
                source_id=item["source_id"],
                reliability_score=item["reliability_score"],
                summary=item["summary"],
                metadata={"sector": sector_key, "source": item.get("source"), "link": item.get("link")}
            )
            for item in rss_items
        ]
        return evidence[:8]

    async def collect_stock_news(self, symbol: str) -> List[Evidence]:
        """收集股票新闻（真实 RSS）"""
        sym = (symbol or "").upper().strip()
        if not sym:
            return []
        q = f"{sym} stock earnings guidance regulation when:7d"
        rss_items = await self._fetch_google_news_rss(q, limit=10)

        evidence = [
            Evidence(
                content=item["title"],
                timestamp=item["timestamp"],
                source_id=item["source_id"],
                reliability_score=item["reliability_score"],
                summary=item["summary"],
                metadata={"symbol": sym, "source": item.get("source"), "link": item.get("link")}
            )
            for item in rss_items
        ]
        return evidence[:8]

    async def collect_sector_snapshot(self, sector: str) -> Optional[Evidence]:
        """行业快照（基于代表ETF/指数的当日行情）"""
        sector_to_symbol = {
            "technology": "XLK.US",
            "semiconductor": "SOXX.US",
            "software": "IGV.US",
            "financial": "XLF.US",
            "energy": "XLE.US",
            "healthcare": "XLV.US",
            "consumer": "XLY.US",
            "industrial": "XLI.US",
            "utilities": "XLU.US",
            "communication": "XLC.US",
            "materials": "XLB.US",
            "real_estate": "XLRE.US",
        }
        stooq_symbol = sector_to_symbol.get((sector or "").lower(), "XLK.US")
        quote = await self.get_stooq_quote(stooq_symbol)
        if not quote:
            return None

        close = quote.get("close")
        open_ = quote.get("open")
        if close is None or open_ is None or open_ == 0:
            return None
        chg_pct = (close - open_) / open_ * 100.0
        ts = quote.get("timestamp") or datetime.now()

        return Evidence(
            content=f"{stooq_symbol} 当日变动 {chg_pct:.2f}%，收盘 {close:.2f}，成交量 {quote.get('volume', 0):.0f}",
            timestamp=ts,
            source_id=f"stooq_{stooq_symbol}_{ts.strftime('%Y%m%d%H%M')}",
            reliability_score=0.88,
            summary=f"行业代表行情快照：{stooq_symbol} {chg_pct:.2f}%",
            metadata={"sector": sector, "stooq_symbol": stooq_symbol}
        )

    def infer_sector(self, symbol: str) -> str:
        """推断股票所属行业（轻量规则）"""
        sym = (symbol or "").upper().strip()
        if not sym:
            return "technology"
        if sym in self.SYMBOL_SECTOR_HINTS:
            return self.SYMBOL_SECTOR_HINTS[sym]
        if sym.endswith("BANK") or sym.startswith("BK"):
            return "financial"
        return "technology"

    async def get_market_data(self, symbol: str) -> MarketData:
        """获取市场数据（Stooq 优先）"""
        quote = await self.get_stooq_quote(f"{symbol.upper().replace('.', '-')}.US")
        if quote:
            price = float(quote.get("close") or quote.get("open") or 0.0)
            if price > 0:
                volume = float(quote.get("volume") or 0.0)
                return MarketData(
                    symbol=symbol,
                    timestamp=quote.get("timestamp") or datetime.now(),
                    price=price,
                    volume=volume,
                    vwap=price,
                    bid_price=price * 0.999,
                    ask_price=price * 1.001,
                    bid_size=max(10000.0, volume * 0.002 if volume > 0 else 10000.0),
                    ask_size=max(10000.0, volume * 0.002 if volume > 0 else 10000.0)
                )

        # 兜底模拟
        price = random.uniform(100, 200)
        return MarketData(
            symbol=symbol,
            timestamp=datetime.now(),
            price=price,
            volume=random.uniform(1000000, 10000000),
            vwap=price * random.uniform(0.99, 1.01),
            bid_price=price * 0.999,
            ask_price=price * 1.001,
            bid_size=random.uniform(10000, 50000),
            ask_size=random.uniform(10000, 50000)
        )

    async def get_whale_flow(self, symbol: str) -> WhaleFlow:
        """获取大额资金流数据（当前为估计）"""
        market_data = await self.get_market_data(symbol)
        adv = max(market_data.volume, 1_000_000.0)
        drift = random.uniform(-1, 1)
        return WhaleFlow(
            symbol=symbol,
            timestamp=datetime.now(),
            block_net_buy_value=drift * adv * 0.08,
            dark_pool_net=drift * adv * 0.03,
            options_whale_notional=abs(drift) * adv * 0.5,
            adv=adv
        )

    async def get_historical_prices(self, symbol: str, days: int = 30) -> List[float]:
        """获取历史价格（Stooq 日线）"""
        sym = f"{symbol.upper().replace('.', '-')}.US"
        url = f"https://stooq.com/q/d/l/?s={sym.lower()}&i=d"
        text = await self._fetch_text(url, ttl_seconds=900)
        if not text:
            base_price = random.uniform(100, 200)
            out = [base_price]
            for _ in range(max(1, days - 1)):
                out.append(max(1.0, out[-1] * (1 + random.uniform(-0.03, 0.03))))
            return out

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 2:
            return [random.uniform(100, 200)]

        closes: List[float] = []
        for ln in lines[1:]:
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) < 5:
                continue
            try:
                close = float(parts[4])
                if close > 0:
                    closes.append(close)
            except Exception:
                continue

        if not closes:
            return [random.uniform(100, 200)]
        return closes[-days:]

    async def get_stooq_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从 Stooq 获取单标的最新OHLCV"""
        sym = (symbol or "").strip().lower()
        if not sym:
            return None
        if "." not in sym:
            sym = f"{sym}.us"

        url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&h&e=csv"
        text = await self._fetch_text(url, ttl_seconds=60)
        if not text:
            return None

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 2:
            return None

        # 第一行是 header
        row = [p.strip() for p in lines[1].split(",")]
        if len(row) < 8:
            return None

        symbol_raw, date_s, time_s, open_s, high_s, low_s, close_s, vol_s = row[:8]
        if close_s in ("N/D", "-"):
            return None

        try:
            open_v = float(open_s)
            high_v = float(high_s)
            low_v = float(low_s)
            close_v = float(close_s)
            volume_v = float(vol_s) if vol_s not in ("", "N/D", "-") else 0.0
        except Exception:
            return None

        ts = datetime.now()
        try:
            if date_s and time_s:
                ts = datetime.strptime(f"{date_s} {time_s}", "%Y%m%d %H%M%S")
            elif date_s:
                ts = datetime.strptime(date_s, "%Y%m%d")
        except Exception:
            pass

        return {
            "symbol": symbol_raw,
            "timestamp": ts,
            "open": open_v,
            "high": high_v,
            "low": low_v,
            "close": close_v,
            "volume": volume_v,
        }

    async def _fetch_google_news_rss(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        q = query.strip().replace(" ", "+")
        url = f"{self.GOOGLE_NEWS_RSS}?q={q}&hl=en-US&gl=US&ceid=US:en"
        xml_text = await self._fetch_text(url, ttl_seconds=180)
        if not xml_text:
            return []

        items: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
            for node in root.findall("./channel/item")[:limit]:
                title_raw = (node.findtext("title") or "").strip()
                link = (node.findtext("link") or "").strip()
                pub = (node.findtext("pubDate") or "").strip()
                source_node = node.find("source")
                source = (source_node.text or "").strip() if source_node is not None else "Google News"

                title = self._clean_title(title_raw)
                if not title:
                    continue

                timestamp = datetime.now()
                try:
                    timestamp = parsedate_to_datetime(pub).replace(tzinfo=None)
                except Exception:
                    pass

                sid = f"google_news_{abs(hash((title, link, pub)))}"
                reliability = 0.78
                if source.lower() in {"reuters", "bloomberg.com", "the new york times", "wsj", "cnbc"}:
                    reliability = 0.90

                items.append({
                    "title": title,
                    "summary": title[:120],
                    "link": link,
                    "source": source,
                    "timestamp": timestamp,
                    "source_id": sid,
                    "reliability_score": reliability
                })
        except Exception:
            return []

        # 去重 + 时间排序
        uniq = {}
        for it in items:
            uniq[it["source_id"]] = it
        return sorted(uniq.values(), key=lambda x: x["timestamp"], reverse=True)

    async def _fetch_text(self, url: str, ttl_seconds: int = 60) -> Optional[str]:
        cached = self._get_from_cache(url)
        if cached is not None:
            return cached

        headers = {
            "User-Agent": "Mozilla/5.0 (MyQuantBot/1.0)",
            "Accept": "text/xml,application/xml,text/plain,*/*"
        }
        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    text = await resp.text()
                    self._save_to_cache(url, text, ttl_seconds=ttl_seconds)
                    return text
        except Exception:
            return None

    def _clean_title(self, text: str) -> str:
        t = html.unescape(text or "")
        t = re.sub(r"\s+", " ", t).strip()
        # Google News 常带 “ - Source” 尾缀
        if " - " in t and len(t.split(" - ")) > 1:
            left = t.rsplit(" - ", 1)[0].strip()
            if len(left) >= 12:
                t = left
        return t

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.cache_expiry.clear()

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if key in self.cache:
            if datetime.now() < self.cache_expiry.get(key, datetime.min):
                return self.cache[key]
        return None

    def _save_to_cache(self, key: str, value: Any, ttl_seconds: int = 300):
        """保存到缓存"""
        self.cache[key] = value
        self.cache_expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)
