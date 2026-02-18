"""
分析者Agent
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentConfig
from models.base_models import AnalystOutput, Evidence


class AnalystAgent(BaseAgent):
    """分析者Agent - Round 1"""

    def __init__(self, config: AgentConfig, analyst_id: str):
        super().__init__(config)
        self.analyst_id = analyst_id

    def _department_playbook(self, department: str) -> str:
        d = (department or "").upper()
        if "宏观" in department or d == "D1":
            return (
                "关注：利率路径、通胀、就业、美元、油价、地缘冲突。"
                "输出必须写清宏观变量如何传导到风险偏好与估值折现。"
            )
        if "行业" in department or d == "D2":
            return (
                "关注：行业景气度、供需变化、监管与价格周期。"
                "输出必须区分结构性趋势与短期噪音。"
            )
        if "单股" in department or d == "D3":
            return (
                "关注：财报、指引、产品节奏、管理层、诉讼与监管。"
                "输出必须明确公司特异性催化/风险。"
            )
        if "专业材料" in department or d == "D4":
            return (
                "关注：用户上传材料的可信度、作者偏见、与公开信息一致性。"
                "图文材料需先抽取事实，再做观点。"
            )
        if "决策" in department or d == "D6":
            return (
                "关注：把 D1-D5 综合成可执行交易意见。"
                "在风控合规下追求月度可实现收益，分歧大时可降仓但不要机械长期空转。"
            )
        if "选股" in department or d == "D7":
            return (
                "关注：候选池覆盖度、行业分散、避免热门拥挤交易。"
                "必须区分短/中/长期入选逻辑。"
            )
        return "输出必须可审计，所有核心论点需绑定证据 source_id。"

    def _build_web_queries(self, department: str, stock_symbol: str, evidence_pack: List[Evidence]) -> List[str]:
        base = []
        sym = (stock_symbol or "").upper().strip()
        if sym:
            base.extend([
                f"{sym} earnings guidance regulation last 7 days",
                f"{sym} analyst rating target price latest",
                f"{sym} unusual volume options flow",
            ])
        else:
            base.extend([
                "US macro inflation fed rates latest",
                "global risk sentiment dollar treasury yield",
                "equity sector rotation latest week",
            ])

        # 用证据摘要补充检索词
        for ev in evidence_pack[:2]:
            s = (getattr(ev, "summary", "") or "").strip()
            if s:
                base.append(f"{s} market impact")

        dep = (department or "")
        if "行业" in dep:
            base.append("sector outlook valuation cycle latest")
        if "宏观" in dep:
            base.append("fed minutes cpi jobs market reaction")

        # 去重
        out = []
        seen = set()
        for q in base:
            k = q.lower().strip()
            if k and k not in seen:
                seen.add(k)
                out.append(q)
        return out[:5]

    def build_prompt(self, context: Dict[str, Any]) -> str:
        """构建分析提示词"""
        department = context.get('department', 'Unknown')
        stock_symbol = context.get('stock_symbol', '')
        evidence_pack = context.get('evidence_pack', [])
        memory_summary = context.get('memory_summary', '')

        web_queries = self._build_web_queries(department, stock_symbol, evidence_pack)
        web_block = "\n".join([f"- {q}" for q in web_queries])

        prompt = f"""
你是 {department} 的资深 Analyst（{self.analyst_id}）。
今天日期：{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}。

[任务目标]
你必须产出一份可审计、可执行、可证伪的结构化分析，不允许泛泛而谈。

[策略导向（必须遵守）]
1. 目标是月度维度持续盈利，避免“超过3个月长期持有且无操作建议”。
2. 在风控约束内可以更积极一些，优先给出可执行的加减仓/交易窗口建议。
3. 只有在证据明确不足或风险极高时才建议 NO_TRADE，不能把 NO_TRADE 当默认答案。

[部门作业规范]
{self._department_playbook(department)}

[分析对象]
{stock_symbol if stock_symbol else '全局/组合层面'}

[输入证据包]
{self._format_evidence(evidence_pack)}

[记忆摘要]
{memory_summary}

WEB_SEARCH_QUERIES_START
{web_block}
WEB_SEARCH_QUERIES_END

[强制要求]
1. 必须结合联网检索结果与输入证据包。
2. 至少引用 3 条证据（source_id/url/时间）。
3. 先写“事实”再写“推断”，明确两者边界。
4. 给出最少 3 个可证伪条件。
5. 分数必须和逻辑一致，禁止高分低置信矛盾。
6. 给出时间维度建议（短线/波段/月度），避免只有超长期被动持有结论。

[输出JSON Schema]
{{
  "stance": "bull|bear|neutral",
  "score": -1.0,
  "confidence": 0.0,
  "reasoning": "分步骤推理，含风险与反证",
  "key_evidence_ids": ["source_id_1", "source_id_2"],
  "web_findings": [
    {{"title":"...","url":"...","source":"...","timestamp":"...","impact":"..."}}
  ],
  "counter_evidence": ["反方证据1", "反方证据2"],
  "falsifiable_conditions": ["条件1", "条件2", "条件3"]
}}

只输出 JSON，不要输出 markdown。
"""
        return prompt

    def _format_evidence(self, evidence_list: List[Evidence]) -> str:
        if not evidence_list:
            return "暂无可用证据"

        formatted = []
        for i, ev in enumerate(evidence_list, 1):
            formatted.append(
                f"{i}. [{ev.timestamp.strftime('%Y-%m-%d %H:%M')}] "
                f"(可靠性: {ev.reliability_score:.2f}) "
                f"{ev.summary}\n"
                f"   source_id: {ev.source_id}"
            )
        return "\n".join(formatted)

    async def execute(self, context: Dict[str, Any]) -> AnalystOutput:
        prompt = self.build_prompt(context)
        response = await self.call_model(prompt)
        parsed = self.parse_response(response)

        evidence_pack: List[Evidence] = context.get('evidence_pack', [])
        by_id = {e.source_id: e for e in evidence_pack if hasattr(e, "source_id")}
        selected_ids = parsed.get("key_evidence_ids", []) or []
        selected_evidence: List[Evidence] = []
        for sid in selected_ids:
            if sid in by_id:
                selected_evidence.append(by_id[sid])
        if not selected_evidence:
            selected_evidence = evidence_pack[:3]

        return AnalystOutput(
            analyst_id=self.analyst_id,
            model_provider=self.model_provider,
            stance=parsed.get('stance', 'neutral'),
            score=float(parsed.get('score', 0.0)),
            confidence=float(parsed.get('confidence', 0.5)),
            key_evidence=selected_evidence,
            counter_evidence=[],
            falsifiable_conditions=parsed.get('falsifiable_conditions', []),
            reasoning=parsed.get('reasoning', '')
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
                "stance": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "reasoning": response,
                "key_evidence_ids": [],
                "counter_evidence": [],
                "falsifiable_conditions": []
            }
