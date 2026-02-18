"""
部门基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import logging
from models.base_models import DepartmentFinal, Evidence, AnalystOutput
from memory.memory_store import MemoryManager
from agents.analyst import AnalystAgent
from agents.critic import CriticAgent
from agents.decider import DeciderAgent
from agents.base_agent import AgentConfig


class BaseDepartment(ABC):
    """部门基类 - 实现三轮讨论机制"""
    
    def __init__(self, 
                 department_type: str,
                 memory_manager: MemoryManager,
                 agent_configs: Optional[Dict[str, AgentConfig]] = None):
        self.department_type = department_type
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化agents
        self.analysts: List[AnalystAgent] = []
        self.critic: Optional[CriticAgent] = None
        self.decider: Optional[DeciderAgent] = None
        
        if agent_configs:
            self._initialize_agents(agent_configs)
        else:
            self._initialize_agents({})
    
    def _initialize_agents(self, configs: Dict[str, AgentConfig]):
        """初始化agents"""
        from config.settings import config as system_config

        default_analyst_models = [m.value for m in system_config.default_analyst_models]
        while len(default_analyst_models) < 3:
            default_analyst_models.append("deepseek")
        default_analyst_model_names = list(system_config.analyst_model_names)
        while len(default_analyst_model_names) < 3:
            default_analyst_model_names.append("")

        # 初始化3个分析者
        for i in range(3):
            provider = default_analyst_models[i]
            config = configs.get(f'analyst_{i}', AgentConfig(
                agent_id=f'{self.department_type}_analyst_{i}',
                model_provider=provider,
                model_name=default_analyst_model_names[i]
            ))
            self.analysts.append(AnalystAgent(config, f'{self.department_type}_analyst_{i}'))
        
        # 初始化批评者
        critic_config = configs.get('critic', AgentConfig(
            agent_id=f'{self.department_type}_critic',
            model_provider=system_config.default_critic_model.value,
            model_name=system_config.critic_model_name
        ))
        self.critic = CriticAgent(critic_config, f'{self.department_type}_critic')
        
        # 初始化拍板者
        decider_config = configs.get('decider', AgentConfig(
            agent_id=f'{self.department_type}_decider',
            model_provider=system_config.default_decider_model.value,
            model_name=system_config.decider_model_name
        ))
        self.decider = DeciderAgent(decider_config, f'{self.department_type}_decider')
    
    @abstractmethod
    async def gather_evidence(self, stock_symbol: Optional[str] = None) -> List[Evidence]:
        """收集证据 - 各部门实现具体逻辑"""
        pass
    
    @abstractmethod
    def get_department_name(self) -> str:
        """获取部门名称"""
        pass
    
    async def run_three_round_discussion(self, 
                                        stock_symbol: Optional[str] = None,
                                        additional_context: Optional[Dict[str, Any]] = None) -> DepartmentFinal:
        """执行三轮讨论机制"""
        
        # 1. 收集证据
        evidence_pack = await self.gather_evidence(stock_symbol)
        
        # 2. 获取记忆摘要
        memory_query = self._build_memory_query(stock_symbol, evidence_pack, additional_context)
        memory_summary = self.memory_manager.get_summary(
            department=self.department_type,
            stock_symbol=stock_symbol,
            query_text=memory_query
        )
        
        # 3. Round 1: 独立分析
        analyst_outputs = await self._run_round1(
            evidence_pack, 
            memory_summary, 
            stock_symbol,
            additional_context
        )
        
        # 4. Round 2: 批评质疑
        critic_output = await self._run_round2(analyst_outputs)
        
        # 5. Round 3: 拍板裁决
        decider_output = await self._run_round3(analyst_outputs, critic_output)
        
        # 6. 构建部门最终结论
        dept_final = DepartmentFinal(
            department_type=self.department_type,
            stock_symbol=stock_symbol,
            round1_outputs=analyst_outputs,
            round2_output=critic_output,
            round3_output=decider_output,
            score=decider_output.final_score,
            confidence=decider_output.final_confidence
        )
        
        # 7. 写入记忆
        self._write_to_memory(dept_final, stock_symbol)
        
        return dept_final
    
    async def _run_round1(self, 
                         evidence_pack: List[Evidence],
                         memory_summary: str,
                         stock_symbol: Optional[str],
                         additional_context: Optional[Dict[str, Any]]) -> List[Any]:
        """Round 1: 独立分析"""
        context = {
            'department': self.get_department_name(),
            'stock_symbol': stock_symbol,
            'evidence_pack': evidence_pack,
            'memory_summary': memory_summary,
            **(additional_context or {})
        }
        
        # 并行执行三个分析者
        tasks = [analyst.execute(context) for analyst in self.analysts]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)
        normalized: List[Any] = []
        failures = 0
        for idx, out in enumerate(outputs):
            if isinstance(out, Exception):
                failures += 1
                analyst = self.analysts[idx]
                self.logger.warning(
                    "Round1 analyst failed: dept=%s analyst=%s provider=%s model=%s err=%s",
                    self.department_type,
                    getattr(analyst, "analyst_id", f"{self.department_type}_analyst_{idx}"),
                    getattr(analyst, "model_provider", ""),
                    getattr(getattr(analyst, "config", None), "model_name", ""),
                    out,
                )
                normalized.append(AnalystOutput(
                    analyst_id=getattr(analyst, "analyst_id", f"{self.department_type}_analyst_{idx}"),
                    model_provider=getattr(analyst, "model_provider", ""),
                    stance="neutral",
                    score=0.0,
                    confidence=0.15,
                    key_evidence=evidence_pack[:2],
                    counter_evidence=[],
                    falsifiable_conditions=["Analyst model unavailable in this round"],
                    reasoning=f"Model call failed and was downgraded: {out}"
                ))
            else:
                normalized.append(out)

        if failures >= len(outputs):
            raise RuntimeError(f"All analysts failed in {self.department_type} round1")
        return normalized
    
    async def _run_round2(self, analyst_outputs: List[Any]) -> Any:
        """Round 2: 批评质疑"""
        context = {
            'department': self.get_department_name(),
            'analyst_outputs': analyst_outputs
        }
        
        return await self.critic.execute(context)
    
    async def _run_round3(self, 
                         analyst_outputs: List[Any],
                         critic_output: Any) -> Any:
        """Round 3: 拍板裁决"""
        context = {
            'department': self.get_department_name(),
            'analyst_outputs': analyst_outputs,
            'critic_output': critic_output
        }
        
        return await self.decider.execute(context)

    def _build_memory_query(self,
                            stock_symbol: Optional[str],
                            evidence_pack: List[Evidence],
                            additional_context: Optional[Dict[str, Any]]) -> str:
        """构建记忆检索查询串，用于语义召回历史结论。"""
        parts: List[str] = []
        if stock_symbol:
            parts.append(str(stock_symbol).upper())
        parts.append(self.department_type)
        for ev in evidence_pack[:5]:
            if getattr(ev, "summary", ""):
                parts.append(str(ev.summary))
            elif getattr(ev, "content", ""):
                parts.append(str(ev.content)[:80])
        if additional_context:
            for k in ("theme", "focus", "signal", "macro_theme", "industry_theme"):
                v = additional_context.get(k)
                if v:
                    parts.append(str(v))
        return " | ".join(parts)
    
    def _write_to_memory(self, dept_final: DepartmentFinal, stock_symbol: Optional[str]):
        """写入记忆"""
        summary = (
            f"{self.get_department_name()} 分析结论:\n"
            f"分数: {dept_final.score:.2f}, 置信度: {dept_final.confidence:.2f}\n"
            f"核心论点: {dept_final.round3_output.thesis}\n"
            f"行动建议: {dept_final.round3_output.action_recommendation}"
        )
        
        self.memory_manager.write_session_summary(
            department=self.department_type,
            stock_symbol=stock_symbol,
            summary=summary,
            metadata={
                "memory_kind": "analysis_conclusion",
                "score": dept_final.score,
                "confidence": dept_final.confidence,
                "evidence_count": len(getattr(dept_final.round3_output, "evidence_ids", []) or []),
                "thesis": str(getattr(dept_final.round3_output, "thesis", "") or "")[:400],
                "action_recommendation": str(getattr(dept_final.round3_output, "action_recommendation", "") or "")[:200],
                "analysis_timestamp": dept_final.timestamp.isoformat() if getattr(dept_final, "timestamp", None) else datetime.now().isoformat(),
            }
        )
