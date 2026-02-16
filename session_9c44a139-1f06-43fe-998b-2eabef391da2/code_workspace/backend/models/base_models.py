"""
基础数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


@dataclass
class Evidence:
    """证据包"""
    content: str  # 内容
    timestamp: datetime  # 时间戳
    source_id: str  # 来源ID（URL或文件hash）
    reliability_score: float  # 来源可靠性评分 [0, 1]
    summary: str  # 简短摘要
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "reliability_score": self.reliability_score,
            "summary": self.summary,
            "metadata": self.metadata
        }


@dataclass
class AnalystOutput:
    """分析者输出"""
    analyst_id: str
    model_provider: str
    stance: str  # bull/bear/neutral
    score: float  # [-1, 1]
    confidence: float  # [0, 1]
    key_evidence: List[Evidence]
    counter_evidence: List[Evidence]
    falsifiable_conditions: List[str]  # 可证伪条件
    reasoning: str  # 推理过程
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyst_id": self.analyst_id,
            "model_provider": self.model_provider,
            "stance": self.stance,
            "score": self.score,
            "confidence": self.confidence,
            "key_evidence": [e.to_dict() for e in self.key_evidence],
            "counter_evidence": [e.to_dict() for e in self.counter_evidence],
            "falsifiable_conditions": self.falsifiable_conditions,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CriticOutput:
    """批评者输出"""
    critic_id: str
    model_provider: str
    logic_gaps: List[str]  # 逻辑漏洞
    insufficient_evidence: List[str]  # 证据不足点
    steelman_argument: str  # 最强反方论证
    tail_risks: List[str]  # 风险情景
    confidence_corrections: Dict[str, float]  # 对各分析者置信度的校正建议
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "critic_id": self.critic_id,
            "model_provider": self.model_provider,
            "logic_gaps": self.logic_gaps,
            "insufficient_evidence": self.insufficient_evidence,
            "steelman_argument": self.steelman_argument,
            "tail_risks": self.tail_risks,
            "confidence_corrections": self.confidence_corrections,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DeciderOutput:
    """拍板者输出"""
    decider_id: str
    model_provider: str
    consensus_points: List[str]  # 共识点
    divergence_points: List[str]  # 分歧点
    final_score: float  # 最终分数 [-1, 1]
    final_confidence: float  # 最终置信度 [0, 1]
    thesis: str  # 核心论点
    falsifiable_triggers: List[str]  # 可证伪触发条件
    action_recommendation: str  # 行动建议
    evidence_ids: List[str]  # 引用的证据ID
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decider_id": self.decider_id,
            "model_provider": self.model_provider,
            "consensus_points": self.consensus_points,
            "divergence_points": self.divergence_points,
            "final_score": self.final_score,
            "final_confidence": self.final_confidence,
            "thesis": self.thesis,
            "falsifiable_triggers": self.falsifiable_triggers,
            "action_recommendation": self.action_recommendation,
            "evidence_ids": self.evidence_ids,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DepartmentFinal:
    """部门最终结论"""
    department_type: str
    stock_symbol: Optional[str]  # D1和D5可以为None（共享）
    round1_outputs: List[AnalystOutput]
    round2_output: CriticOutput
    round3_output: DeciderOutput
    score: float  # 最终分数
    confidence: float  # 最终置信度
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "department_type": self.department_type,
            "stock_symbol": self.stock_symbol,
            "round1_outputs": [o.to_dict() for o in self.round1_outputs],
            "round2_output": self.round2_output.to_dict(),
            "round3_output": self.round3_output.to_dict(),
            "score": self.score,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MarketData:
    """市场数据"""
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    vwap: float
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    
    @property
    def mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2
    
    @property
    def spread(self) -> float:
        return self.ask_price - self.bid_price
    
    @property
    def imbalance(self) -> float:
        """订单簿不平衡"""
        total_size = self.bid_size + self.ask_size
        if total_size == 0:
            return 0
        return (self.bid_size - self.ask_size) / total_size


@dataclass
class WhaleFlow:
    """大额资金流"""
    symbol: str
    timestamp: datetime
    block_net_buy_value: float  # 大单净买入
    dark_pool_net: float  # 暗池净流入
    options_whale_notional: float  # 期权大额名义价值
    adv: float  # 平均日成交量
    
    @property
    def bf(self) -> float:
        """Block Flow指标"""
        return self.block_net_buy_value / self.adv if self.adv > 0 else 0
    
    @property
    def dp(self) -> float:
        """Dark Pool指标"""
        return self.dark_pool_net / self.adv if self.adv > 0 else 0
    
    @property
    def of(self) -> float:
        """Options Flow指标"""
        return self.options_whale_notional / self.adv if self.adv > 0 else 0


@dataclass
class QuantOutput:
    """量化部输出"""
    symbol: str
    timestamp: datetime
    market_alpha: float  # 市场alpha
    research_gate: float  # 研究门控
    final_alpha: float  # 最终alpha
    position: float  # 建议仓位
    volatility: float  # 波动率
    whale_flow_score: float  # 大额资金流得分
    research_score: float  # 研究得分
    divergence: float  # 分歧度
    event_risk: float  # 事件风险
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "market_alpha": self.market_alpha,
            "research_gate": self.research_gate,
            "final_alpha": self.final_alpha,
            "position": self.position,
            "volatility": self.volatility,
            "whale_flow_score": self.whale_flow_score,
            "research_score": self.research_score,
            "divergence": self.divergence,
            "event_risk": self.event_risk
        }


@dataclass
class TradingDecision:
    """交易决策"""
    symbol: str
    timestamp: datetime
    direction: str  # LONG/SHORT/FLAT/NO_TRADE
    target_position: float
    execution_plan: Dict[str, Any]
    risk_controls: Dict[str, Any]
    rationale: str
    evidence_ids: List[str]
    department_outputs: Dict[str, Any]  # D1-D6的输出
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "target_position": self.target_position,
            "execution_plan": self.execution_plan,
            "risk_controls": self.risk_controls,
            "rationale": self.rationale,
            "evidence_ids": self.evidence_ids,
            "department_outputs": self.department_outputs
        }


@dataclass
class StockCase:
    """股票案例"""
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active/closed
    department_finals: Dict[str, DepartmentFinal] = field(default_factory=dict)
    quant_output: Optional[QuantOutput] = None
    trading_decision: Optional[TradingDecision] = None
    latest_price: Optional[float] = None
    latest_market_timestamp: Optional[datetime] = None
    
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "symbol": self.symbol,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "department_finals": {k: v.to_dict() for k, v in self.department_finals.items()},
            "quant_output": self.quant_output.to_dict() if self.quant_output else None,
            "trading_decision": self.trading_decision.to_dict() if self.trading_decision else None,
            "latest_price": self.latest_price,
            "latest_market_timestamp": self.latest_market_timestamp.isoformat() if self.latest_market_timestamp else None
        }


@dataclass
class UserAccount:
    """用户账户配置"""
    user_id: str
    account_type: str  # "paper" 或 "real"
    brokerage: Optional[str] = None  # 券商名称（如 "ibkr", "td_ameritrade"）
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    account_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "account_type": self.account_type,
            "brokerage": self.brokerage,
            "account_id": self.account_id,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
            # 注意：不返回敏感信息如 api_key 和 api_secret
        }
