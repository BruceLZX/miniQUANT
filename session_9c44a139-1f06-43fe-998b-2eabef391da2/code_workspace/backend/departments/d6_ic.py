"""
D6 投资决策委员会（IC）
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.base_models import Evidence, TradingDecision, DepartmentFinal, QuantOutput
from memory.memory_store import MemoryManager
from agents.base_agent import AgentConfig
from agents.analyst import AnalystAgent
from agents.critic import CriticAgent
from agents.decider import DeciderAgent
import asyncio


class D6ICDepartment:
    """D6 投资决策委员会 - 综合D1-D5，做最终交易决策"""
    
    def __init__(self, memory_manager: MemoryManager, agent_configs: Optional[Dict[str, AgentConfig]] = None):
        self.department_type = "D6"
        self.memory_manager = memory_manager
        
        # 初始化agents
        self.analysts: List[AnalystAgent] = []
        self.critic: Optional[CriticAgent] = None
        self.decider: Optional[DeciderAgent] = None
        
        if agent_configs:
            self._initialize_agents(agent_configs)
        else:
            self._initialize_default_agents()
    
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
            config = configs.get(f'analyst_{i}', AgentConfig(
                agent_id=f'D6_analyst_{i}',
                model_provider=default_analyst_models[i],
                model_name=default_analyst_model_names[i]
            ))
            self.analysts.append(AnalystAgent(config, f'D6_analyst_{i}'))
        
        # 初始化批评者
        critic_config = configs.get('critic', AgentConfig(
            agent_id='D6_critic',
            model_provider=system_config.default_critic_model.value,
            model_name=system_config.critic_model_name
        ))
        self.critic = CriticAgent(critic_config, 'D6_critic')
        
        # 初始化拍板者
        decider_config = configs.get('decider', AgentConfig(
            agent_id='D6_decider',
            model_provider=system_config.default_decider_model.value,
            model_name=system_config.decider_model_name
        ))
        self.decider = DeciderAgent(decider_config, 'D6_decider')
    
    def _initialize_default_agents(self):
        """初始化默认agents"""
        self._initialize_agents({})
    
    async def make_decision(self,
                           symbol: str,
                           department_finals: Dict[str, DepartmentFinal],
                           quant_output: QuantOutput,
                           current_position: float = 0.0) -> TradingDecision:
        """做出最终交易决策"""
        
        # 1. 构建综合上下文
        context = self._build_decision_context(symbol, department_finals, quant_output, current_position)
        
        # 2. 执行三轮讨论
        dept_final = await self._run_three_round_discussion(symbol, context)
        
        # 3. 检查风控条件
        risk_controls = self._check_risk_controls(department_finals, quant_output, current_position)
        
        # 4. 构建交易决策
        direction = self._determine_direction(dept_final.score, risk_controls)
        target_position = self._calculate_target_position(dept_final.score, quant_output.position, risk_controls)
        
        trading_decision = TradingDecision(
            symbol=symbol,
            timestamp=datetime.now(),
            direction=direction,
            target_position=target_position,
            execution_plan=self._build_execution_plan(direction, target_position, current_position),
            risk_controls=risk_controls,
            rationale=dept_final.round3_output.thesis,
            evidence_ids=dept_final.round3_output.evidence_ids,
            department_outputs={k: v.to_dict() for k, v in department_finals.items()}
        )
        
        # 5. 写入记忆
        self._write_to_memory(trading_decision, symbol)
        
        return trading_decision
    
    def _build_decision_context(self,
                                symbol: str,
                                department_finals: Dict[str, DepartmentFinal],
                                quant_output: QuantOutput,
                                current_position: float) -> Dict[str, Any]:
        """构建决策上下文"""
        
        # 提取各部门结论
        dept_summaries = {}
        for dept_type, dept_final in department_finals.items():
            dept_summaries[dept_type] = {
                'score': dept_final.score,
                'confidence': dept_final.confidence,
                'thesis': dept_final.round3_output.thesis,
                'action': dept_final.round3_output.action_recommendation
            }
        
        return {
            'symbol': symbol,
            'department_finals': dept_summaries,
            'quant_output': {
                'market_alpha': quant_output.market_alpha,
                'research_gate': quant_output.research_gate,
                'final_alpha': quant_output.final_alpha,
                'position': quant_output.position,
                'divergence': quant_output.divergence,
                'event_risk': quant_output.event_risk
            },
            'current_position': current_position
        }
    
    async def _run_three_round_discussion(self, symbol: str, context: Dict[str, Any]) -> DepartmentFinal:
        """执行三轮讨论"""
        # 获取记忆摘要
        memory_summary = self.memory_manager.get_summary(
            department=self.department_type,
            stock_symbol=symbol,
            query_text=(
                f"{symbol} decision context "
                f"{context.get('quant_output', {}).get('final_alpha', '')} "
                f"{context.get('quant_output', {}).get('event_risk', '')} "
                f"{' '.join(context.get('department_finals', {}).keys())}"
            )
        )
        context['memory_summary'] = memory_summary
        
        # Round 1: 独立分析
        tasks = [analyst.execute(context) for analyst in self.analysts]
        analyst_outputs = await asyncio.gather(*tasks)
        
        # Round 2: 批评质疑
        critic_output = await self.critic.execute({
            'department': '投资决策委员会',
            'analyst_outputs': analyst_outputs
        })
        
        # Round 3: 拍板裁决
        decider_output = await self.decider.execute({
            'department': '投资决策委员会',
            'analyst_outputs': analyst_outputs,
            'critic_output': critic_output
        })
        
        return DepartmentFinal(
            department_type=self.department_type,
            stock_symbol=symbol,
            round1_outputs=list(analyst_outputs),
            round2_output=critic_output,
            round3_output=decider_output,
            score=decider_output.final_score,
            confidence=decider_output.final_confidence
        )
    
    def _check_risk_controls(self,
                            department_finals: Dict[str, DepartmentFinal],
                            quant_output: QuantOutput,
                            current_position: float) -> Dict[str, Any]:
        """检查风控条件"""
        risk_controls = {
            'no_trade': False,
            'reduce_position': False,
            'max_position': 1.0,
            'stop_loss': -0.02,  # 止损 -2%
            'take_profit': 0.05,  # 止盈 5%
            'max_daily_loss': 0.02,  # 最大日亏损 2%
            'warnings': []
        }
        
        # 检查分歧度
        if quant_output.divergence > 0.5:
            risk_controls['warnings'].append(f"分歧度过高: {quant_output.divergence:.2f}")
            risk_controls['reduce_position'] = True
        
        # 检查事件风险
        if quant_output.event_risk > 0.7:
            risk_controls['warnings'].append(f"事件风险高: {quant_output.event_risk:.2f}")
            risk_controls['no_trade'] = True
        
        # 检查置信度
        avg_confidence = sum(df.confidence for df in department_finals.values()) / len(department_finals)
        if avg_confidence < 0.4:
            risk_controls['warnings'].append(f"平均置信度过低: {avg_confidence:.2f}")
            risk_controls['no_trade'] = True
        
        return risk_controls
    
    def _determine_direction(self, score: float, risk_controls: Dict[str, Any]) -> str:
        """确定交易方向"""
        if risk_controls['no_trade']:
            return "NO_TRADE"
        
        if score > 0.2:
            return "LONG"
        elif score < -0.2:
            return "SHORT"
        else:
            return "FLAT"
    
    def _calculate_target_position(self,
                                   score: float,
                                   quant_position: float,
                                   risk_controls: Dict[str, Any]) -> float:
        """计算目标仓位"""
        if risk_controls['no_trade']:
            return 0.0
        
        if risk_controls['reduce_position']:
            quant_position *= 0.5  # 减半仓位
        
        # 结合分数和量化建议
        target = abs(score) * quant_position
        
        # 限制最大仓位
        return max(-risk_controls['max_position'], 
                  min(risk_controls['max_position'], target))
    
    def _build_execution_plan(self,
                             direction: str,
                             target_position: float,
                             current_position: float) -> Dict[str, Any]:
        """构建执行计划"""
        return {
            'direction': direction,
            'target_position': target_position,
            'position_change': target_position - current_position,
            'order_type': 'limit',  # 限价单
            'time_in_force': 'DAY',  # 当日有效
            'split_orders': abs(target_position - current_position) > 0.3  # 大额订单分批执行
        }
    
    def _write_to_memory(self, decision: TradingDecision, symbol: str):
        """写入记忆"""
        summary = (
            f"投委会决策: {decision.symbol} {decision.direction}\n"
            f"目标仓位: {decision.target_position:.2f}\n"
            f"理由: {decision.rationale}"
        )
        
        self.memory_manager.write_session_summary(
            department=self.department_type,
            stock_symbol=symbol,
            summary=summary,
            metadata={
                "memory_kind": "trading_decision",
                "decision_direction": decision.direction,
                "target_position": decision.target_position,
                "analysis_timestamp": decision.timestamp.isoformat(),
                "retention": "short_term" if decision.direction in ("NO_TRADE", "FLAT") else "long_term",
                "importance": 0.68 if decision.direction in ("NO_TRADE", "FLAT") else 0.86,
                "evidence_count": len(decision.evidence_ids or []),
            }
        )
