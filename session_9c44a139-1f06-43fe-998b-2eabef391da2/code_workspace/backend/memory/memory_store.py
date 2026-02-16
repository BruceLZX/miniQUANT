"""
记忆系统 - 三层记忆架构
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import re
import math
from collections import Counter
from abc import ABC, abstractmethod


class MemoryScope(Enum):
    """记忆范围"""
    GLOBAL = "global"  # 全局共享（D1, D5, D7）
    STOCK_SPECIFIC = "stock_specific"  # 股票特定（D2, D3, D4, D6）
    DEPARTMENT_SPECIFIC = "department_specific"  # 部门特定


class MemoryType(Enum):
    """记忆类型"""
    LTM = "long_term"  # 长期记忆（months/years）
    STM = "short_term"  # 短期记忆（days/weeks）
    EPHEMERAL = "ephemeral"  # 会话记忆（minutes/hours）


@dataclass
class MemoryEntry:
    """记忆条目"""
    entry_id: str
    memory_type: MemoryType
    scope: MemoryScope
    department: Optional[str]  # 部门标识
    stock_symbol: Optional[str]  # 股票代码
    content: str  # 记忆内容
    metadata: Dict[str, Any]  # 元数据
    created_at: datetime
    expires_at: Optional[datetime] = None
    importance: float = 0.5  # 重要性 [0, 1]
    access_count: int = 0  # 访问次数
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "memory_type": self.memory_type.value,
            "scope": self.scope.value,
            "department": self.department,
            "stock_symbol": self.stock_symbol,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "importance": self.importance,
            "access_count": self.access_count
        }


class MemoryStore(ABC):
    """记忆存储抽象基类"""
    
    @abstractmethod
    def store(self, entry: MemoryEntry) -> bool:
        """存储记忆"""
        pass
    
    @abstractmethod
    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """检索单条记忆"""
        pass
    
    @abstractmethod
    def query(self, 
              memory_type: Optional[MemoryType] = None,
              scope: Optional[MemoryScope] = None,
              department: Optional[str] = None,
              stock_symbol: Optional[str] = None,
              limit: int = 100) -> List[MemoryEntry]:
        """查询记忆"""
        pass
    
    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def cleanup_expired(self) -> int:
        """清理过期记忆"""
        pass


class InMemoryStore(MemoryStore):
    """内存记忆存储（用于开发和测试）"""
    
    def __init__(self):
        self._entries: Dict[str, MemoryEntry] = {}
    
    def store(self, entry: MemoryEntry) -> bool:
        try:
            self._entries[entry.entry_id] = entry
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
        return entry
    
    def query(self, 
              memory_type: Optional[MemoryType] = None,
              scope: Optional[MemoryScope] = None,
              department: Optional[str] = None,
              stock_symbol: Optional[str] = None,
              limit: int = 100) -> List[MemoryEntry]:
        results = []
        for entry in self._entries.values():
            if entry.is_expired():
                continue
            
            # 应用过滤条件
            if memory_type and entry.memory_type != memory_type:
                continue
            if scope and entry.scope != scope:
                continue
            if department and entry.department != department:
                continue
            if stock_symbol and entry.stock_symbol != stock_symbol:
                continue
            
            results.append(entry)
        
        # 按重要性和访问次数排序
        results.sort(key=lambda x: (x.importance, x.access_count), reverse=True)
        return results[:limit]
    
    def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False
    
    def cleanup_expired(self) -> int:
        expired_ids = [eid for eid, entry in self._entries.items() if entry.is_expired()]
        for eid in expired_ids:
            del self._entries[eid]
        return len(expired_ids)


class MemoryManager:
    """记忆管理器 - 管理三层记忆"""
    
    def __init__(self, store: MemoryStore):
        self.store = store
        self._setup_expiry_rules()
        # 软上限，防止记忆无限增长
        self.max_total_entries = 3000
        self.max_bucket_entries = 120
    
    def _setup_expiry_rules(self):
        """设置过期规则"""
        self.expiry_rules = {
            MemoryType.LTM: None,  # 长期记忆不过期
            MemoryType.STM: timedelta(days=30),  # 短期记忆30天
            MemoryType.EPHEMERAL: timedelta(hours=24)  # 会话记忆24小时
        }

    def _tokenize(self, text: str) -> List[str]:
        s = str(text or "").lower()
        # 英文词 + 数字 + 常见代码符号拆词
        tokens = re.findall(r"[a-z0-9\.\-_]+", s)
        # 过滤太短token
        return [t for t in tokens if len(t) >= 2]

    def _cosine_text(self, a: str, b: str) -> float:
        ta = self._tokenize(a)
        tb = self._tokenize(b)
        if not ta or not tb:
            return 0.0
        ca = Counter(ta)
        cb = Counter(tb)
        dot = 0.0
        for k, va in ca.items():
            dot += float(va) * float(cb.get(k, 0))
        na = math.sqrt(sum(float(v) * float(v) for v in ca.values()))
        nb = math.sqrt(sum(float(v) * float(v) for v in cb.values()))
        if na <= 1e-12 or nb <= 1e-12:
            return 0.0
        return max(0.0, min(1.0, dot / (na * nb)))

    def _keyword_overlap(self, a: str, b: str) -> float:
        sa = set(self._tokenize(a))
        sb = set(self._tokenize(b))
        if not sa or not sb:
            return 0.0
        inter = len(sa.intersection(sb))
        base = len(sb)
        if base <= 0:
            return 0.0
        return max(0.0, min(1.0, inter / float(base)))
    
    def add_memory(self,
                   memory_type: MemoryType,
                   scope: MemoryScope,
                   content: str,
                   department: Optional[str] = None,
                   stock_symbol: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   importance: float = 0.5) -> MemoryEntry:
        """添加记忆"""
        import uuid
        
        # 计算过期时间
        expires_at = None
        if self.expiry_rules.get(memory_type):
            expires_at = datetime.now() + self.expiry_rules[memory_type]
        
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            memory_type=memory_type,
            scope=scope,
            department=department,
            stock_symbol=stock_symbol,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now(),
            expires_at=expires_at,
            importance=max(0.0, min(1.0, float(importance)))
        )
        
        self.store.store(entry)
        self.prune_memories()
        return entry

    def _decide_retention(self,
                          department: str,
                          stock_symbol: Optional[str],
                          summary: str,
                          metadata: Dict[str, Any],
                          default_importance: float = 0.7) -> Dict[str, Any]:
        """根据内容价值决定是否保留、保留层级和重要性。"""
        text = str(summary or "").strip()
        if not text:
            return {"keep": False, "reason": "empty_summary"}

        retention = str((metadata or {}).get("retention", "")).lower().strip()
        if retention == "discard":
            return {"keep": False, "reason": "explicit_discard"}

        # D4 原始材料不应持久化：即使 force_keep 也不落盘
        if department == "D4" and str((metadata or {}).get("memory_kind", "")) == "raw_upload":
            return {"keep": False, "reason": "d4_raw_not_persisted"}

        if bool((metadata or {}).get("force_keep", False)):
            forced_type = str((metadata or {}).get("memory_type", "short_term")).lower().strip()
            mt = MemoryType.LTM if forced_type in ("ltm", "long_term") else MemoryType.STM
            return {
                "keep": True,
                "memory_type": mt,
                "importance": max(0.55, min(1.0, float((metadata or {}).get("importance", default_importance)))),
                "reason": "forced_keep"
            }

        lower = text.lower()
        score = float((metadata or {}).get("score", 0.0) or 0.0)
        confidence = float((metadata or {}).get("confidence", 0.0) or 0.0)
        evidence_count = int((metadata or {}).get("evidence_count", 0) or 0)

        action_hit = any(k in lower for k in ["buy", "sell", "long", "short", "no_trade", "减仓", "加仓", "观望"])
        risk_hit = any(k in lower for k in ["risk", "风控", "回撤", "止损", "tail", "falsifiable", "触发条件"])
        structural_hit = any(k in lower for k in ["regime", "policy", "政策", "利率", "earnings", "guidance", "监管", "并购", "industry", "行业"])
        has_number = bool(re.search(r"[-+]?\d+(\.\d+)?", text))

        imp = float(default_importance)
        imp += min(0.18, max(0.0, confidence - 0.5) * 0.6)
        imp += min(0.14, abs(score) * 0.2)
        if action_hit:
            imp += 0.08
        if risk_hit:
            imp += 0.08
        if structural_hit:
            imp += 0.08
        if has_number:
            imp += 0.05
        if evidence_count >= 2:
            imp += 0.05
        if len(text) < 30:
            imp -= 0.12
        imp = max(0.0, min(1.0, imp))

        weak_signal = (confidence < 0.42 and abs(score) < 0.12 and not action_hit and evidence_count == 0)
        if weak_signal:
            return {"keep": False, "reason": "low_value_signal"}

        if retention in ("ltm", "long_term"):
            memory_type = MemoryType.LTM
        elif retention in ("stm", "short_term"):
            memory_type = MemoryType.STM
        elif retention in ("ephemeral", "tmp"):
            memory_type = MemoryType.EPHEMERAL
        else:
            if imp >= 0.78 or (structural_hit and confidence >= 0.55):
                memory_type = MemoryType.LTM
            elif imp >= 0.48:
                memory_type = MemoryType.STM
            else:
                # 低价值短暂保留，后续会过期清理
                memory_type = MemoryType.EPHEMERAL

        return {
            "keep": True,
            "memory_type": memory_type,
            "importance": imp,
            "reason": "heuristic_keep"
        }
    
    def get_department_memory(self, 
                             department: str,
                             stock_symbol: Optional[str] = None,
                             memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        """获取部门记忆（权限隔离）"""
        # 根据部门类型确定查询范围
        if department in ['D1', 'D5', 'D7']:
            # 全局部门只能访问全局记忆
            scope = MemoryScope.GLOBAL
            stock_symbol = None
        else:
            # 股票特定部门访问股票特定记忆
            scope = MemoryScope.STOCK_SPECIFIC
        
        return self.store.query(
            memory_type=memory_type,
            scope=scope,
            department=department,
            stock_symbol=stock_symbol
        )

    def retrieve_relevant_memory(self,
                                 department: str,
                                 stock_symbol: Optional[str] = None,
                                 query_text: Optional[str] = None,
                                 max_entries: int = 10) -> List[MemoryEntry]:
        """
        语义检索 + 规则分混合：
        - 基础分：importance/access_count/recency
        - 语义分：余弦相似度 + 关键词重叠
        """
        entries = self.get_department_memory(department, stock_symbol)
        if not entries:
            return []

        q = str(query_text or "").strip()
        now = datetime.now()
        scored: List[tuple] = []
        for e in entries:
            age_days = max(0.0, (now - e.created_at).total_seconds() / 86400.0)
            recency = 1.0 / (1.0 + age_days / 7.0)  # 约7天半衰
            access = min(1.0, float(e.access_count) / 20.0)
            base = 0.50 * float(e.importance) + 0.25 * recency + 0.25 * access

            if q:
                sem = self._cosine_text(e.content, q)
                key = self._keyword_overlap(e.content, q)
                rank = 0.60 * base + 0.25 * sem + 0.15 * key
            else:
                rank = base

            scored.append((rank, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:max_entries]]
    
    def get_summary(self,
                   department: str,
                   stock_symbol: Optional[str] = None,
                   max_entries: int = 10,
                   query_text: Optional[str] = None) -> str:
        """获取记忆摘要（用于上下文构建）"""
        entries = self.retrieve_relevant_memory(
            department=department,
            stock_symbol=stock_symbol,
            query_text=query_text,
            max_entries=max_entries
        )
        
        if not entries:
            return "No relevant memory found."
        
        summary_parts = []
        for entry in entries:
            summary_parts.append(f"[{entry.created_at.strftime('%Y-%m-%d %H:%M')}] {entry.content}")
        
        return "\n".join(summary_parts)
    
    def update_importance(self, entry_id: str, delta: float):
        """更新记忆重要性"""
        entry = self.store.retrieve(entry_id)
        if entry:
            entry.importance = min(1.0, max(0.0, entry.importance + delta))
    
    def consolidate_to_ltm(self, entry_id: str):
        """将短期记忆固化为长期记忆"""
        import uuid
        entry = self.store.retrieve(entry_id)
        if entry and entry.memory_type == MemoryType.STM:
            # 创建长期记忆副本
            ltm_entry = MemoryEntry(
                entry_id=str(uuid.uuid4()),
                memory_type=MemoryType.LTM,
                scope=entry.scope,
                department=entry.department,
                stock_symbol=entry.stock_symbol,
                content=entry.content,
                metadata=entry.metadata,
                created_at=entry.created_at,
                expires_at=None,  # 长期记忆不过期
                importance=entry.importance
            )
            self.store.store(ltm_entry)
    
    def prune_memories(self):
        """按容量、时效、重要性清理记忆。"""
        self.store.cleanup_expired()
        if not hasattr(self.store, "_entries"):
            return

        entries: Dict[str, MemoryEntry] = getattr(self.store, "_entries", {})
        now = datetime.now()
        to_delete = set()

        # 1) 清理低重要性旧数据
        for eid, e in entries.items():
            age = now - e.created_at
            if e.memory_type == MemoryType.EPHEMERAL and age > timedelta(hours=24):
                to_delete.add(eid)
                continue
            if e.importance < 0.45 and age > timedelta(days=14):
                to_delete.add(eid)

        # 2) 每个 bucket 限制条数
        buckets: Dict[str, List[MemoryEntry]] = {}
        for eid, e in entries.items():
            if eid in to_delete:
                continue
            key = f"{e.department or 'NA'}::{e.stock_symbol or 'GLOBAL'}::{e.scope.value}"
            buckets.setdefault(key, []).append(e)
        for _, arr in buckets.items():
            arr.sort(key=lambda x: (x.importance, x.access_count, x.created_at.timestamp()), reverse=True)
            for extra in arr[self.max_bucket_entries:]:
                to_delete.add(extra.entry_id)

        # 3) 全局上限
        alive = [e for eid, e in entries.items() if eid not in to_delete]
        alive.sort(key=lambda x: (x.importance, x.access_count, x.created_at.timestamp()), reverse=True)
        for extra in alive[self.max_total_entries:]:
            to_delete.add(extra.entry_id)

        for eid in to_delete:
            entries.pop(eid, None)

    def apply_trade_feedback(self,
                             symbol: str,
                             pnl_ratio: float,
                             decision_direction: str = "",
                             as_of: Optional[datetime] = None):
        """
        交易反馈学习：
        - 根据 pnl_ratio 对相关记忆做 importance 微调
        - 正收益强化，负收益衰减
        """
        if not hasattr(self.store, "_entries"):
            return
        now = as_of or datetime.now()
        sym = str(symbol or "").upper().strip()
        if not sym:
            return

        p = max(-1.0, min(1.0, float(pnl_ratio or 0.0)))
        direction = str(decision_direction or "").upper().strip()
        # SHORT方向收益符号反转
        signed = -p if direction == "SHORT" else p
        # 控制单次调整幅度
        delta_base = max(-0.10, min(0.10, signed * 0.25))
        if abs(delta_base) < 0.002:
            return

        entries: Dict[str, MemoryEntry] = getattr(self.store, "_entries", {})
        for entry in entries.values():
            # 只更新与该股票有关或全局策略部门的近期记忆
            related_stock = str(entry.stock_symbol or "").upper() == sym
            related_global = (
                entry.scope == MemoryScope.GLOBAL
                and (entry.department in ("D1", "D5", "D7"))
            )
            if not (related_stock or related_global):
                continue

            age_h = max(0.0, (now - entry.created_at).total_seconds() / 3600.0)
            if age_h > 24 * 45:
                continue
            recency_w = 1.0 / (1.0 + age_h / 48.0)
            delta = delta_base * recency_w
            entry.importance = max(0.0, min(1.0, entry.importance + delta))

            fb = dict(entry.metadata.get("feedback") or {})
            fb["last_update_at"] = now.isoformat()
            fb["last_symbol"] = sym
            fb["last_direction"] = direction
            fb["last_pnl_ratio"] = p
            fb["updates"] = int(fb.get("updates", 0) or 0) + 1
            fb["importance_delta"] = float(fb.get("importance_delta", 0.0) or 0.0) + float(delta)
            entry.metadata["feedback"] = fb

        self.prune_memories()

    def write_session_summary(self,
                              department: str,
                              stock_symbol: Optional[str],
                              summary: str,
                              metadata: Optional[Dict[str, Any]] = None) -> Optional[MemoryEntry]:
        """
        写入会话摘要：自动评估价值，决定是否保留及保留层级。
        - 低价值会被丢弃
        - 高价值会进入 STM/LTM
        """
        meta = dict(metadata or {})
        decision = self._decide_retention(
            department=department,
            stock_symbol=stock_symbol,
            summary=summary,
            metadata=meta,
            default_importance=float(meta.get("importance", 0.7) or 0.7)
        )
        if not decision.get("keep"):
            return None

        meta["retention_decision"] = {
            "reason": decision.get("reason", "unknown"),
            "memory_type": decision["memory_type"].value,
            "importance": decision["importance"],
            "decided_at": datetime.now().isoformat()
        }

        return self.add_memory(
            memory_type=decision["memory_type"],
            scope=MemoryScope.STOCK_SPECIFIC if stock_symbol else MemoryScope.GLOBAL,
            content=summary,
            department=department,
            stock_symbol=stock_symbol,
            metadata=meta,
            importance=decision["importance"]
        )
