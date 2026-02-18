"""
D7 选股部门
"""
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
from models.base_models import StockCase
from memory.memory_store import MemoryManager
from data.data_collector import DataCollector
import asyncio
import math
import random


@dataclass
class StockCandidate:
    """股票候选"""
    symbol: str
    name: str
    horizon: str  # short/mid/long
    score: float
    macro_match: float
    industry_tailwind: float
    news_momentum: float
    whale_flow_heat: float
    risk_score: float
    why_now: str
    disqualifiers: List[str]


class D7StockSelectionDepartment:
    """D7 选股部 - 每天一次输出候选池（参考 D1/D2，不再只盯超大热门）"""

    def __init__(self, memory_manager: MemoryManager, agent_configs: Optional[Dict[str, Any]] = None):
        self.department_type = "D7"
        self.memory_manager = memory_manager
        self.collector = DataCollector()
        self.last_pool_source: str = "unknown"
        self._sector_map = self._build_sector_map()
        self._mega_hot = {
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B"
        }

    async def select_stocks(
        self,
        top_k: int = 12,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> List[StockCandidate]:
        """选股 - 输出候选池"""
        sector_bias, bias_meta = await self._build_theme_bias()
        candidate_pool = await self._get_candidate_pool(sector_bias)

        if not candidate_pool:
            self.last_pool_source = "fallback"
            return self._fallback_candidates(top_k)

        scored_candidates: List[StockCandidate] = []
        total = len(candidate_pool)
        for idx, candidate in enumerate(candidate_pool, 1):
            score = await self._score_candidate(candidate, sector_bias)
            candidate.score = score
            scored_candidates.append(candidate)
            if progress_cb:
                progress_cb(idx, total, candidate.symbol)
            await asyncio.sleep(0.04)

        # 先按分数排序，再做行业分散约束
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        diversified = self._diversify_by_sector(scored_candidates, top_k)

        # 更新 why_now 补充主题来源
        for c in diversified:
            c.why_now = f"{c.why_now} | theme={bias_meta}"

        self._write_to_memory(diversified)
        return diversified

    def _build_sector_map(self) -> Dict[str, str]:
        sectors: Dict[str, List[str]] = {
            "technology": [
                "AAPL", "MSFT", "ORCL", "CRM", "ADBE", "NOW", "INTU", "ADP", "IBM", "SAP",
                "SNOW", "DDOG", "MDB", "OKTA", "TEAM", "DOCU", "NET", "ZS", "CRWD", "PANW",
                "AKAM", "WDAY", "HUBS", "SHOP", "SQ", "PYPL", "U", "TWLO", "PLTR", "RBLX"
            ],
            "semiconductor": [
                "NVDA", "AMD", "QCOM", "AVGO", "TXN", "AMAT", "LRCX", "KLAC", "ASML", "MU",
                "MRVL", "INTC", "NXPI", "MCHP", "ON", "SWKS", "QRVO", "TER", "UMC", "TSM",
                "ARM", "SMCI", "GFS", "MPWR", "ENTG", "COHR", "LSCC", "ALAB", "ANET", "CIEN"
            ],
            "financial": [
                "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "AXP", "BLK", "SPGI",
                "ICE", "CME", "KKR", "BX", "APO", "COF", "PYPL", "SOFI", "HOOD", "ALLY",
                "USB", "PNC", "TFC", "FITB", "MTB", "RF", "KEY", "NTRS", "AFL", "CB"
            ],
            "energy": [
                "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "OXY", "DVN", "MRO", "BKR",
                "FANG", "PXD", "APA", "VLO", "MPC", "PSX", "KMI", "WMB", "OKE", "ET"
            ],
            "healthcare": [
                "LLY", "UNH", "JNJ", "PFE", "MRK", "ABBV", "AMGN", "GILD", "REGN", "VRTX",
                "TMO", "DHR", "ISRG", "SYK", "MDT", "ZTS", "BSX", "BMY", "CVS", "CI",
                "HUM", "ELV", "MRNA", "BIIB", "ILMN", "IDXX", "DXCM", "EW", "ALGN", "HCA"
            ],
            "consumer": [
                "AMZN", "TSLA", "WMT", "COST", "TGT", "HD", "LOW", "MCD", "SBUX", "NKE",
                "DIS", "CMCSA", "NFLX", "BKNG", "ABNB", "UBER", "DASH", "RCL", "CCL", "NCLH",
                "ROST", "TJX", "DG", "DLTR", "ULTA", "LULU", "ETSY", "MELI", "PDD", "BABA"
            ],
            "industrial": [
                "CAT", "DE", "GE", "HON", "RTX", "LMT", "NOC", "BA", "UPS", "FDX",
                "UNP", "CSX", "NSC", "WM", "ETN", "PH", "EMR", "ROK", "MMM", "ITW",
                "JCI", "OTIS", "CARR", "IR", "TXT", "PCAR", "CMI", "URI", "FAST", "XYL"
            ],
            "materials": [
                "LIN", "APD", "SHW", "ECL", "NEM", "FCX", "NUE", "STLD", "AA", "MOS",
                "CF", "FMC", "DOW", "DD", "PPG", "MLM", "VMC", "IP", "PKG", "BALL"
            ],
            "utilities": [
                "NEE", "DUK", "SO", "AEP", "EXC", "XEL", "SRE", "D", "PEG", "ED",
                "EIX", "WEC", "AWK", "ES", "FE", "AEE", "CMS", "PNW", "EVRG", "LNT"
            ],
            "real_estate": [
                "PLD", "AMT", "CCI", "EQIX", "O", "SPG", "PSA", "WELL", "DLR", "VICI",
                "EQR", "AVB", "SBAC", "IRM", "CBRE", "BXP", "VTR", "ARE", "KIM", "REG"
            ]
        }
        out: Dict[str, str] = {}
        for sec, syms in sectors.items():
            for s in syms:
                out[s] = sec
        return out

    async def _build_theme_bias(self) -> Tuple[Dict[str, float], str]:
        """用 D1/D2 记忆生成行业主题偏置；若缺失则自己做一轮宏观扫描"""
        d1_summary = self.memory_manager.get_summary("D1", None)
        d2_summary = self.memory_manager.get_summary("D2", None)

        text = f"{d1_summary}\n{d2_summary}".strip()
        source = "memory"
        if not text or "No relevant memory" in text:
            source = "self_scan"
            macro_news = await self.collector.collect_macro_news()
            sector_heads = []
            for sec in ["technology", "financial", "energy", "healthcare", "industrial"]:
                sector_heads.extend(await self.collector.collect_industry_news(sec))
            text = "\n".join([x.summary for x in (macro_news + sector_heads)[:24]])

        # 关键词 -> 行业偏置
        bias = defaultdict(float)
        rules = {
            "technology": ["ai", "cloud", "software", "chip", "semiconductor", "datacenter"],
            "semiconductor": ["chip", "semiconductor", "gpu", "foundry", "memory"],
            "financial": ["yield", "bank", "credit", "rate cut", "rate hike", "liquidity"],
            "energy": ["oil", "gas", "opec", "crude", "refinery"],
            "healthcare": ["drug", "fda", "biotech", "clinical", "pharma"],
            "industrial": ["manufacturing", "freight", "aerospace", "defense", "infrastructure"],
            "consumer": ["retail", "consumer", "ecommerce", "spending", "travel"],
            "materials": ["copper", "steel", "chemical", "mining", "commodity"],
            "utilities": ["power", "grid", "utility", "electricity"],
            "real_estate": ["reit", "housing", "mortgage", "office", "property"],
        }

        neg_words = ["recession", "slowdown", "cut guidance", "downgrade", "risk-off", "selloff"]
        pos_words = ["beat", "upgrade", "growth", "tailwind", "momentum", "risk-on"]

        t = text.lower()
        sentiment = 0.0
        for w in pos_words:
            sentiment += 0.03 * t.count(w)
        for w in neg_words:
            sentiment -= 0.03 * t.count(w)

        for sec, kws in rules.items():
            for kw in kws:
                bias[sec] += 0.04 * t.count(kw)

        # 归一+截断
        out: Dict[str, float] = {}
        for sec in set(list(self._sector_map.values()) + list(bias.keys())):
            raw = bias.get(sec, 0.0) + sentiment * 0.35
            out[sec] = max(-0.35, min(0.35, raw))

        return out, source

    async def _get_candidate_pool(self, sector_bias: Dict[str, float]) -> List[StockCandidate]:
        """构建候选池：大池抽样 + Stooq行情"""
        symbols = list(self._sector_map.keys())

        # 分行业抽样，避免只剩热门大票
        sec_buckets = defaultdict(list)
        for s in symbols:
            sec_buckets[self._sector_map[s]].append(s)

        sample_syms: List[str] = []
        rnd = random.SystemRandom()
        for sec, arr in sec_buckets.items():
            arr = arr[:]
            rnd.shuffle(arr)
            # 行业最多抽样 16，确保宽覆盖
            sample_syms.extend(arr[:16])

        # 加一点全局随机探索
        left = [s for s in symbols if s not in set(sample_syms)]
        rnd.shuffle(left)
        sample_syms.extend(left[:40])
        sample_syms = list(dict.fromkeys(sample_syms))

        quotes = await self._fetch_stooq_quotes(sample_syms)
        if not quotes:
            return []

        # 先统计流动性分位，做拥挤惩罚
        vols = [max(1.0, float(q.get("volume") or 1.0)) for q in quotes.values()]
        vols_sorted = sorted(vols)
        p90 = vols_sorted[max(0, int(len(vols_sorted) * 0.9) - 1)] if vols_sorted else 1.0

        candidates: List[StockCandidate] = []
        for symbol in sample_syms:
            q = quotes.get(symbol)
            if not q:
                continue
            open_v = float(q.get("open") or 0.0)
            high_v = float(q.get("high") or 0.0)
            low_v = float(q.get("low") or 0.0)
            close_v = float(q.get("close") or 0.0)
            vol_v = float(q.get("volume") or 0.0)
            if open_v <= 0 or close_v <= 0:
                continue

            chg = (close_v - open_v) / open_v * 100.0
            intraday_range = max(0.0, (high_v - low_v) / open_v)
            flow = min(1.0, max(0.0, math.log(max(vol_v, 1.0), 10) / 8.0))
            momentum = min(1.0, max(0.0, (chg + 6.0) / 12.0))
            risk = min(1.0, max(0.0, 0.20 + abs(chg) / 10.0 + intraday_range * 2.5))

            sector = self._sector_map.get(symbol, "technology")
            sec_bias = sector_bias.get(sector, 0.0)
            macro = min(1.0, max(0.0, 0.55 + sec_bias + random.uniform(-0.05, 0.06)))
            tailwind = min(1.0, max(0.0, 0.45 + sec_bias + abs(chg) / 12.0 + random.uniform(-0.04, 0.05)))

            if abs(chg) >= 3.2 or intraday_range >= 0.06:
                horizon = "short"
            elif risk <= 0.33:
                horizon = "long"
            else:
                horizon = "mid"

            disq = []
            if risk >= 0.78:
                disq.append("波动过高")
            if vol_v <= 150000:
                disq.append("流动性偏弱")

            crowded_penalty = 0.0
            if symbol in self._mega_hot and vol_v >= p90:
                crowded_penalty += 0.12

            why = (
                f"sector={sector}, 日内涨跌 {chg:.2f}%, 振幅 {intraday_range*100:.2f}%, "
                f"成交量 {vol_v:.0f}, crowd_penalty={crowded_penalty:.2f}"
            )

            c = StockCandidate(
                symbol=symbol,
                name=symbol,
                horizon=horizon,
                score=0.0,
                macro_match=macro,
                industry_tailwind=tailwind,
                news_momentum=momentum,
                whale_flow_heat=flow,
                risk_score=min(1.0, risk + crowded_penalty),
                why_now=why,
                disqualifiers=disq
            )
            candidates.append(c)

        self.last_pool_source = "stooq+theme"
        return candidates

    async def _fetch_stooq_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        sem = asyncio.Semaphore(18)

        async def one(sym: str):
            async with sem:
                q = await self.collector.get_stooq_quote(f"{sym.lower().replace('.', '-')}.us")
                if q and float(q.get("close") or 0.0) > 0:
                    out[sym] = q

        await asyncio.gather(*[one(s) for s in symbols])
        return out

    async def _score_candidate(self, candidate: StockCandidate, sector_bias: Dict[str, float]) -> float:
        """评分：多因子 + 主题偏置 + 去拥挤化"""
        sec = self._sector_map.get(candidate.symbol, "technology")
        sec_bias = sector_bias.get(sec, 0.0)

        weights = {
            'macro_match': 0.18,
            'industry_tailwind': 0.24,
            'news_momentum': 0.17,
            'whale_flow_heat': 0.19,
            'risk_score': -0.14,
            'theme_bias': 0.16,
        }

        score = (
            weights['macro_match'] * candidate.macro_match
            + weights['industry_tailwind'] * candidate.industry_tailwind
            + weights['news_momentum'] * candidate.news_momentum
            + weights['whale_flow_heat'] * candidate.whale_flow_heat
            + weights['risk_score'] * candidate.risk_score
            + weights['theme_bias'] * sec_bias
        )

        # 探索加分：避免长期只选超级热门（对 mega-hot 稍微惩罚）
        if candidate.symbol in self._mega_hot:
            score -= 0.08
        else:
            score += 0.04

        if candidate.disqualifiers:
            score *= 0.72

        # 抖动避免完全固定顺序
        score += random.uniform(-0.015, 0.015)
        return score

    def _diversify_by_sector(self, candidates: List[StockCandidate], top_k: int) -> List[StockCandidate]:
        """行业分散：同一行业最多 2 只，剩余名额再按分数补齐"""
        picked: List[StockCandidate] = []
        sec_count: Dict[str, int] = defaultdict(int)

        # 第一轮：每行业最多2只
        for c in candidates:
            sec = self._sector_map.get(c.symbol, "technology")
            if sec_count[sec] >= 2:
                continue
            picked.append(c)
            sec_count[sec] += 1
            if len(picked) >= top_k:
                return picked

        # 第二轮：补齐
        used = {x.symbol for x in picked}
        for c in candidates:
            if c.symbol in used:
                continue
            picked.append(c)
            if len(picked) >= top_k:
                break
        return picked

    def _fallback_candidates(self, top_k: int) -> List[StockCandidate]:
        """降级池仍保持多行业而非只大票"""
        rnd = random.SystemRandom()
        all_syms = list(self._sector_map.keys())
        rnd.shuffle(all_syms)
        out: List[StockCandidate] = []
        for sym in all_syms[: max(30, top_k * 3)]:
            sec = self._sector_map.get(sym, "technology")
            hz = rnd.choice(["short", "mid", "long"])
            macro_match = 0.5 + rnd.random() * 0.3
            tailwind = 0.5 + rnd.random() * 0.3
            momentum = 0.45 + rnd.random() * 0.35
            flow = 0.4 + rnd.random() * 0.4
            risk = 0.2 + rnd.random() * 0.5
            score = (
                0.20 * macro_match
                + 0.25 * tailwind
                + 0.20 * momentum
                + 0.20 * flow
                - 0.15 * risk
                + rnd.uniform(-0.02, 0.02)
            )
            out.append(StockCandidate(
                symbol=sym,
                name=sym,
                horizon=hz,
                score=score,
                macro_match=macro_match,
                industry_tailwind=tailwind,
                news_momentum=momentum,
                whale_flow_heat=flow,
                risk_score=risk,
                why_now=f"fallback diversified universe | sector={sec}",
                disqualifiers=[]
            ))
        out.sort(key=lambda x: x.score, reverse=True)
        return self._diversify_by_sector(out, top_k)

    def _write_to_memory(self, candidates: List[StockCandidate]):
        summary = "选股部候选池:\n"
        for i, candidate in enumerate(candidates, 1):
            summary += f"{i}. {candidate.symbol} - score={candidate.score:.3f} horizon={candidate.horizon}\n"
            summary += f"   why: {candidate.why_now}\n"

        self.memory_manager.write_session_summary(
            department=self.department_type,
            stock_symbol=None,
            summary=summary,
            metadata={
                "memory_kind": "stock_selection_batch",
                "candidate_count": len(candidates),
                "analysis_timestamp": datetime.now().isoformat(),
                "retention": "short_term",
                "importance": 0.74 if len(candidates) >= 8 else 0.62,
            }
        )

    def create_stock_cases(self, candidates: List[StockCandidate]) -> List[StockCase]:
        return [StockCase(symbol=c.symbol) for c in candidates]
