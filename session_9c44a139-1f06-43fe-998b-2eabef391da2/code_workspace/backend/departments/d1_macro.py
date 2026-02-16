"""
D1 宏观国际新闻部
"""
from typing import List, Optional
from datetime import datetime, timedelta
from models.base_models import Evidence
from .base_department import BaseDepartment
from data.data_collector import DataCollector


class D1MacroDepartment(BaseDepartment):
    """D1 宏观国际新闻部 - 负责政治/央行/地缘/宏观金融"""

    def __init__(self, memory_manager, agent_configs=None):
        super().__init__("D1", memory_manager, agent_configs)
        self.collector = DataCollector()

    def get_department_name(self) -> str:
        return "宏观国际新闻部"

    async def gather_evidence(self, stock_symbol: Optional[str] = None) -> List[Evidence]:
        """收集宏观证据（真实新闻源 + 兜底）"""
        evidence_list = await self.collector.collect_macro_news()

        if evidence_list:
            return evidence_list[:12]

        # 兜底：确保流程不断
        return [
            Evidence(
                content="宏观新闻源暂不可达，系统进入降级模式并维持稳健仓位。",
                timestamp=datetime.now() - timedelta(minutes=20),
                source_id=f"macro_fallback_{int(datetime.now().timestamp())}",
                reliability_score=0.55,
                summary="宏观数据降级提醒",
                metadata={"fallback": True}
            )
        ]
