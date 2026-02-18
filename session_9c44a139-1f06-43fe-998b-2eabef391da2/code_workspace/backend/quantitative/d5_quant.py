"""
D5 量化部 - 持续运行的量化分析部门
"""
from typing import Optional, Dict, Any
from datetime import datetime
import math
from collections import deque
import numpy as np
from models.base_models import QuantOutput, MarketData, WhaleFlow, DepartmentFinal
from memory.memory_store import MemoryManager


class D5QuantDepartment:
    """D5 量化部 - 负责市场微结构 + 大额资金流 + 融合研究因子"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self._last_price: Dict[str, float] = {}
        self._ret_windows: Dict[str, deque] = {}

        # 用于在线监督训练：上一时刻特征等待下一时刻收益标签
        self._pending_sample: Dict[str, Dict[str, float]] = {}
        self.training_samples: list = []
        self.max_training_samples = 4000
        self.min_training_samples = 40

        # 量化模型参数
        self.params = {
            # 市场alpha参数
            'beta_0': 0.0,
            'beta_1': 0.3,   # 收益率权重
            'beta_2': 0.2,   # VWAP偏离权重
            'beta_3': 0.15,  # 订单簿不平衡权重
            'beta_4': 0.35,  # 大额资金流权重

            # 大额资金流权重
            'w_1': 0.5,
            'w_2': 0.3,
            'w_3': 0.2,

            # 研究因子权重
            'alpha_M': 0.25,
            'alpha_I': 0.25,
            'alpha_S': 0.35,
            'alpha_E': 0.15,

            # 门控参数
            'gamma_0': 0.0,
            'gamma_1': 1.5,
            'gamma_2': 2.0,
            'gamma_3': 1.0,

            # 风险控制
            'lambda_div': 0.5,
            'K': 0.6,
            'pos_max': 0.8,
            'epsilon': 1e-6
        }
        self.last_training_report: Dict[str, Any] = {}

    async def calculate_quant_output(self,
                                    symbol: str,
                                    market_data: MarketData,
                                    whale_flow: WhaleFlow,
                                    department_finals: Dict[str, DepartmentFinal],
                                    event_risk: float = 0.0) -> QuantOutput:
        """计算量化输出"""

        # 1. 计算市场特征
        r_t = self._calculate_return(market_data)
        z_vwap = self._calculate_vwap_zscore(market_data)
        imb_t = market_data.imbalance
        vol_t = self._calculate_volatility(symbol)

        # 2. 计算大额资金流指标
        WF_t = self._calculate_whale_flow_score(whale_flow)

        # 3. 计算市场alpha
        market_alpha = self._calculate_market_alpha(r_t, z_vwap, imb_t, WF_t)

        # 4. 计算研究因子
        LA_t, divergence = self._calculate_research_factor(department_finals)

        # 5. 应用分歧惩罚
        LA_adjusted = LA_t * (1 - self.params['lambda_div'] * divergence)

        # 6. 计算门控
        gate_t = self._calculate_gate(LA_adjusted, divergence, event_risk)

        # 7. 计算最终alpha
        final_alpha = gate_t * market_alpha

        # 8. 计算建议仓位
        position = self._calculate_position(final_alpha, vol_t)

        # 9. 记录训练样本（下一时刻收益作为监督标签）
        self._record_training_sample(
            symbol=symbol,
            price=market_data.price,
            r_t=r_t,
            z_vwap=z_vwap,
            imb_t=imb_t,
            wf_t=WF_t,
            la_adjusted=LA_adjusted,
            divergence=divergence,
            event_risk=event_risk
        )

        return QuantOutput(
            symbol=symbol,
            timestamp=datetime.now(),
            market_alpha=market_alpha,
            research_gate=gate_t,
            final_alpha=final_alpha,
            position=position,
            volatility=vol_t,
            whale_flow_score=WF_t,
            research_score=LA_t,
            divergence=divergence,
            event_risk=event_risk
        )

    def _record_training_sample(self,
                                symbol: str,
                                price: float,
                                r_t: float,
                                z_vwap: float,
                                imb_t: float,
                                wf_t: float,
                                la_adjusted: float,
                                divergence: float,
                                event_risk: float):
        if price <= 0:
            return

        prev = self._pending_sample.get(symbol)
        if prev and prev.get("price", 0.0) > 0:
            y = (price - prev["price"]) / prev["price"]
            self.training_samples.append({
                "symbol": symbol,
                "ts": datetime.now().isoformat(),
                "x": [1.0, prev["r_t"], prev["z_vwap"], prev["imb_t"], prev["wf_t"]],
                "la_adjusted": prev["la_adjusted"],
                "divergence": prev["divergence"],
                "event_risk": prev["event_risk"],
                "y": float(y)
            })
            if len(self.training_samples) > self.max_training_samples:
                self.training_samples = self.training_samples[-self.max_training_samples:]

        self._pending_sample[symbol] = {
            "price": float(price),
            "r_t": float(r_t),
            "z_vwap": float(z_vwap),
            "imb_t": float(imb_t),
            "wf_t": float(wf_t),
            "la_adjusted": float(la_adjusted),
            "divergence": float(divergence),
            "event_risk": float(event_risk),
        }

    def _calculate_return(self, market_data: MarketData) -> float:
        """计算收益率"""
        prev = self._last_price.get(market_data.symbol)
        self._last_price[market_data.symbol] = market_data.price
        if prev is None or prev <= 0:
            return 0.0
        ret = (market_data.price - prev) / prev

        w = self._ret_windows.setdefault(market_data.symbol, deque(maxlen=120))
        w.append(ret)
        return ret

    def _calculate_vwap_zscore(self, market_data: MarketData) -> float:
        """计算VWAP偏离"""
        if market_data.vwap == 0:
            return 0.0
        return (market_data.price - market_data.vwap) / market_data.vwap

    def _calculate_volatility(self, symbol: str) -> float:
        """计算滚动波动率（使用近120个收益率）"""
        w = self._ret_windows.get(symbol)
        if not w or len(w) < 10:
            return 0.02
        arr = np.array(w, dtype=float)
        vol = float(np.std(arr))
        return max(0.005, min(0.12, vol))

    def _calculate_whale_flow_score(self, whale_flow: WhaleFlow) -> float:
        """计算大额资金流得分"""
        w1 = self.params['w_1']
        w2 = self.params['w_2']
        w3 = self.params['w_3']
        bf = float(np.clip(whale_flow.bf, -3.0, 3.0))
        dp = float(np.clip(whale_flow.dp, -3.0, 3.0))
        of = float(np.clip(whale_flow.of, -3.0, 3.0))
        wf = w1 * bf + w2 * dp + w3 * of
        return float(np.clip(wf, -4.0, 4.0))

    def _calculate_market_alpha(self, r_t: float, z_vwap: float, imb_t: float, WF_t: float) -> float:
        """计算市场alpha（不依赖LLM）"""
        alpha = (
            self.params['beta_0']
            + self.params['beta_1'] * r_t
            + self.params['beta_2'] * z_vwap
            + self.params['beta_3'] * imb_t
            + self.params['beta_4'] * WF_t
        )
        return float(np.clip(alpha, -6.0, 6.0))

    def _calculate_research_factor(self, department_finals: Dict[str, DepartmentFinal]) -> tuple:
        """计算研究因子"""
        scores = {}
        confidences = {}

        dept_mapping = {
            'D1': ('M', 'alpha_M'),
            'D2': ('I', 'alpha_I'),
            'D3': ('S', 'alpha_S'),
            'D4': ('E', 'alpha_E')
        }

        for dept_type, (key, _) in dept_mapping.items():
            if dept_type in department_finals:
                dept_final = department_finals[dept_type]
                scores[key] = dept_final.score
                confidences[key] = dept_final.confidence

        numerator = 0.0
        denominator = self.params['epsilon']

        for key, alpha_key in [('M', 'alpha_M'), ('I', 'alpha_I'), ('S', 'alpha_S'), ('E', 'alpha_E')]:
            if key in scores:
                alpha = self.params[alpha_key]
                c = confidences[key]
                s = scores[key]
                numerator += alpha * c * s
                denominator += alpha * c

        LA_t = numerator / denominator if denominator > self.params['epsilon'] else 0.0

        score_values = list(scores.values())
        if len(score_values) > 1:
            mean_score = sum(score_values) / len(score_values)
            variance = sum((s - mean_score) ** 2 for s in score_values) / len(score_values)
            divergence = math.sqrt(variance)
        else:
            divergence = 0.0

        return LA_t, divergence

    def _calculate_gate(self, LA_adjusted: float, divergence: float, event_risk: float) -> float:
        """计算研究门控"""
        x = (
            self.params['gamma_0']
            + self.params['gamma_1'] * LA_adjusted
            - self.params['gamma_2'] * divergence
            - self.params['gamma_3'] * event_risk
        )
        # 防止exp溢出
        x = max(-20.0, min(20.0, x))
        return 1.0 / (1.0 + math.exp(-x))

    def _calculate_position(self, final_alpha: float, volatility: float) -> float:
        """计算建议仓位"""
        if volatility <= 0:
            volatility = 0.01
        raw_position = self.params['K'] * final_alpha / volatility
        return max(-self.params['pos_max'], min(self.params['pos_max'], raw_position))

    def update_params(self, new_params: Dict[str, float]):
        """更新模型参数"""
        self.params.update(new_params)

    def get_params(self) -> Dict[str, float]:
        """获取当前参数"""
        return self.params.copy()

    def train_from_runtime(self,
                           trade_history: list,
                           positions: list,
                           latest_quotes: Dict[str, float],
                           account_summary: Dict[str, Any],
                           stock_cases: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """基于运行时数据在线训练：回归校准 beta + 风险门控参数"""
        old = self.get_params()

        # ===== 1) 监督训练样本 =====
        samples = self.training_samples[-1500:]
        sample_n = len(samples)

        # 运行统计
        trade_cnt = len(trade_history or [])
        max_dd = float(account_summary.get("max_drawdown") or 0.0)
        total_pnl = float(account_summary.get("total_pnl") or 0.0)

        # 开仓胜率
        open_samples = 0
        open_wins = 0
        for p in positions or []:
            qty = float(p.get("quantity") or 0.0)
            if qty == 0:
                continue
            open_samples += 1
            entry = float(p.get("avg_cost") or 0.0)
            cur = float(p.get("current_price") or latest_quotes.get(p.get("symbol", ""), 0.0) or 0.0)
            if entry > 0 and cur > entry:
                open_wins += 1
        open_win_rate = (open_wins / open_samples) if open_samples else 0.5

        # ===== 2) 样本不足，跳过训练 =====
        if sample_n < self.min_training_samples:
            report = {
                "timestamp": datetime.now().isoformat(),
                "training": {
                    "sample_count": sample_n,
                    "min_required": self.min_training_samples,
                    "mode": "skip"
                },
                "runtime": {
                    "trade_count": trade_cnt,
                    "open_positions": open_samples,
                    "open_win_rate": round(open_win_rate, 4),
                    "total_pnl": total_pnl,
                    "max_drawdown": max_dd,
                },
                "params_before": old,
                "params_after": old,
                "summary": "D5 training skipped: insufficient samples"
            }
            self.last_training_report = report
            return report

        # ===== 3) 线性回归拟合 beta =====
        X = np.array([s["x"] for s in samples], dtype=float)
        y = np.array([s["y"] for s in samples], dtype=float)

        ridge = 1e-3
        I = np.eye(X.shape[1], dtype=float)
        beta_hat = np.linalg.solve(X.T @ X + ridge * I, X.T @ y)

        pred = X @ beta_hat
        mse = float(np.mean((pred - y) ** 2)) if len(y) else 0.0

        # 方向命中率（忽略极小波动）
        mask = np.abs(y) > 1e-4
        if np.any(mask):
            hit = float(np.mean(np.sign(pred[mask]) == np.sign(y[mask])))
        else:
            hit = 0.5

        # EMA 平滑更新 beta，避免过拟合抖动
        smooth = 0.25
        for i, k in enumerate(["beta_0", "beta_1", "beta_2", "beta_3", "beta_4"]):
            self.params[k] = (1 - smooth) * self.params[k] + smooth * float(beta_hat[i])

        # 防止参数爆炸
        self.params["beta_1"] = float(np.clip(self.params["beta_1"], -2.0, 2.0))
        self.params["beta_2"] = float(np.clip(self.params["beta_2"], -2.0, 2.0))
        self.params["beta_3"] = float(np.clip(self.params["beta_3"], -2.0, 2.0))
        self.params["beta_4"] = float(np.clip(self.params["beta_4"], -2.0, 2.0))

        # ===== 4) 研究门控参数微调（基于样本相关性） =====
        la_vals = np.array([float(s.get("la_adjusted", 0.0)) for s in samples], dtype=float)
        div_vals = np.array([float(s.get("divergence", 0.0)) for s in samples], dtype=float)
        err_vals = np.abs(pred - y)

        la_corr = 0.0
        div_err_corr = 0.0
        if np.std(la_vals) > 1e-8 and np.std(y) > 1e-8:
            la_corr = float(np.corrcoef(la_vals, y)[0, 1])
            if np.isnan(la_corr):
                la_corr = 0.0
        if np.std(div_vals) > 1e-8 and np.std(err_vals) > 1e-8:
            div_err_corr = float(np.corrcoef(div_vals, err_vals)[0, 1])
            if np.isnan(div_err_corr):
                div_err_corr = 0.0

        self.params["gamma_1"] = float(np.clip(self.params["gamma_1"] * (1 + 0.08 * la_corr), 0.6, 3.5))
        self.params["gamma_2"] = float(np.clip(self.params["gamma_2"] * (1 + 0.08 * max(0.0, div_err_corr)), 0.8, 4.0))

        # ===== 5) 风险参数调整 =====
        # hit 高且回撤低 -> 略放大；否则收缩
        if hit >= 0.56 and open_win_rate >= 0.54 and max_dd <= 0.08:
            self.params["K"] = float(np.clip(self.params["K"] * 1.04, 0.4, 2.5))
            self.params["lambda_div"] = float(np.clip(self.params["lambda_div"] * 0.97, 0.2, 1.5))
            self.params["pos_max"] = float(np.clip(self.params["pos_max"] * 1.02, 0.3, 1.25))
        else:
            self.params["K"] = float(np.clip(self.params["K"] * 0.94, 0.35, 2.5))
            self.params["lambda_div"] = float(np.clip(self.params["lambda_div"] * 1.05, 0.2, 1.6))
            self.params["pos_max"] = float(np.clip(self.params["pos_max"] * 0.96, 0.3, 1.25))

        if total_pnl < 0 or max_dd > 0.1:
            self.params["gamma_2"] = float(np.clip(self.params["gamma_2"] * 1.04, 0.8, 4.0))

        report = {
            "timestamp": datetime.now().isoformat(),
            "training": {
                "sample_count": sample_n,
                "mode": "ridge_regression_online",
                "mse": round(mse, 8),
                "directional_hit_rate": round(hit, 4),
                "la_return_corr": round(la_corr, 4),
                "divergence_error_corr": round(div_err_corr, 4),
            },
            "runtime": {
                "trade_count": trade_cnt,
                "open_positions": open_samples,
                "open_win_rate": round(open_win_rate, 4),
                "total_pnl": total_pnl,
                "max_drawdown": max_dd,
            },
            "params_before": old,
            "params_after": self.get_params(),
            "summary": "D5 online training completed"
        }
        self.last_training_report = report
        return report
