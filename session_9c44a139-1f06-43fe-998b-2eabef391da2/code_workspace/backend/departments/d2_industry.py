"""
D2 行业部
"""
from typing import List, Optional
from datetime import datetime, timedelta
from models.base_models import Evidence
from .base_department import BaseDepartment
from data.data_collector import DataCollector


class D2IndustryDepartment(BaseDepartment):
    """D2 行业部 - 负责产业方向分析"""

    def __init__(self, memory_manager, agent_configs=None):
        super().__init__("D2", memory_manager, agent_configs)
        self.collector = DataCollector()

    def get_department_name(self) -> str:
        return "行业部"

    async def gather_evidence(self, stock_symbol: Optional[str] = None) -> List[Evidence]:
        """收集行业证据（行业新闻 + 行业行情快照）"""
        sector = self.collector.infer_sector(stock_symbol or "")
        evidence_list = await self.collector.collect_industry_news(sector)

        snap = await self.collector.collect_sector_snapshot(sector)
        if snap:
            evidence_list.insert(0, snap)

        if evidence_list:
            return evidence_list[:10]

        # 兜底：不让部门空跑
        return [
            Evidence(
                content=f"{sector} 行业数据源暂不可达，维持中性行业判断。",
                timestamp=datetime.now() - timedelta(minutes=15),
                source_id=f"industry_fallback_{sector}_{int(datetime.now().timestamp())}",
                reliability_score=0.55,
                summary=f"{sector} 行业降级提醒",
                metadata={"sector": sector, "fallback": True}
            )
        ]
