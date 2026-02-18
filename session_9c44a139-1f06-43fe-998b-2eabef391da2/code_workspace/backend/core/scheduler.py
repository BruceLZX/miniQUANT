"""
核心调度系统 - 协调所有部门的运行
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
import logging
import uuid
import copy
import os
import json
import re
from types import SimpleNamespace

from config.settings import config, DepartmentType
from models.base_models import StockCase, TradingDecision, QuantOutput, UserAccount
from memory.memory_store import InMemoryStore, MemoryManager, MemoryEntry, MemoryType, MemoryScope

from departments.d1_macro import D1MacroDepartment
from departments.d2_industry import D2IndustryDepartment
from departments.d3_stock import D3StockDepartment
from departments.d4_expert import D4ExpertDepartment
from departments.d6_ic import D6ICDepartment
from departments.d7_stock_selection import D7StockSelectionDepartment
from quantitative.d5_quant import D5QuantDepartment
from trading.paper_trading import PaperTradingEngine, Position


@dataclass
class SchedulerState:
    """调度器状态"""
    is_running: bool = False
    last_run_times: Dict[str, datetime] = None
    active_stocks: List[str] = None
    progress: Dict[str, Any] = None
    d7_recommendations: Dict[str, List[Dict[str, Any]]] = None
    d7_history: List[List[str]] = None
    jobs: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.last_run_times is None:
            self.last_run_times = {}
        if self.active_stocks is None:
            self.active_stocks = []
        if self.progress is None:
            self.progress = {"global": {}, "stocks": {}, "d7": {"status": "idle", "message": ""}}
        if self.d7_recommendations is None:
            self.d7_recommendations = {"short": [], "mid": [], "long": []}
        if self.d7_history is None:
            self.d7_history = []
        if self.jobs is None:
            self.jobs = {}


class _LiteDepartmentFinal:
    """用于重启恢复时保存 D1-D4 关键字段的轻量对象"""

    def __init__(self, raw: Dict[str, Any]):
        raw = raw or {}
        r3 = raw.get("round3_output") or {}
        self.department_type = raw.get("department_type")
        self.stock_symbol = raw.get("stock_symbol")
        self.score = float(raw.get("score", 0.0) or 0.0)
        self.confidence = float(raw.get("confidence", 0.5) or 0.5)
        self.round3_output = SimpleNamespace(
            thesis=str(r3.get("thesis") or ""),
            action_recommendation=str(r3.get("action_recommendation") or ""),
            evidence_ids=list(r3.get("evidence_ids") or []),
        )
        self._raw = raw

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._raw)


class TradingPlatformScheduler:
    """交易平台调度器"""
    
    def __init__(self, user_config: Optional[Dict[str, Any]] = None):
        # 初始化记忆系统
        self.memory_store = InMemoryStore()
        self.memory_manager = MemoryManager(self.memory_store)
        
        # 初始化部门
        self.d1 = D1MacroDepartment(self.memory_manager)
        self.d2 = D2IndustryDepartment(self.memory_manager)
        self.d3 = D3StockDepartment(self.memory_manager)
        self.d4 = D4ExpertDepartment(self.memory_manager)
        self.d5 = D5QuantDepartment(self.memory_manager)
        self.d6 = D6ICDepartment(self.memory_manager)
        self.d7 = D7StockSelectionDepartment(self.memory_manager)
        
        # 初始化交易引擎（默认的，用于向后兼容）
        self.trading_engine = PaperTradingEngine()
        
        # 用户账户管理
        self.user_accounts: Dict[str, UserAccount] = {}
        self.user_trading_engines: Dict[str, PaperTradingEngine] = {}
        
        # 股票案例管理
        self.stock_cases: Dict[str, StockCase] = {}
        
        # 调度器状态
        self.state = SchedulerState()
        
        # 用户配置
        self.user_config = user_config or {}
        
        # 日志
        # 日志
        self.logger = logging.getLogger(__name__)
        
        # 事件触发冷却时间
        self.event_cooldowns: Dict[str, datetime] = {}
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        # D7 仅支持手动触发
        self.d7_manual_only: bool = True
        self._state_file = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", ".runtime_state.json")
        )
        self._load_runtime_state()

    def reload_departments(self):
        """重载部门实例，使运行时配置（如模型选择）立即生效"""
        old_d4_materials = list(getattr(self.d4, "uploaded_materials", [])) if hasattr(self, "d4") else []
        old_d5_params = dict(getattr(self.d5, "params", {})) if hasattr(self, "d5") else {}
        old_d5_samples = list(getattr(self.d5, "training_samples", [])) if hasattr(self, "d5") else []
        old_d5_pending = dict(getattr(self.d5, "_pending_sample", {})) if hasattr(self, "d5") else {}
        old_d5_report = dict(getattr(self.d5, "last_training_report", {})) if hasattr(self, "d5") else {}
        self.d1 = D1MacroDepartment(self.memory_manager)
        self.d2 = D2IndustryDepartment(self.memory_manager)
        self.d3 = D3StockDepartment(self.memory_manager)
        self.d4 = D4ExpertDepartment(self.memory_manager)
        self.d5 = D5QuantDepartment(self.memory_manager)
        self.d6 = D6ICDepartment(self.memory_manager)
        self.d7 = D7StockSelectionDepartment(self.memory_manager)
        self.d4.uploaded_materials = old_d4_materials
        if old_d5_params:
            self.d5.params.update(old_d5_params)
        if old_d5_samples:
            self.d5.training_samples = old_d5_samples
        if old_d5_pending:
            self.d5._pending_sample = old_d5_pending
        if old_d5_report:
            self.d5.last_training_report = old_d5_report
        self.logger.info("Departments reloaded with latest runtime config")

    def _iso(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if isinstance(dt, datetime) else None

    def _parse_dt(self, raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw))
        except Exception:
            return None

    def _serialize_stock_case(self, case: StockCase) -> Dict[str, Any]:
        return case.to_dict()

    def _deserialize_stock_case(self, raw: Dict[str, Any]) -> StockCase:
        symbol = str(raw.get("symbol") or "").upper()
        case = StockCase(symbol=symbol)
        created = self._parse_dt(raw.get("created_at"))
        if created:
            case.created_at = created
        case.status = str(raw.get("status") or "active")
        case.latest_price = raw.get("latest_price")
        case.latest_market_timestamp = self._parse_dt(raw.get("latest_market_timestamp"))

        # 部门历史使用轻量对象恢复，供 D5/D6 与前端展示使用
        dept_raw = raw.get("department_finals") or {}
        case.department_finals = {k: _LiteDepartmentFinal(v) for k, v in dept_raw.items()}

        q = raw.get("quant_output") or None
        if q:
            try:
                case.quant_output = QuantOutput(
                    symbol=symbol,
                    timestamp=self._parse_dt(q.get("timestamp")) or datetime.now(),
                    market_alpha=float(q.get("market_alpha", 0.0) or 0.0),
                    research_gate=float(q.get("research_gate", 0.0) or 0.0),
                    final_alpha=float(q.get("final_alpha", 0.0) or 0.0),
                    position=float(q.get("position", 0.0) or 0.0),
                    volatility=float(q.get("volatility", 0.02) or 0.02),
                    whale_flow_score=float(q.get("whale_flow_score", 0.0) or 0.0),
                    research_score=float(q.get("research_score", 0.0) or 0.0),
                    divergence=float(q.get("divergence", 0.0) or 0.0),
                    event_risk=float(q.get("event_risk", 0.0) or 0.0),
                )
            except Exception:
                case.quant_output = None

        d = raw.get("trading_decision") or None
        if d:
            try:
                case.trading_decision = TradingDecision(
                    symbol=symbol,
                    timestamp=self._parse_dt(d.get("timestamp")) or datetime.now(),
                    direction=str(d.get("direction") or "NO_TRADE"),
                    target_position=float(d.get("target_position", 0.0) or 0.0),
                    execution_plan=dict(d.get("execution_plan") or {}),
                    risk_controls=dict(d.get("risk_controls") or {}),
                    rationale=str(d.get("rationale") or ""),
                    evidence_ids=list(d.get("evidence_ids") or []),
                    department_outputs=dict(d.get("department_outputs") or {}),
                )
            except Exception:
                case.trading_decision = None
        return case

    def _serialize_trading_engine(self) -> Dict[str, Any]:
        acc = self.trading_engine.account
        weekly = {}
        for sym, week_map in self.trading_engine.weekly_trade_days.items():
            weekly[sym] = {wk: sorted([d.isoformat() for d in days]) for wk, days in week_map.items()}
        return {
            "account": {
                "account_id": acc.account_id,
                "initial_capital": acc.initial_capital,
                "cash": acc.cash,
                "daily_pnl": acc.daily_pnl,
                "total_pnl": acc.total_pnl,
                "max_drawdown": acc.max_drawdown,
                "peak_value": acc.peak_value,
                "positions": {k: v.to_dict() for k, v in acc.positions.items()},
            },
            "trade_history": list(self.trading_engine.trade_history),
            "daily_trade_counts": dict(self.trading_engine.daily_trade_counts),
            "weekly_trade_days": weekly,
            "equity_history": list(getattr(self.trading_engine, "equity_history", []) or []),
        }

    def _deserialize_trading_engine(self, raw: Dict[str, Any]):
        acc = raw.get("account") or {}
        self.trading_engine.account.account_id = str(acc.get("account_id") or self.trading_engine.account.account_id)
        self.trading_engine.account.initial_capital = float(acc.get("initial_capital", self.trading_engine.account.initial_capital))
        self.trading_engine.account.cash = float(acc.get("cash", self.trading_engine.account.cash))
        self.trading_engine.account.daily_pnl = float(acc.get("daily_pnl", 0.0) or 0.0)
        self.trading_engine.account.total_pnl = float(acc.get("total_pnl", 0.0) or 0.0)
        self.trading_engine.account.max_drawdown = float(acc.get("max_drawdown", 0.0) or 0.0)
        self.trading_engine.account.peak_value = float(acc.get("peak_value", self.trading_engine.account.peak_value))
        pos_raw = acc.get("positions") or {}
        self.trading_engine.account.positions = {}
        for sym, p in pos_raw.items():
            self.trading_engine.account.positions[sym] = Position(
                symbol=str(sym).upper(),
                quantity=float(p.get("quantity", 0.0) or 0.0),
                avg_cost=float(p.get("avg_cost", 0.0) or 0.0),
                current_price=float(p.get("current_price", 0.0) or 0.0),
                market_value=float(p.get("market_value", 0.0) or 0.0),
                unrealized_pnl=float(p.get("unrealized_pnl", 0.0) or 0.0),
                realized_pnl=float(p.get("realized_pnl", 0.0) or 0.0),
            )

        self.trading_engine.trade_history = list(raw.get("trade_history") or [])
        self.trading_engine.daily_trade_counts = dict(raw.get("daily_trade_counts") or {})
        self.trading_engine.equity_history = list(raw.get("equity_history") or [])
        if not self.trading_engine.equity_history:
            self.trading_engine.record_equity_snapshot("restore_init")
        weekly_raw = raw.get("weekly_trade_days") or {}
        weekly_out = {}
        for sym, week_map in weekly_raw.items():
            weekly_out[sym] = {}
            for wk, day_list in (week_map or {}).items():
                weekly_out[sym][wk] = {datetime.fromisoformat(d).date() for d in (day_list or [])}
        self.trading_engine.weekly_trade_days = weekly_out

    def _serialize_memory_entries(self) -> List[Dict[str, Any]]:
        if not hasattr(self.memory_store, "_entries"):
            return []
        entries = list(getattr(self.memory_store, "_entries", {}).values())
        return [e.to_dict() for e in entries]

    def _deserialize_memory_entries(self, rows: List[Dict[str, Any]]):
        if not hasattr(self.memory_store, "_entries"):
            return
        target = {}
        for r in rows or []:
            try:
                entry = MemoryEntry(
                    entry_id=str(r.get("entry_id")),
                    memory_type=MemoryType(str(r.get("memory_type"))),
                    scope=MemoryScope(str(r.get("scope"))),
                    department=r.get("department"),
                    stock_symbol=r.get("stock_symbol"),
                    content=str(r.get("content") or ""),
                    metadata=dict(r.get("metadata") or {}),
                    created_at=self._parse_dt(r.get("created_at")) or datetime.now(),
                    expires_at=self._parse_dt(r.get("expires_at")),
                    importance=float(r.get("importance", 0.5) or 0.5),
                    access_count=int(r.get("access_count", 0) or 0),
                )
                target[entry.entry_id] = entry
            except Exception:
                continue
        self.memory_store._entries = target

    def _persist_runtime_state(self):
        payload = {
            "version": 2,
            "saved_at": datetime.now().isoformat(),
            "state": {
                "active_stocks": list(self.state.active_stocks),
                "last_run_times": {k: self._iso(v) for k, v in self.state.last_run_times.items()},
                "progress": self.state.progress,
                "d7_recommendations": self.state.d7_recommendations,
                "d7_history": self.state.d7_history,
                "jobs": self.state.jobs,
            },
            "stock_cases": [self._serialize_stock_case(c) for c in self.stock_cases.values()],
            "trading": self._serialize_trading_engine(),
            "memory_entries": self._serialize_memory_entries(),
            "market_cache": self.market_cache,
        }
        try:
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to persist runtime state: {e}")

    def _load_runtime_state(self):
        if not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            st = data.get("state") or {}
            self.state.active_stocks = [str(s).upper() for s in (st.get("active_stocks") or [])]
            self.state.last_run_times = {}
            for k, v in (st.get("last_run_times") or {}).items():
                dt = self._parse_dt(v)
                if dt:
                    self.state.last_run_times[k] = dt
            self.state.progress = st.get("progress") or {"global": {}, "stocks": {}, "d7": {"status": "idle", "message": ""}}
            self.state.d7_recommendations = st.get("d7_recommendations") or {"short": [], "mid": [], "long": []}
            self.state.d7_history = st.get("d7_history") or []
            self.state.jobs = st.get("jobs") or {}
            for job in self.state.jobs.values():
                if job.get("status") == "running":
                    job["status"] = "interrupted"
                    job["message"] = "Interrupted by restart"

            self.stock_cases = {}
            for raw in data.get("stock_cases") or []:
                case = self._deserialize_stock_case(raw)
                self.stock_cases[case.symbol] = case
            for sym in self.state.active_stocks:
                if sym not in self.stock_cases:
                    self.stock_cases[sym] = StockCase(symbol=sym)
            self._cleanup_orphan_stock_state()
            self._deserialize_trading_engine(data.get("trading") or {})
            # D4 用户原始粘贴材料不持久化：仅保留本次进程内队列
            self.d4.clear_materials()
            self._deserialize_memory_entries(data.get("memory_entries") or [])
            self.market_cache = dict(data.get("market_cache") or {})
            self.logger.info(
                "Loaded runtime state: stocks=%d, d7_history=%d, trades=%d",
                len(self.state.active_stocks),
                len(self.state.d7_history),
                len(self.trading_engine.trade_history),
            )
        except Exception as e:
            self.logger.warning(f"Failed to load runtime state: {e}")

    def save_runtime_state(self):
        """对外暴露的状态持久化入口"""
        self._persist_runtime_state()

    def _set_global_progress(self, department: str, status: str, message: str = ""):
        self.state.progress["global"][department] = {
            "status": status,
            "message": message,
            "updated_at": datetime.now().isoformat()
        }

    def _set_stock_progress(self, symbol: str, department: str, status: str, message: str = ""):
        if symbol not in self.state.progress["stocks"]:
            self.state.progress["stocks"][symbol] = {}
        self.state.progress["stocks"][symbol][department] = {
            "status": status,
            "message": message,
            "updated_at": datetime.now().isoformat()
        }

    def _reset_stock_cycle_progress(self, symbol: str, last_decision: str = ""):
        """单只股票完成一轮决策后，清空部门状态等待下一轮"""
        for dep in ("D1", "D2", "D3", "D4", "D5", "D6"):
            msg = "Waiting for next analysis cycle"
            if dep == "D6" and last_decision:
                msg = f"Last decision: {last_decision}; waiting for next analysis cycle"
            self._set_stock_progress(symbol, dep, "pending", msg)

    def _get_interval_minutes(self, dep: str) -> int:
        mapping = {
            "D1": config.d1_interval,
            "D2": config.d2_interval,
            "D3": config.d3_interval,
            "D4": config.d4_interval,
            "D5": config.d5_interval,
            "D6": config.d6_interval,
        }
        return int(mapping.get(dep, 60))

    def _build_next_run_item(self, dept_key: str, interval_minutes: int, now: datetime) -> Dict[str, Any]:
        last = self.state.last_run_times.get(dept_key)
        if not last:
            return {
                "last_run": None,
                "next_run": None,
                "seconds_left": 0,
                "due_now": True
            }
        next_run = last + timedelta(minutes=max(1, int(interval_minutes)))
        sec_left = int((next_run - now).total_seconds())
        if sec_left < 0:
            sec_left = 0
        return {
            "last_run": last.isoformat(),
            "next_run": next_run.isoformat(),
            "seconds_left": sec_left,
            "due_now": sec_left == 0
        }

    def _build_next_run_schedule(self) -> Dict[str, Any]:
        now = datetime.now()
        out: Dict[str, Any] = {
            "global": {},
            "stocks": {},
            "d7": {"manual_only": True}
        }
        out["global"]["D1"] = self._build_next_run_item("D1", self._get_interval_minutes("D1"), now)
        out["global"]["D5"] = self._build_next_run_item("D5", self._get_interval_minutes("D5"), now)
        for symbol in list(self.state.active_stocks):
            out["stocks"][symbol] = {
                "D2": self._build_next_run_item(f"D2_{symbol}", self._get_interval_minutes("D2"), now),
                "D3": self._build_next_run_item(f"D3_{symbol}", self._get_interval_minutes("D3"), now),
                "D4": self._build_next_run_item(f"D4_{symbol}", self._get_interval_minutes("D4"), now),
                "D5": self._build_next_run_item(f"D5_{symbol}", self._get_interval_minutes("D5"), now),
                "D6": self._build_next_run_item(f"D6_{symbol}", self._get_interval_minutes("D6"), now),
            }
        return out

    def _create_job(self, job_type: str) -> str:
        job_id = str(uuid.uuid4())
        self.state.jobs[job_id] = {
            "job_id": job_id,
            "type": job_type,
            "status": "running",
            "progress": 0,
            "stage": "starting",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "message": ""
        }
        return job_id

    def _find_running_job(self, job_type: str) -> Optional[str]:
        for jid, meta in self.state.jobs.items():
            if meta.get("type") == job_type and meta.get("status") == "running":
                return jid
        return None

    def _update_job(self, job_id: str, progress: Optional[int] = None, stage: Optional[str] = None, message: Optional[str] = None):
        if job_id not in self.state.jobs:
            return
        if progress is not None:
            self.state.jobs[job_id]["progress"] = max(0, min(100, progress))
        if stage is not None:
            self.state.jobs[job_id]["stage"] = stage
        if message is not None:
            self.state.jobs[job_id]["message"] = message

    def _finish_job(self, job_id: str, status: str, message: str = ""):
        if job_id in self.state.jobs:
            self.state.jobs[job_id]["status"] = status
            self.state.jobs[job_id]["message"] = message
            self.state.jobs[job_id]["finished_at"] = datetime.now().isoformat()
            self._persist_runtime_state()
    
    async def start(self):
        """启动调度器"""
        self.state.is_running = True
        self.logger.info("Trading platform scheduler started")
        
        # 启动主调度循环
        await self._run_scheduler()
    
    async def stop(self):
        """停止调度器"""
        self.state.is_running = False
        self._persist_runtime_state()
        self.logger.info("Trading platform scheduler stopped")
    
    async def _run_scheduler(self):
        """运行调度循环"""
        while self.state.is_running:
            try:
                # 检查并运行各部门
                await self._check_and_run_departments()
                
                # 短暂休眠
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)
    
    async def _check_and_run_departments(self):
        """检查并运行各部门"""
        now = datetime.now()

        # 股票池为空时，不运行 D1-D6/D5；D7 仅手动触发
        if not self.state.active_stocks:
            return
        
        # D5 量化 - 持续运行
        if self._should_run_department("D5", now, timedelta(minutes=config.d5_interval)):
            try:
                await self._run_d5_for_all_stocks()
            except Exception as e:
                self.logger.error(f"D5 scheduled run failed: {e}")
        
        # D1 宏观 - 每60分钟
        if self._should_run_department("D1", now, timedelta(minutes=config.d1_interval)):
            try:
                await self._run_d1()
            except Exception as e:
                self.logger.error(f"D1 scheduled run failed: {e}")
        
        # D2/D3/D4/D6 - 对每只股票运行
        for symbol in self.state.active_stocks:
            # D2 行业
            if self._should_run_department(f"D2_{symbol}", now, timedelta(minutes=config.d2_interval)):
                try:
                    await self._run_d2(symbol)
                except Exception as e:
                    self.logger.error(f"D2 scheduled run failed for {symbol}: {e}")
            
            # D3 单股
            if self._should_run_department(f"D3_{symbol}", now, timedelta(minutes=config.d3_interval)):
                try:
                    await self._run_d3(symbol)
                except Exception as e:
                    self.logger.error(f"D3 scheduled run failed for {symbol}: {e}")
            
            # D4 专家材料
            if self._should_run_department(f"D4_{symbol}", now, timedelta(minutes=config.d4_interval)):
                try:
                    await self._run_d4(symbol)
                except Exception as e:
                    self.logger.error(f"D4 scheduled run failed for {symbol}: {e}")
            
            # D6 投委会
            if self._should_run_department(f"D6_{symbol}", now, timedelta(minutes=config.d6_interval)):
                try:
                    await self._run_d6(symbol)
                except Exception as e:
                    self.logger.error(f"D6 scheduled run failed for {symbol}: {e}")
    
    def _should_run_department(self, dept_key: str, now: datetime, interval: timedelta) -> bool:
        """判断是否应该运行部门"""
        # 若上次状态为失败，则优先重试，不受冷却间隔限制
        if self._is_failed_department(dept_key):
            return True

        if dept_key not in self.state.last_run_times:
            return True
        
        last_run = self.state.last_run_times[dept_key]
        return (now - last_run) >= interval

    def _is_failed_department(self, dept_key: str) -> bool:
        """根据调度键判断对应部门当前是否为 failed。"""
        # 全局部门（如 D1）
        if "_" not in dept_key:
            status = (
                self.state.progress.get("global", {})
                .get(dept_key, {})
                .get("status", "")
            )
            return str(status).lower() == "failed"

        # 按股票部门（如 D2_AAPL、D6_MSFT）
        dep, symbol = dept_key.split("_", 1)
        status = (
            self.state.progress.get("stocks", {})
            .get(symbol, {})
            .get(dep, {})
            .get("status", "")
        )
        return str(status).lower() == "failed"
    
    async def _run_d7(self, progress_cb=None):
        """运行D7选股"""
        self.logger.info("Running D7 stock selection")
        
        candidates = await self.d7.select_stocks(top_k=30, progress_cb=progress_cb)
        pool_source = getattr(self.d7, "last_pool_source", "unknown")
        active_set = {s.upper() for s in self.state.active_stocks}
        recent_runs = self.state.d7_history[-5:]
        recent_set = {s.upper() for run in recent_runs for s in run}
        fresh = [c for c in candidates if c.symbol.upper() not in active_set and c.symbol.upper() not in recent_set]
        if len(fresh) < 8:
            backfill = [c for c in candidates if c.symbol.upper() not in active_set and c.symbol.upper() not in {x.symbol.upper() for x in fresh}]
            fresh.extend(backfill[: max(0, 8 - len(fresh))])
        buckets = {"short": [], "mid": [], "long": []}
        for c in fresh:
            buckets.setdefault(c.horizon, []).append(c)
        selected_candidates = []
        quota = {"short": 3, "mid": 3, "long": 2}
        for h in ("short", "mid", "long"):
            selected_candidates.extend(buckets.get(h, [])[:quota[h]])
        if len(selected_candidates) < 8:
            used = {x.symbol.upper() for x in selected_candidates}
            remains = [c for c in fresh if c.symbol.upper() not in used]
            selected_candidates.extend(remains[: max(0, 8 - len(selected_candidates))])
        selected_candidates = selected_candidates[:8]

        grouped = {"short": [], "mid": [], "long": []}
        for c in selected_candidates:
            item = {
                "symbol": c.symbol,
                "name": c.name,
                "horizon": c.horizon,
                "score": c.score,
                "why_now": c.why_now,
                "risk_score": c.risk_score,
                "selected": False
            }
            grouped.setdefault(c.horizon, []).append(item)

        self.state.d7_recommendations = grouped
        self._prune_d7_recommendations()
        picked_symbols = [c.symbol for c in selected_candidates]
        self.state.d7_history.append(picked_symbols)
        self.state.d7_history = self.state.d7_history[-20:]
        
        self.state.last_run_times["D7"] = datetime.now()
        self.logger.info(f"D7 selected {len(selected_candidates)} stocks ({pool_source}): {picked_symbols}")
        self._persist_runtime_state()
        return picked_symbols

    def run_d7_manual(self) -> str:
        """手动触发 D7 选股（异步任务）"""
        running = self._find_running_job("run_d7")
        if running:
            return running
        job_id = self._create_job("run_d7")
        asyncio.create_task(self._run_d7_job(job_id))
        return job_id

    async def _run_d7_job(self, job_id: str):
        try:
            self.state.progress["d7"] = {
                "status": "running",
                "message": "Step 1/4: 收集候选股票池",
                "stage": "collecting",
                "progress": 10,
                "updated_at": datetime.now().isoformat()
            }
            self._update_job(job_id, progress=10, stage="collecting", message="Collecting candidate universe")
            await asyncio.sleep(1.2)

            self.state.progress["d7"] = {
                "status": "running",
                "message": "Step 2/4: 多维度评分中",
                "stage": "scoring",
                "progress": 45,
                "updated_at": datetime.now().isoformat()
            }
            self._update_job(job_id, progress=45, stage="scoring", message="Scoring candidates")
            await asyncio.sleep(0.6)

            self.state.progress["d7"] = {
                "status": "running",
                "message": "Step 3/4: 按短/中/长分组",
                "stage": "grouping",
                "progress": 75,
                "updated_at": datetime.now().isoformat()
            }
            self._update_job(job_id, progress=75, stage="grouping", message="Grouping by horizons")

            def _on_candidate_scored(done: int, total: int, symbol: str):
                base = 45
                span = 40
                frac = 0 if total <= 0 else done / total
                p = base + int(span * frac)
                self.state.progress["d7"] = {
                    "status": "running",
                    "message": f"Step 2/4: 评分中 {done}/{total} · {symbol}",
                    "stage": "scoring",
                    "progress": p,
                    "updated_at": datetime.now().isoformat()
                }
                self._update_job(job_id, progress=p, stage="scoring", message=f"Scored {done}/{total}: {symbol}")

            symbols = await self._run_d7(progress_cb=_on_candidate_scored)
            pool_source = getattr(self.d7, "last_pool_source", "unknown")
            await asyncio.sleep(0.8)
            self.state.progress["d7"] = {
                "status": "completed",
                "message": f"Step 4/4: 完成，生成 {len(symbols)} 条推荐（source={pool_source}）",
                "stage": "completed",
                "progress": 100,
                "updated_at": datetime.now().isoformat()
            }
            self._update_job(job_id, progress=100, stage="completed", message=f"D7 completed ({pool_source}): {', '.join(symbols)}")
            self._finish_job(job_id, "completed", f"D7 completed ({pool_source}): {', '.join(symbols)}")
        except Exception as e:
            self.state.progress["d7"] = {
                "status": "failed",
                "message": str(e),
                "stage": "failed",
                "progress": 100,
                "updated_at": datetime.now().isoformat()
            }
            self._finish_job(job_id, "failed", str(e))

    def run_once_manual(self) -> str:
        """手动执行一轮（D1/D2/D3/D4/D5/D6）（异步任务）"""
        running = self._find_running_job("run_once")
        if running:
            return running
        job_id = self._create_job("run_once")
        asyncio.create_task(self._run_once_job(job_id))
        return job_id

    async def _run_once_job(self, job_id: str):
        if not self.state.active_stocks:
            self._finish_job(job_id, "completed", "No active stocks")
            return

        errors: List[str] = []
        dept_timeout = 95
        try:
            self._update_job(job_id, progress=5, stage="d1", message="Running D1")
            try:
                await asyncio.wait_for(self._run_d1(), timeout=dept_timeout)
            except Exception as e:
                errors.append(f"D1:{e}")

            self._update_job(job_id, progress=20, stage="d5", message="Running D5")
            try:
                await asyncio.wait_for(self._run_d5_for_all_stocks(), timeout=dept_timeout)
            except Exception as e:
                errors.append(f"D5:{e}")

            symbols = list(self.state.active_stocks)
            total_steps = max(1, len(symbols) * 4)
            done_steps = 0
            for symbol in symbols:
                for dept, fn in [("D2", self._run_d2), ("D3", self._run_d3), ("D4", self._run_d4), ("D6", self._run_d6)]:
                    done_steps += 1
                    p = 20 + int(75 * done_steps / total_steps)
                    self._update_job(job_id, progress=p, stage=f"{dept}_{symbol}", message=f"Running {dept} for {symbol}")
                    try:
                        await asyncio.wait_for(fn(symbol), timeout=dept_timeout)
                    except Exception as e:
                        errors.append(f"{dept}_{symbol}:{e}")

            if errors:
                self._finish_job(job_id, "failed", "; ".join(errors[:6]))
            else:
                self._finish_job(job_id, "completed", f"Run once completed for {len(self.state.active_stocks)} stocks")
        except Exception as e:
            self._finish_job(job_id, "failed", f"Unexpected error: {e}")
        try:
            if self.state.jobs.get(job_id, {}).get("status") == "running":
                self._finish_job(job_id, "failed", "Run-once ended without terminal state")
        except Exception:
            pass
    
    async def _run_d1(self):
        """运行D1宏观"""
        self._set_global_progress("D1", "running", "Macro analysis in progress")
        self.logger.info("Running D1 macro analysis")
        try:
            dept_final = await self.d1.run_three_round_discussion()
            
            # D1是全局的，存储到所有股票案例中
            for symbol in self.state.active_stocks:
                if symbol in self.stock_cases:
                    self.stock_cases[symbol].department_finals["D1"] = dept_final
                    self._set_stock_progress(symbol, "D1", "completed", "Macro context updated")
            
            self.state.last_run_times["D1"] = datetime.now()
            self._set_global_progress("D1", "completed", "Macro analysis completed")
            self._persist_runtime_state()
        except Exception as e:
            self._set_global_progress("D1", "failed", str(e))
            for symbol in self.state.active_stocks:
                self._set_stock_progress(symbol, "D1", "failed", str(e))
            raise
    
    async def _run_d2(self, symbol: str):
        """运行D2行业"""
        self._set_stock_progress(symbol, "D2", "running", "Industry analysis in progress")
        self.logger.info(f"Running D2 industry analysis for {symbol}")
        try:
            dept_final = await self.d2.run_three_round_discussion(stock_symbol=symbol)
            
            if symbol in self.stock_cases:
                self.stock_cases[symbol].department_finals["D2"] = dept_final
            
            self.state.last_run_times[f"D2_{symbol}"] = datetime.now()
            self._set_stock_progress(symbol, "D2", "completed", "Industry analysis completed")
            self._persist_runtime_state()
        except Exception as e:
            self._set_stock_progress(symbol, "D2", "failed", str(e))
            raise
    
    async def _run_d3(self, symbol: str):
        """运行D3单股"""
        self._set_stock_progress(symbol, "D3", "running", "Stock-specific analysis in progress")
        self.logger.info(f"Running D3 stock analysis for {symbol}")
        try:
            dept_final = await self.d3.run_three_round_discussion(stock_symbol=symbol)
            
            if symbol in self.stock_cases:
                self.stock_cases[symbol].department_finals["D3"] = dept_final
            
            self.state.last_run_times[f"D3_{symbol}"] = datetime.now()
            self._set_stock_progress(symbol, "D3", "completed", "Stock-specific analysis completed")
            self._persist_runtime_state()
        except Exception as e:
            self._set_stock_progress(symbol, "D3", "failed", str(e))
            raise
    
    async def _run_d4(self, symbol: str):
        """运行D4专家材料"""
        self._set_stock_progress(symbol, "D4", "running", "Expert material analysis in progress")
        self.logger.info(f"Running D4 expert analysis for {symbol}")
        try:
            dept_final = await self.d4.run_three_round_discussion(stock_symbol=symbol)
            
            if symbol in self.stock_cases:
                self.stock_cases[symbol].department_finals["D4"] = dept_final
            
            self.state.last_run_times[f"D4_{symbol}"] = datetime.now()
            self._set_stock_progress(symbol, "D4", "completed", "Expert analysis completed")
            self._persist_runtime_state()
        except Exception as e:
            self._set_stock_progress(symbol, "D4", "failed", str(e))
            raise
    
    async def _run_d5_for_all_stocks(self):
        """为所有股票运行D5量化"""
        symbols = list(self.state.active_stocks)
        if not symbols:
            return

        # D5 对每只股票是独立计算，可并发执行，避免“排队感”
        tasks = [self._run_d5(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                self.logger.error(f"D5 run failed for {symbol}: {result}")
        self.trading_engine.record_equity_snapshot("d5_cycle")
    
    async def _run_d5(self, symbol: str):
        """运行D5量化"""
        self._set_stock_progress(symbol, "D5", "running", "Quant signal generation in progress")
        self.logger.info(f"Running D5 quant analysis for {symbol}")
        try:
            # 获取市场数据和资金流（模拟数据）
            market_data, whale_flow = await self._get_market_data(symbol)
            
            # 获取部门结论
            dept_finals = {}
            if symbol in self.stock_cases:
                dept_finals = self.stock_cases[symbol].department_finals
            
            # 计算量化输出
            quant_output = await self.d5.calculate_quant_output(
                symbol=symbol,
                market_data=market_data,
                whale_flow=whale_flow,
                department_finals=dept_finals
            )
            
            if symbol in self.stock_cases:
                self.stock_cases[symbol].quant_output = quant_output
                self.stock_cases[symbol].latest_price = market_data.price
                self.stock_cases[symbol].latest_market_timestamp = market_data.timestamp
            decision_direction = ""
            if symbol in self.stock_cases and self.stock_cases[symbol].trading_decision:
                decision_direction = str(self.stock_cases[symbol].trading_decision.direction or "")
            if symbol in self.trading_engine.account.positions:
                pos = self.trading_engine.account.positions[symbol]
                self.trading_engine.mark_to_market(symbol, market_data.price)
                pnl_ratio = 0.0
                base_mv = max(1e-9, abs(pos.market_value))
                if base_mv > 1e-9:
                    pnl_ratio = float(pos.unrealized_pnl) / base_mv
                self.memory_manager.apply_trade_feedback(
                    symbol=symbol,
                    pnl_ratio=pnl_ratio,
                    decision_direction=decision_direction,
                    as_of=datetime.now()
                )
            
            self.state.last_run_times[f"D5_{symbol}"] = datetime.now()
            self._set_stock_progress(symbol, "D5", "completed", "Quant output completed")
            self._persist_runtime_state()
        except Exception as e:
            self._set_stock_progress(symbol, "D5", "failed", str(e))
            raise
    
    async def _run_d6(self, symbol: str):
        """运行D6投委会"""
        self._set_stock_progress(symbol, "D6", "running", "IC decision in progress")
        self.logger.info(f"Running D6 IC decision for {symbol}")
        try:
            # 检查事件触发冷却
            if not self._check_event_cooldown(symbol):
                self.logger.info(f"D6 for {symbol} is in cooldown")
                self._set_stock_progress(symbol, "D6", "skipped", "In cooldown")
                return
            
            # 获取部门结论和量化输出
            dept_finals = {}
            quant_output = None
            
            if symbol in self.stock_cases:
                dept_finals = self.stock_cases[symbol].department_finals
                quant_output = self.stock_cases[symbol].quant_output
            
            if not dept_finals or not quant_output:
                self.logger.warning(f"Insufficient data for D6 decision on {symbol}")
                self._set_stock_progress(symbol, "D6", "skipped", "Insufficient department or quant data")
                return
            
            # 获取当前持仓
            current_position = 0.0
            if symbol in self.trading_engine.account.positions:
                pos = self.trading_engine.account.positions[symbol]
                current_position = pos.quantity * pos.current_price / self.trading_engine.account.total_value
            
            # 做出决策
            decision = await self.d6.make_decision(
                symbol=symbol,
                department_finals=dept_finals,
                quant_output=quant_output,
                current_position=current_position
            )
            
            if symbol in self.stock_cases:
                self.stock_cases[symbol].trading_decision = decision
            
            # 执行交易
            await self._execute_trade(decision, symbol)

            self.state.last_run_times[f"D6_{symbol}"] = datetime.now()
            # 完成一轮后清空状态，进入下一轮倒计时
            self._reset_stock_cycle_progress(symbol, last_decision=decision.direction)
            pool_action = str((decision.execution_plan or {}).get("pool_action", "keep")).strip().lower()
            if pool_action == "remove_if_flat" and self._is_flat_position(symbol):
                self.logger.info("Auto-removing %s from active stocks based on D6 pool_action=remove_if_flat", symbol)
                self.remove_stock(symbol)
            self._persist_runtime_state()
        except Exception as e:
            self._set_stock_progress(symbol, "D6", "failed", str(e))
            raise
    
    def _check_event_cooldown(self, symbol: str) -> bool:
        """检查事件触发冷却时间"""
        now = datetime.now()
        
        if symbol in self.event_cooldowns:
            last_trigger = self.event_cooldowns[symbol]
            if (now - last_trigger).total_seconds() < config.event_cooldown * 60:
                return False
        
        self.event_cooldowns[symbol] = now
        return True

    async def _estimate_large_prints_from_yahoo(self, symbol: str, timeout_sec: int = 10) -> Dict[str, float]:
        """
        基于 Yahoo 1m 全日序列近似“逐笔成交记录”，并自适应大单阈值：
        - baseline: 50万美元
        - adaptive: max(50万, 当日1m成交额P95, 当日总成交额0.2%)
        """
        import aiohttp

        y_symbol = symbol.replace(".", "-").upper()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_symbol}?interval=1m&range=1d&includePrePost=false"
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"yahoo chart status={resp.status}")
                data = await resp.json()
        result = (((data or {}).get("chart") or {}).get("result") or [None])[0]
        if not result:
            raise RuntimeError("empty chart")
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = list(quote.get("close") or [])
        vols = list(quote.get("volume") or [])
        notionals: List[float] = []
        total_volume = 0.0
        total_notional = 0.0
        prev_close = None
        n = min(len(closes), len(vols))
        for i in range(n):
            c = closes[i]
            v = vols[i]
            if c is None or v is None:
                continue
            c = float(c)
            v = float(v)
            if c <= 0 or v <= 0:
                prev_close = c if c > 0 else prev_close
                continue
            notional = c * v
            total_volume += v
            total_notional += notional
            notionals.append(notional)
            prev_close = c
        if not notionals:
            return {
                "threshold_usd": 500000.0,
                "large_trade_count": 0.0,
                "large_trade_notional": 0.0,
                "large_trade_net": 0.0,
                "adv": 1.0,
                "adv_dollar": 1.0,
            }
        sorted_notionals = sorted(notionals)
        p95_index = min(len(sorted_notionals) - 1, int(0.95 * (len(sorted_notionals) - 1)))
        p95_notional = float(sorted_notionals[p95_index])
        threshold = float(max(500000.0, p95_notional, total_notional * 0.002))
        large_count = 0
        large_notional = 0.0
        large_net = 0.0
        prev_close = None
        for i in range(n):
            c = closes[i]
            v = vols[i]
            if c is None or v is None:
                continue
            c = float(c)
            v = float(v)
            if c <= 0 or v <= 0:
                prev_close = c if c > 0 else prev_close
                continue
            notional = c * v
            if notional >= threshold:
                large_count += 1
                large_notional += notional
                signed = 1.0 if (prev_close is None or c >= prev_close) else -1.0
                large_net += signed * notional
            prev_close = c
        return {
            "threshold_usd": threshold,
            "large_trade_count": float(large_count),
            "large_trade_notional": float(large_notional),
            "large_trade_net": float(large_net),
            "adv": float(max(total_volume, 1.0)),
            "adv_dollar": float(max(total_notional, 1.0)),
        }
    
    async def _get_market_data(self, symbol: str):
        """获取市场数据（Stooq优先，Yahoo兜底，失败时仅用缓存真实数据）。"""
        from models.base_models import MarketData, WhaleFlow
        import aiohttp
        import csv
        from io import StringIO
        y_symbol = symbol.replace(".", "-").upper()
        stooq_symbol = f"{symbol.replace('.', '-').lower()}.us"
        try:
            # 1) Stooq（稳定且无需key）
            stooq_url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(stooq_url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status == 200:
                        txt = await resp.text()
                        rows = list(csv.reader(StringIO(txt)))
                        if len(rows) >= 2 and len(rows[1]) >= 8:
                            r = [x.strip() for x in rows[1]]
                            close_s = r[6]
                            if close_s not in ("N/D", "-", ""):
                                open_v = float(r[3])
                                high_v = float(r[4])
                                low_v = float(r[5])
                                close_v = float(close_s)
                                vol_v = float(r[7]) if r[7] not in ("N/D", "-", "") else 0.0
                                market_data = MarketData(
                                    symbol=symbol,
                                    timestamp=datetime.now(),
                                    price=close_v,
                                    volume=max(vol_v, 1.0),
                                    vwap=(open_v + high_v + low_v + close_v) / 4.0,
                                    bid_price=close_v * 0.999,
                                    ask_price=close_v * 1.001,
                                    bid_size=max(8000.0, vol_v * 0.002),
                                    ask_size=max(8000.0, vol_v * 0.002)
                                )
                                adv = max(vol_v, 1_000_000.0)
                                adv_dollar = max(close_v * adv, 1_000_000.0)
                                chg_pct = ((close_v - open_v) / open_v * 100.0) if open_v > 0 else 0.0
                                # 优先用 Yahoo 全日1m成交记录估算大单流；失败再用价格变化近似
                                large_stats = {}
                                try:
                                    large_stats = await self._estimate_large_prints_from_yahoo(symbol)
                                except Exception:
                                    large_stats = {}
                                adv_dollar_used = float(large_stats.get("adv_dollar", adv_dollar))
                                block_net = float(large_stats.get("large_trade_net", (close_v - open_v) * adv * 0.08))
                                large_notional = float(
                                    large_stats.get("large_trade_notional", abs(chg_pct) / 100.0 * adv_dollar_used * 0.5)
                                )
                                whale_flow = WhaleFlow(
                                    symbol=symbol,
                                    timestamp=datetime.now(),
                                    block_net_buy_value=block_net,
                                    dark_pool_net=block_net * 0.15,
                                    options_whale_notional=large_notional * 0.12,
                                    adv=max(adv_dollar_used, 1.0)
                                )
                                cached_meta = self.market_cache.get(symbol) or {}
                                market_cap = cached_meta.get("market_cap")
                                short_name = str(cached_meta.get("short_name") or symbol)
                                try:
                                    quote_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={y_symbol}"
                                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                                    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                                        async with session.get(quote_url) as q_resp:
                                            if q_resp.status == 200:
                                                q_data = await q_resp.json()
                                                row = (((q_data or {}).get("quoteResponse") or {}).get("result") or [None])[0]
                                                if row:
                                                    market_cap = float(row.get("marketCap") or 0.0) or None
                                                    short_name = str(row.get("shortName") or row.get("longName") or symbol)
                                except Exception:
                                    pass
                                self.market_cache[symbol] = {
                                    "price": close_v,
                                    "ts": datetime.now().isoformat(),
                                    "source": "stooq",
                                    "change_percent": chg_pct,
                                    "market_cap": market_cap,
                                    "avg_volume_3m": adv,
                                    "avg_volume_3m_dollar": adv_dollar_used,
                                    "short_name": short_name,
                                    "large_trade_threshold_usd": float(large_stats.get("threshold_usd", max(500000.0, adv_dollar_used * 0.002))),
                                    "large_trade_count": int(large_stats.get("large_trade_count", max(0, int(abs((close_v - open_v) * adv) / 500000.0)))),
                                    "large_trade_notional": float(large_stats.get("large_trade_notional", abs((close_v - open_v) * adv))),
                                    "large_trade_net": float(large_stats.get("large_trade_net", (close_v - open_v) * adv * 0.35)),
                                    "tape_source": "yahoo_chart_1m"
                                }
                                return market_data, whale_flow

            # 2) Yahoo Chart 兜底（无需 quote v7）
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_symbol}?interval=1m&range=1d&includePrePost=false"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(chart_url) as resp:
                    if resp.status == 200:
                        chart_data = await resp.json()
                        result = (((chart_data or {}).get("chart") or {}).get("result") or [None])[0]
                        if result:
                            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
                            closes = list(quote.get("close") or [])
                            vols = list(quote.get("volume") or [])
                            valid = []
                            n = min(len(closes), len(vols))
                            for i in range(n):
                                c = closes[i]
                                v = vols[i]
                                if c is None or v is None:
                                    continue
                                c = float(c)
                                v = float(v)
                                if c <= 0:
                                    continue
                                valid.append((c, max(v, 0.0)))
                            if valid:
                                open_v = float(valid[0][0])
                                close_v = float(valid[-1][0])
                                vol_v = float(sum(v for _, v in valid))
                                adv = max(vol_v, 1_000_000.0)
                                adv_dollar = max(close_v * adv, 1_000_000.0)
                                chg_pct = ((close_v - open_v) / open_v * 100.0) if open_v > 0 else 0.0

                                market_data = MarketData(
                                    symbol=symbol,
                                    timestamp=datetime.now(),
                                    price=close_v,
                                    volume=max(vol_v, 1.0),
                                    vwap=(open_v + close_v) / 2.0,
                                    bid_price=close_v * 0.9995,
                                    ask_price=close_v * 1.0005,
                                    bid_size=max(12000.0, vol_v * 0.0015),
                                    ask_size=max(12000.0, vol_v * 0.0015),
                                )
                                large_stats = {}
                                try:
                                    large_stats = await self._estimate_large_prints_from_yahoo(symbol)
                                except Exception:
                                    large_stats = {}
                                adv_dollar_used = float(large_stats.get("adv_dollar", adv_dollar))
                                block_net = float(large_stats.get("large_trade_net", (close_v - open_v) * adv * 0.08))
                                large_notional = float(
                                    large_stats.get("large_trade_notional", abs(chg_pct) / 100.0 * adv_dollar_used * 0.5)
                                )
                                whale_flow = WhaleFlow(
                                    symbol=symbol,
                                    timestamp=datetime.now(),
                                    block_net_buy_value=block_net,
                                    dark_pool_net=block_net * 0.15,
                                    options_whale_notional=large_notional * 0.12,
                                    adv=max(adv_dollar_used, 1.0)
                                )
                                cached_meta = self.market_cache.get(symbol) or {}
                                self.market_cache[symbol] = {
                                    "price": close_v,
                                    "ts": datetime.now().isoformat(),
                                    "source": "yahoo_chart",
                                    "change_percent": chg_pct,
                                    "market_cap": cached_meta.get("market_cap"),
                                    "avg_volume_3m": adv,
                                    "avg_volume_3m_dollar": adv_dollar_used,
                                    "short_name": str(cached_meta.get("short_name") or symbol),
                                    "large_trade_threshold_usd": float(large_stats.get("threshold_usd", max(500000.0, adv_dollar_used * 0.002))),
                                    "large_trade_count": int(large_stats.get("large_trade_count", 0)),
                                    "large_trade_notional": float(large_stats.get("large_trade_notional", 0.0)),
                                    "large_trade_net": float(large_stats.get("large_trade_net", 0.0)),
                                    "tape_source": "yahoo_chart_1m"
                                }
                                return market_data, whale_flow

            # 3) Yahoo quote v7 兜底
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={y_symbol}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"quote status={resp.status}")
                    data = await resp.json()
            row = (((data or {}).get("quoteResponse") or {}).get("result") or [None])[0]
            if not row:
                raise RuntimeError("empty quote")
            price = float(row.get("regularMarketPrice") or 0.0)
            if price <= 0:
                raise RuntimeError("invalid price")
            volume = float(row.get("regularMarketVolume") or 0.0)
            bid = float(row.get("bid") or 0.0)
            ask = float(row.get("ask") or 0.0)
            if bid <= 0 or ask <= 0:
                bid = price * 0.9995
                ask = price * 1.0005
            bid_sz = float(row.get("bidSize") or 20000.0)
            ask_sz = float(row.get("askSize") or 20000.0)
            vwap = float(row.get("regularMarketPrice") or price)
            adv = float(row.get("averageDailyVolume3Month") or volume or 1_000_000.0)
            adv_dollar = max(price * adv, 1_000_000.0)
            chg_pct = float(row.get("regularMarketChangePercent") or 0.0)
            cap = float(row.get("marketCap") or 0.0)
            short_name = str(row.get("shortName") or row.get("longName") or symbol)
            prev = self.market_cache.get(symbol, {}).get("price", price)
            delta = price - prev

            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=price,
                volume=volume if volume > 0 else adv,
                vwap=vwap,
                bid_price=bid,
                ask_price=ask,
                bid_size=bid_sz if bid_sz > 0 else 20000.0,
                ask_size=ask_sz if ask_sz > 0 else 20000.0
            )
            large_stats = {}
            try:
                large_stats = await self._estimate_large_prints_from_yahoo(symbol)
            except Exception:
                large_stats = {}
            adv_dollar_used = float(large_stats.get("adv_dollar", adv_dollar))
            block_net = float(large_stats.get("large_trade_net", delta * adv * 0.08))
            large_notional = float(
                large_stats.get("large_trade_notional", abs(chg_pct) / 100.0 * adv_dollar_used * 0.5)
            )
            whale_flow = WhaleFlow(
                symbol=symbol,
                timestamp=datetime.now(),
                block_net_buy_value=block_net,
                dark_pool_net=block_net * 0.15,
                options_whale_notional=large_notional * 0.12,
                adv=max(adv_dollar_used, 1.0)
            )
            self.market_cache[symbol] = {
                "price": price,
                "ts": datetime.now().isoformat(),
                "source": "yahoo",
                "change_percent": chg_pct,
                "market_cap": cap if cap > 0 else None,
                "avg_volume_3m": adv if adv > 0 else None,
                "avg_volume_3m_dollar": adv_dollar_used,
                "short_name": short_name,
                "large_trade_threshold_usd": float(large_stats.get("threshold_usd", max(500000.0, adv_dollar_used * 0.002))),
                "large_trade_count": int(large_stats.get("large_trade_count", max(0, int(abs(delta * adv) / 500000.0)))),
                "large_trade_notional": float(large_stats.get("large_trade_notional", abs(delta * adv))),
                "large_trade_net": float(large_stats.get("large_trade_net", delta * adv * 0.35)),
                "tape_source": "yahoo_chart_1m"
            }
            return market_data, whale_flow
        except Exception as e:
            # 严格降级：仅使用已缓存真实行情；不再生成随机“假数据”
            cached = self.market_cache.get(symbol, {})
            cached_price = cached.get("price")
            if cached_price is None:
                raise RuntimeError(f"Market data unavailable for {symbol}") from e
            price = float(cached_price)
            volume = float(cached.get("avg_volume_3m") or 1_000_000.0)
            chg_pct = float(cached.get("change_percent") or 0.0)
            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=price,
                volume=volume,
                vwap=price,
                bid_price=price * 0.9995,
                ask_price=price * 1.0005,
                bid_size=12000.0,
                ask_size=12000.0
            )
            whale_flow = WhaleFlow(
                symbol=symbol,
                timestamp=datetime.now(),
                block_net_buy_value=0.0,
                dark_pool_net=0.0,
                options_whale_notional=0.0,
                adv=max(volume, 1.0)
            )
            self.market_cache[symbol]["source"] = str(cached.get("source") or "cached_fallback")
            self.market_cache[symbol]["change_percent"] = chg_pct
            return market_data, whale_flow
    
    async def _execute_trade(self, decision: TradingDecision, symbol: str):
        """执行交易"""
        if decision.direction == "NO_TRADE":
            self.logger.info(f"No trade for {symbol}: {decision.rationale}")
            return
        
        # 获取当前价格（模拟）
        market_data, _ = await self._get_market_data(symbol)
        current_price = market_data.price
        
        # 执行交易
        order = await self.trading_engine.execute_decision(decision, current_price)
        if symbol in self.trading_engine.account.positions:
            pos = self.trading_engine.account.positions[symbol]
            base_mv = max(1e-9, abs(pos.market_value))
            pnl_ratio = (float(pos.unrealized_pnl) / base_mv) if base_mv > 1e-9 else 0.0
            self.memory_manager.apply_trade_feedback(
                symbol=symbol,
                pnl_ratio=pnl_ratio,
                decision_direction=decision.direction,
                as_of=datetime.now()
            )
        
        self.logger.info(
            f"Executed trade for {symbol}: {order.side} {order.filled_quantity} @ {order.filled_price}"
        )
        self._persist_runtime_state()

    def _normalize_symbol(self, symbol: str) -> str:
        s = str(symbol or "").upper().strip()
        if not s:
            raise ValueError("Stock symbol is empty")
        if not re.match(r"^[A-Z][A-Z0-9\.\-]{0,9}$", s):
            raise ValueError(f"Invalid stock symbol format: {symbol}")
        return s

    async def validate_symbol_exists(self, symbol: str) -> bool:
        """严格验证股票代码是否可被真实行情源识别（不使用随机/缓存降级）"""
        import aiohttp
        import csv
        from io import StringIO

        s = self._normalize_symbol(symbol)
        y_symbol = s.replace(".", "-").upper()
        stooq_symbol = f"{s.replace('.', '-').lower()}.us"
        timeout = aiohttp.ClientTimeout(total=8)

        # 1) Stooq
        try:
            stooq_url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(stooq_url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status == 200:
                        txt = await resp.text()
                        rows = list(csv.reader(StringIO(txt)))
                        if len(rows) >= 2 and len(rows[1]) >= 8:
                            close_s = str(rows[1][6]).strip()
                            if close_s not in ("N/D", "-", ""):
                                return True
        except Exception:
            pass

        # 2) Yahoo quote v7
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={y_symbol}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        data = None
                    else:
                        data = await resp.json()
            if not data:
                raise RuntimeError("quote_v7_unavailable")
            row = (((data or {}).get("quoteResponse") or {}).get("result") or [None])[0]
            if not row:
                raise RuntimeError("quote_v7_empty")
            price = float(row.get("regularMarketPrice") or 0.0)
            return price > 0
        except Exception:
            pass

        # 3) Yahoo chart v8 fallback（v7 在部分网络环境会 401）
        try:
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_symbol}?interval=1d&range=5d&includePrePost=false"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(chart_url) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
            result = (((data or {}).get("chart") or {}).get("result") or [None])[0]
            if not result:
                return False
            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            closes = list(quote.get("close") or [])
            for c in closes:
                if c is None:
                    continue
                if float(c) > 0:
                    return True
            return False
        except Exception:
            return False

    def _is_flat_position(self, symbol: str) -> bool:
        """判断当前是否空仓。不存在持仓记录也视为0仓位。"""
        pos = self.trading_engine.account.positions.get(symbol)
        if not pos:
            return True
        return abs(float(getattr(pos, "quantity", 0.0) or 0.0)) < 1e-9

    def _prune_d7_recommendations(self):
        """清理推荐池：去重、移除已在股票池中的标的。"""
        active = {s.upper() for s in self.state.active_stocks}
        seen = set()
        pruned = {"short": [], "mid": [], "long": []}
        for bucket_name in ("short", "mid", "long"):
            for item in self.state.d7_recommendations.get(bucket_name, []) or []:
                sym = str(item.get("symbol", "")).upper().strip()
                if not sym or sym in active or sym in seen:
                    continue
                seen.add(sym)
                cp = dict(item)
                cp["symbol"] = sym
                cp["selected"] = False
                pruned[bucket_name].append(cp)
        self.state.d7_recommendations = pruned

    def add_stock(self, symbol: str):
        """手动添加股票"""
        symbol = self._normalize_symbol(symbol)
        if symbol not in self.state.active_stocks:
            self.state.active_stocks.append(symbol)
            self.stock_cases[symbol] = StockCase(symbol=symbol)
            self.state.progress["stocks"][symbol] = {}
            self._prune_d7_recommendations()
            self.logger.info(f"Added stock: {symbol}")
            self._persist_runtime_state()
        return symbol

    def _clear_symbol_runtime(self, symbol: str):
        # 清理每股部门最近运行时间，避免已移除股票仍参与倒计时与调度判断
        for dep in ("D2", "D3", "D4", "D5", "D6"):
            self.state.last_run_times.pop(f"{dep}_{symbol}", None)
        self.event_cooldowns.pop(symbol, None)
        self.market_cache.pop(symbol, None)

        # 清理 D5 该股票训练上下文
        try:
            self.d5._pending_sample.pop(symbol, None)
            self.d5._last_price.pop(symbol, None)
            self.d5._ret_windows.pop(symbol, None)
            self.d5.training_samples = [x for x in self.d5.training_samples if str(x.get("symbol", "")).upper() != symbol]
        except Exception:
            pass

        # 清理 D7 推荐与历史中的该股票
        for k in ("short", "mid", "long"):
            self.state.d7_recommendations[k] = [
                item for item in self.state.d7_recommendations.get(k, [])
                if str(item.get("symbol", "")).upper() != symbol
            ]
        self.state.d7_history = [[s for s in run if str(s).upper() != symbol] for run in self.state.d7_history]

        # 清理 memory 中该股票的条目
        if hasattr(self.memory_store, "_entries"):
            to_del = [eid for eid, e in self.memory_store._entries.items() if str(getattr(e, "stock_symbol", "")).upper() == symbol]
            for eid in to_del:
                self.memory_store._entries.pop(eid, None)

    def _cleanup_orphan_stock_state(self):
        """清理不在 active_stocks 内的遗留股票状态"""
        active = {s.upper() for s in self.state.active_stocks}
        stale = [s for s in list(self.state.progress.get("stocks", {}).keys()) if s.upper() not in active]
        for sym in stale:
            self.state.progress["stocks"].pop(sym, None)
            self._clear_symbol_runtime(sym.upper())

    def remove_stock(self, symbol: str):
        """移除股票"""
        symbol = self._normalize_symbol(symbol)
        if symbol in self.state.active_stocks:
            self.state.active_stocks.remove(symbol)
            if symbol in self.stock_cases:
                del self.stock_cases[symbol]
            if symbol in self.state.progress["stocks"]:
                del self.state.progress["stocks"][symbol]
            self._clear_symbol_runtime(symbol)
            self.logger.info(f"Removed stock: {symbol}")
            self._persist_runtime_state()
            return True
        return False

    def get_progress(self) -> Dict[str, Any]:
        """获取系统和股票进度"""
        self._cleanup_orphan_stock_state()
        payload = copy.deepcopy(self.state.progress)
        payload["next_runs"] = self._build_next_run_schedule()
        return payload

    def get_jobs(self) -> Dict[str, Any]:
        """获取后台任务状态"""
        return self.state.jobs

    def get_d7_recommendations(self) -> Dict[str, Any]:
        """获取D7推荐池（短/中/长）"""
        self._prune_d7_recommendations()
        return self.state.d7_recommendations

    def select_d7_recommendation(self, symbol: str) -> bool:
        """从D7推荐中选中并加入交易池"""
        symbol = self._normalize_symbol(symbol)
        for bucket in self.state.d7_recommendations.values():
            for item in bucket:
                if str(item.get("symbol", "")).upper() == symbol:
                    self.add_stock(symbol)
                    self._prune_d7_recommendations()
                    self._persist_runtime_state()
                    return True
        return False
    
    def get_stock_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票分析结果"""
        if symbol in self.stock_cases:
            return self.stock_cases[symbol].to_dict()
        return None
    
    def get_all_stocks_analysis(self) -> List[Dict[str, Any]]:
        """获取所有股票分析结果"""
        return [case.to_dict() for case in self.stock_cases.values()]
    
    def get_account_status(self) -> Dict[str, Any]:
        """获取账户状态"""
        return self.trading_engine.get_account_summary()
    
    def get_trade_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取交易历史"""
        return self.trading_engine.get_trade_history(symbol)

    def get_portfolio_performance(self) -> Dict[str, Any]:
        """获取组合收益指标（总收益/周/月/半年/年）。"""
        return self.trading_engine.get_portfolio_performance()

    def get_stock_performance(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取按股票收益指标（周/月/半年/年）。"""
        return self.trading_engine.get_stock_performance(symbols)

    async def train_d5(self) -> Dict[str, Any]:
        """触发 D5 在线训练/校准"""
        history = self.trading_engine.get_trade_history()
        positions = self.trading_engine.get_positions()
        account = self.trading_engine.get_account_summary()
        latest_quotes: Dict[str, float] = {}
        for p in positions:
            sym = str(p.get("symbol") or "").upper()
            if not sym:
                continue
            try:
                md, _ = await self._get_market_data(sym)
                latest_quotes[sym] = md.price
            except Exception:
                continue
        report = self.d5.train_from_runtime(
            trade_history=history,
            positions=positions,
            latest_quotes=latest_quotes,
            account_summary=account,
            stock_cases=self.stock_cases
        )
        self._persist_runtime_state()
        return report

    def get_d5_training_report(self) -> Dict[str, Any]:
        return getattr(self.d5, "last_training_report", {}) or {}
    
    # ============== 用户账户管理 ==============
    
    def create_user_account(self, 
                           user_id: str,
                           account_type: str,
                           brokerage: Optional[str] = None,
                           api_key: Optional[str] = None,
                           api_secret: Optional[str] = None,
                           account_id: Optional[str] = None) -> UserAccount:
        """创建用户账户
        
        Args:
            user_id: 用户ID
            account_type: 账户类型 ("paper" 或 "real")
            brokerage: 券商名称（真实账户需要）
            api_key: API密钥（真实账户需要）
            api_secret: API密钥密文（真实账户需要）
            account_id: 账户ID（可选，不提供则自动生成）
        
        Returns:
            UserAccount: 创建的用户账户对象
        """
        # 当前版本仅启用 paper 模式（按产品要求）
        if account_type != "paper":
            raise ValueError("Only paper account is enabled in current version")
        
        # 生成账户ID
        if not account_id:
            if account_type == "paper":
                account_id = f"paper_{user_id}_{datetime.now().timestamp()}"
            else:
                account_id = f"real_{user_id}_{datetime.now().timestamp()}"
        
        # 创建账户记录
        user_account = UserAccount(
            user_id=user_id,
            account_type=account_type,
            brokerage=brokerage,
            api_key=api_key,
            api_secret=api_secret,
            account_id=account_id
        )
        
        self.user_accounts[user_id] = user_account
        
        # 创建交易引擎
        if account_type == "paper":
            # 创建模拟账户
            engine = PaperTradingEngine(
                account_id=user_account.account_id,
                initial_capital=100000.0
            )
            self.user_trading_engines[user_id] = engine
            self.logger.info(f"Created paper trading account for user {user_id}")
        else:
            # 理论上不会进入该分支（前面已限制）
            raise ValueError("Only paper account is enabled in current version")
        
        return user_account
    
    def get_user_account(self, user_id: str) -> Optional[UserAccount]:
        """获取用户账户
        
        Args:
            user_id: 用户ID
        
        Returns:
            UserAccount: 用户账户对象，如果不存在则返回None
        """
        return self.user_accounts.get(user_id)
    
    def get_user_trading_engine(self, user_id: str) -> Optional[PaperTradingEngine]:
        """获取用户的交易引擎
        
        Args:
            user_id: 用户ID
        
        Returns:
            PaperTradingEngine: 交易引擎对象，如果不存在则返回None
        """
        return self.user_trading_engines.get(user_id)
    
    def _create_real_trading_engine(self, user_account: UserAccount) -> PaperTradingEngine:
        """创建真实交易引擎（占位符实现）
        
        Args:
            user_account: 用户账户对象
        
        Returns:
            PaperTradingEngine: 目前返回模拟引擎，后续需要实现真实引擎
        
        Note:
            这是一个占位符实现。真实交易引擎需要：
            1. 根据券商类型选择对应的API适配器
            2. 实现真实的订单提交、查询、取消等功能
            3. 实现真实的账户余额、持仓查询等功能
            4. 添加额外的风控措施
        """
        self.logger.warning(
            f"Real trading engine not yet implemented for {user_account.brokerage}. "
            "Using paper trading engine as placeholder."
        )
        # 目前返回模拟引擎作为占位符
        return PaperTradingEngine(
            account_id=user_account.account_id,
            initial_capital=100000.0
        )
    
    def get_user_account_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户账户状态
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 账户状态信息，如果用户不存在则返回None
        """
        engine = self.user_trading_engines.get(user_id)
        if engine:
            return engine.get_account_summary()
        return None
    
    def get_user_trade_history(self, user_id: str, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """获取用户交易历史
        
        Args:
            user_id: 用户ID
            symbol: 股票代码（可选，不提供则返回所有交易历史）
        
        Returns:
            List[Dict]: 交易历史列表，如果用户不存在则返回None
        """
        engine = self.user_trading_engines.get(user_id)
        if engine:
            return engine.get_trade_history(symbol)
        return None
