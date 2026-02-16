"""
批评者Agent
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentConfig
from models.base_models import CriticOutput, AnalystOutput


class CriticAgent(BaseAgent):
    """批评者Agent - Round 2"""

    def __init__(self, config: AgentConfig, critic_id: str):
        super().__init__(config)
        self.critic_id = critic_id

    def build_prompt(self, context: Dict[str, Any]) -> str:
        department = context.get('department', 'Unknown')
        analyst_outputs: List[AnalystOutput] = context.get('analyst_outputs', [])
        analyst_summary = self._format_analyst_outputs(analyst_outputs)

        prompt = f"""
你是 {department} 的 Critic（{self.critic_id}），职责是“找错、补漏洞、压过度自信”。

[输入]
{analyst_summary}

WEB_SEARCH_QUERIES_START
- {department} key risks contradictory evidence latest
- {department} consensus view blind spots
- market tail risk scenario stress test latest
WEB_SEARCH_QUERIES_END

[批评要求]
1. 必须指出可验证的具体漏洞，而不是抽象评价。
2. 必须构建 steelman（最强反方论证）。
3. 必须输出尾部风险情景（至少3条）。
4. 对三位分析师给出置信度校正建议（可正可负）。
5. 如果发现证据时间不一致/来源弱，必须明确标红。

[输出JSON]
{{
  "logic_gaps": ["..."],
  "insufficient_evidence": ["..."],
  "steelman_argument": "...",
  "tail_risks": ["...","...","..."],
  "confidence_corrections": {{"analyst_id": -0.12}},
  "overall_assessment": "..."
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
                f"{output.analyst_id}({output.model_provider}) | stance={output.stance} | "
                f"score={output.score:.2f} | conf={output.confidence:.2f} | "
                f"reasoning={output.reasoning[:260]}"
            )
        return "\n".join(formatted)

    async def execute(self, context: Dict[str, Any]) -> CriticOutput:
        prompt = self.build_prompt(context)
        response = await self.call_model(prompt)
        parsed = self.parse_response(response)

        return CriticOutput(
            critic_id=self.critic_id,
            model_provider=self.model_provider,
            logic_gaps=parsed.get('logic_gaps', []),
            insufficient_evidence=parsed.get('insufficient_evidence', []),
            steelman_argument=parsed.get('steelman_argument', ''),
            tail_risks=parsed.get('tail_risks', []),
            confidence_corrections=parsed.get('confidence_corrections', {})
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
                "logic_gaps": [],
                "insufficient_evidence": [],
                "steelman_argument": "",
                "tail_risks": [],
                "confidence_corrections": {}
            }
