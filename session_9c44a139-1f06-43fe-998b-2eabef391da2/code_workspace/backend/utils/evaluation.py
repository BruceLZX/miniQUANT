"""
评估系统 - 事后评估和回放
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json


@dataclass
class EvaluationMetrics:
    """评估指标"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_return: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    calibration_score: float = 0.0  # 置信度校准分数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_return": self.total_return,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "calibration_score": self.calibration_score
        }


@dataclass
class CaseEvaluation:
    """案例评估"""
    case_id: str
    symbol: str
    decision_time: datetime
    decision: Dict[str, Any]
    actual_return: float
    hit: bool  # 是否命中
    confidence_at_decision: float
    stance_at_decision: str
    score_at_decision: float
    department_scores: Dict[str, float]
    divergence_at_decision: float
    evaluation_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "symbol": self.symbol,
            "decision_time": self.decision_time.isoformat(),
            "decision": self.decision,
            "actual_return": self.actual_return,
            "hit": self.hit,
            "confidence_at_decision": self.confidence_at_decision,
            "stance_at_decision": self.stance_at_decision,
            "score_at_decision": self.score_at_decision,
            "department_scores": self.department_scores,
            "divergence_at_decision": self.divergence_at_decision,
            "evaluation_time": self.evaluation_time.isoformat()
        }


class EvaluationEngine:
    """评估引擎"""
    
    def __init__(self):
        self.evaluations: List[CaseEvaluation] = []
        self.metrics = EvaluationMetrics()
    
    def evaluate_case(self, 
                     case: Dict[str, Any],
                     actual_return: float) -> CaseEvaluation:
        """评估单个案例"""
        
        decision = case.get('trading_decision', {})
        quant_output = case.get('quant_output', {})
        dept_finals = case.get('department_finals', {})
        
        # 提取决策时的信息
        confidence = 0.5
        stance = "neutral"
        score = 0.0
        dept_scores = {}
        divergence = 0.0
        
        if 'D6' in dept_finals:
            d6_final = dept_finals['D6']
            confidence = d6_final.get('confidence', 0.5)
            score = d6_final.get('score', 0.0)
            stance = "bull" if score > 0.2 else ("bear" if score < -0.2 else "neutral")
        
        for dept_type, dept_final in dept_finals.items():
            dept_scores[dept_type] = dept_final.get('score', 0.0)
        
        if quant_output:
            divergence = quant_output.get('divergence', 0.0)
        
        # 判断是否命中
        hit = False
        if decision.get('direction') == 'LONG' and actual_return > 0:
            hit = True
        elif decision.get('direction') == 'SHORT' and actual_return < 0:
            hit = True
        elif decision.get('direction') == 'FLAT' and abs(actual_return) < 0.01:
            hit = True
        
        evaluation = CaseEvaluation(
            case_id=case.get('case_id', ''),
            symbol=case.get('symbol', ''),
            decision_time=datetime.fromisoformat(case.get('created_at', datetime.now().isoformat())),
            decision=decision,
            actual_return=actual_return,
            hit=hit,
            confidence_at_decision=confidence,
            stance_at_decision=stance,
            score_at_decision=score,
            department_scores=dept_scores,
            divergence_at_decision=divergence
        )
        
        self.evaluations.append(evaluation)
        self._update_metrics(evaluation)
        
        return evaluation
    
    def _update_metrics(self, evaluation: CaseEvaluation):
        """更新评估指标"""
        self.metrics.total_trades += 1
        
        if evaluation.hit:
            self.metrics.winning_trades += 1
            self.metrics.avg_win = (
                (self.metrics.avg_win * (self.metrics.winning_trades - 1) + evaluation.actual_return)
                / self.metrics.winning_trades
            )
        else:
            self.metrics.losing_trades += 1
            self.metrics.avg_loss = (
                (self.metrics.avg_loss * (self.metrics.losing_trades - 1) + evaluation.actual_return)
                / self.metrics.losing_trades
            )
        
        self.metrics.total_return += evaluation.actual_return
        self.metrics.win_rate = self.metrics.winning_trades / self.metrics.total_trades
        
        if self.metrics.avg_loss != 0:
            self.metrics.profit_factor = abs(self.metrics.avg_win / self.metrics.avg_loss)
        
        # 计算置信度校准分数
        self._calculate_calibration()
    
    def _calculate_calibration(self):
        """计算置信度校准分数"""
        if len(self.evaluations) < 10:
            return
        
        # 按置信度分组计算命中率
        confidence_bins = {}
        for eval in self.evaluations:
            conf_bin = int(eval.confidence_at_decision * 10) / 10  # 0.1为间隔
            if conf_bin not in confidence_bins:
                confidence_bins[conf_bin] = []
            confidence_bins[conf_bin].append(eval.hit)
        
        # 计算校准误差
        calibration_errors = []
        for conf_bin, hits in confidence_bins.items():
            actual_rate = sum(hits) / len(hits)
            expected_rate = conf_bin + 0.05  # 中点
            calibration_errors.append(abs(actual_rate - expected_rate))
        
        # 校准分数 = 1 - 平均误差
        if calibration_errors:
            self.metrics.calibration_score = 1 - sum(calibration_errors) / len(calibration_errors)
    
    def get_metrics(self) -> EvaluationMetrics:
        """获取评估指标"""
        return self.metrics
    
    def get_evaluations(self, symbol: Optional[str] = None) -> List[CaseEvaluation]:
        """获取评估记录"""
        if symbol:
            return [e for e in self.evaluations if e.symbol == symbol]
        return self.evaluations
    
    def analyze_department_contribution(self) -> Dict[str, float]:
        """分析各部门贡献度"""
        if len(self.evaluations) < 10:
            return {}
        
        dept_contributions = {}
        
        for dept_type in ['D1', 'D2', 'D3', 'D4']:
            # 计算该部门分数与实际收益的相关性
            scores = []
            returns = []
            
            for eval in self.evaluations:
                if dept_type in eval.department_scores:
                    scores.append(eval.department_scores[dept_type])
                    returns.append(eval.actual_return)
            
            if len(scores) > 0:
                correlation = self._calculate_correlation(scores, returns)
                dept_contributions[dept_type] = correlation
        
        return dept_contributions
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """计算相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = (
            (sum((xi - mean_x) ** 2 for xi in x) ** 0.5) *
            (sum((yi - mean_y) ** 2 for yi in y) ** 0.5)
        )
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def generate_report(self) -> Dict[str, Any]:
        """生成评估报告"""
        return {
            "metrics": self.metrics.to_dict(),
            "total_evaluations": len(self.evaluations),
            "department_contributions": self.analyze_department_contribution(),
            "recent_evaluations": [e.to_dict() for e in self.evaluations[-10:]],
            "generated_at": datetime.now().isoformat()
        }
