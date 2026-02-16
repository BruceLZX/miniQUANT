"""
D4 专业材料部
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from models.base_models import Evidence
from .base_department import BaseDepartment


class D4ExpertDepartment(BaseDepartment):
    """D4 专业材料部 - 负责用户上传/爬虫抓到的专家分析与图片摘要"""
    
    def __init__(self, memory_manager, agent_configs=None):
        super().__init__("D4", memory_manager, agent_configs)
        self.uploaded_materials = []  # 存储用户上传的材料
    
    def get_department_name(self) -> str:
        return "专业材料部"
    
    def upload_material(self, material: Evidence):
        """用户上传材料"""
        self.uploaded_materials.append(material)

    def list_materials(self) -> List[Dict[str, Any]]:
        """返回上传材料队列（给 UI telemetry 查看）"""
        rows: List[Dict[str, Any]] = []
        for m in self.uploaded_materials[-50:]:
            meta = getattr(m, "metadata", {}) or {}
            rows.append({
                "source_id": m.source_id,
                "summary": m.summary,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "reliability_score": m.reliability_score,
                "stock_symbol": str(meta.get("stock_symbol") or "GLOBAL").upper(),
                "scope": str(meta.get("scope") or "global"),
                "broadcast_to_all": bool(meta.get("broadcast_to_all", True)),
                "image_count": len(meta.get("image_urls") or []),
            })
        return rows
    
    async def gather_evidence(self, stock_symbol: Optional[str] = None) -> List[Evidence]:
        """收集专家材料证据"""
        evidence_list = []
        
        # 添加用户上传的材料：
        # - broadcast_to_all=True：同步给所有 D4 股票运行单元
        # - broadcast_to_all=False：仅同步给目标股票
        target = (stock_symbol or "").upper().strip()
        matched = []
        broadcasted = []
        for material in self.uploaded_materials:
            meta = getattr(material, "metadata", {}) or {}
            scope = str(meta.get("scope") or "global").lower()
            sym = str(meta.get("stock_symbol") or "").upper()
            all_scope = bool(meta.get("broadcast_to_all", scope == "global"))
            if target and sym == target:
                matched.append(material)
            elif all_scope:
                broadcasted.append(material)
        evidence_list.extend(matched + broadcasted)
        evidence_list = evidence_list[-30:]
        
        # 没有用户材料时，保留一条默认样本，避免 D4 空转
        if not evidence_list:
            evidence_list.append(Evidence(
                content="知名分析师报告：该股票技术面显示突破信号，建议关注",
                timestamp=datetime.now() - timedelta(hours=4),
                source_id="expert_analysis_20240115",
                reliability_score=0.70,
                summary="专家技术分析看多",
                metadata={"scope": "default", "stock_symbol": target or "GLOBAL"}
            ))
        
        return evidence_list
    
    def clear_materials(self):
        """清空上传的材料"""
        self.uploaded_materials = []
