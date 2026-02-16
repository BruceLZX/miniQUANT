"""
D3 单股新闻部
"""
from typing import List, Optional
from datetime import datetime, timedelta
from models.base_models import Evidence
from .base_department import BaseDepartment
from data.data_collector import DataCollector


class D3StockDepartment(BaseDepartment):
    """D3 单股新闻部 - 负责公司层面新闻/财报/监管/诉讼/产品/管理层"""

    def __init__(self, memory_manager, agent_configs=None):
        super().__init__("D3", memory_manager, agent_configs)
        self.collector = DataCollector()

    def get_department_name(self) -> str:
        return "单股新闻部"

    async def gather_evidence(self, stock_symbol: Optional[str] = None) -> List[Evidence]:
        """收集单股证据（真实新闻源 + 价格快照）"""
        symbol = (stock_symbol or "").upper().strip()
        if not symbol:
            return []

        evidence_list = await self.collector.collect_stock_news(symbol)

        # 补充一条行情快照，增强可证据化
        try:
            md = await self.collector.get_market_data(symbol)
            evidence_list.insert(0, Evidence(
                content=f"{symbol} 最新价 {md.price:.2f}，成交量 {md.volume:.0f}，时间 {md.timestamp.isoformat()}",
                timestamp=md.timestamp,
                source_id=f"quote_{symbol}_{md.timestamp.strftime('%Y%m%d%H%M')}",
                reliability_score=0.86,
                summary=f"{symbol} 行情快照",
                metadata={"symbol": symbol, "price": md.price, "volume": md.volume}
            ))
        except Exception:
            pass

        if evidence_list:
            return evidence_list[:10]

        return [
            Evidence(
                content=f"{symbol} 新闻源暂不可达，保持中性并等待下一轮证据更新。",
                timestamp=datetime.now() - timedelta(minutes=10),
                source_id=f"stock_fallback_{symbol}_{int(datetime.now().timestamp())}",
                reliability_score=0.55,
                summary=f"{symbol} 新闻降级提醒",
                metadata={"symbol": symbol, "fallback": True}
            )
        ]
