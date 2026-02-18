"""
拍板者Agent
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentConfig
from models.base_models import DeciderOutput, AnalystOutput, CriticOutput


class DeciderAgent(BaseAgent):
    """拍板者Agent - Round 3"""

    def __init__(self, config: AgentConfig, decider_id: str):
        super().__init__(config)
        self.decider_id = decider_id

    def build_prompt(self, context: Dict[str, Any]) -> str:
        department = context.get('department', 'Unknown')
        analyst_outputs: List[AnalystOutput] = context.get('analyst_outputs', [])
        critic_output: CriticOutput = context.get('critic_output')

        analyst_summary = self._format_analyst_outputs(analyst_outputs)
        critic_summary = self._format_critic_output(critic_output)

        prompt = f"""
你是 {department} 的 Decider（{self.decider_id}），目标是产出“可执行且可追责”的最终结论。

[Analyst 输入]
{analyst_summary}

[Critic 输入]
{critic_summary}

WEB_SEARCH_QUERIES_START
- {department} decision framework risk control best practice
- conflicting market signals resolution method
- no-trade conditions position sizing discipline
WEB_SEARCH_QUERIES_END

[裁决规则]
1. 先列共识，再列分歧。
2. 分歧大或证据弱时，必须下调 final_confidence。
3. score/confidence/action 三者必须一致。
4. 必须给出至少3条 falsifiable_triggers。
5. 给出行动建议时必须附 rationale 与关键证据id。
6. 以“月度可实现盈利”为目标，不鼓励“超过3个月超长期持有且无操作”。
7. 在风控允许下可适度更积极，优先输出可执行交易动作；NO_TRADE 仅在高风险/证据不足时使用。
8. 若建议持有，必须给出明确再评估时间点与触发条件（不能无限期持有）。

[输出JSON]
{{
  "consensus_points": ["..."],
  "divergence_points": ["..."],
  "final_score": 0.0,
  "final_confidence": 0.0,
  "thesis": "一句话结论",
  "falsifiable_triggers": ["...","...","..."],
  "action_recommendation": "加仓|减仓|观望|不交易|LONG|SHORT|FLAT|NO_TRADE",
  "evidence_ids": ["source_id_1","source_id_2"],
  "rationale": "可执行理由"
}}

只输出 JSON。
"""
        return prompt

    def _format_analyst_outputs(self, outputs: List[AnalystOutput]) -> str:
        if not outputs:
            return "暂无分析者输出"

        formatted = []
        for output in outputs:
            formatted.append(
                f"{output.analyst_id}: stance={output.stance}, score={output.score:.2f}, "
                f"conf={output.confidence:.2f}, reasoning={output.reasoning[:220]}"
            )
        return "\n".join(formatted)

    def _format_critic_output(self, output: CriticOutput) -> str:
        if not output:
            return "暂无批评者输出"
        return (
            f"logic_gaps={output.logic_gaps}; insufficient={output.insufficient_evidence}; "
            f"steelman={output.steelman_argument[:220]}; tail_risks={output.tail_risks}; "
            f"confidence_corrections={output.confidence_corrections}"
        )

    async def execute(self, context: Dict[str, Any]) -> DeciderOutput:
        prompt = self.build_prompt(context)
        response = await self.call_model(prompt)
        parsed = self.parse_response(response)

        evidence_ids = parsed.get('evidence_ids') or []
        if not evidence_ids:
            # 兜底：从 analyst 关键证据中提取
            for output in context.get('analyst_outputs', []):
                for ev in output.key_evidence:
                    sid = getattr(ev, "source_id", "")
                    if sid:
                        evidence_ids.append(sid)

        return DeciderOutput(
            decider_id=self.decider_id,
            model_provider=self.model_provider,
            consensus_points=parsed.get('consensus_points', []),
            divergence_points=parsed.get('divergence_points', []),
            final_score=float(parsed.get('final_score', 0.0)),
            final_confidence=float(parsed.get('final_confidence', 0.5)),
            thesis=parsed.get('thesis', ''),
            falsifiable_triggers=parsed.get('falsifiable_triggers', []),
            action_recommendation=parsed.get('action_recommendation', '观望'),
            evidence_ids=evidence_ids
        )

    def parse_response(self, response: str) -> Dict[str, Any]:
        import json
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
            return json.loads(response)
        except Exception:
            return {
                "consensus_points": [],
                "divergence_points": [],
                "final_score": 0.0,
                "final_confidence": 0.5,
                "thesis": "",
                "falsifiable_triggers": [],
                "action_recommendation": "观望",
                "evidence_ids": []
            }
