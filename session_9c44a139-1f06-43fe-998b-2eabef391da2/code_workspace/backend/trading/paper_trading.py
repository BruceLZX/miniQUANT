"""
Paper Trading - 模拟交易执行
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from models.base_models import TradingDecision
import uuid
import asyncio
import random


@dataclass
class Order:
    """订单"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: str = "BUY"  # BUY/SELL
    order_type: str = "LIMIT"  # MARKET/LIMIT
    quantity: float = 0.0
    price: Optional[float] = None
    status: str = "PENDING"  # PENDING/FILLED/CANCELLED/REJECTED
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    decision_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "decision_id": self.decision_id
        }


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float = 0.0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    def update_price(self, price: float):
        """更新价格"""
        self.current_price = price
        self.market_value = self.quantity * price
        if self.avg_cost > 0:
            self.unrealized_pnl = (price - self.avg_cost) * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl
        }


@dataclass
class TradingAccount:
    """交易账户"""
    account_id: str
    initial_capital: float = 100000.0  # 初始资金
    cash: float = 100000.0  # 现金
    positions: Dict[str, Position] = field(default_factory=dict)
    orders: List[Order] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_value: float = 100000.0
    
    @property
    def total_value(self) -> float:
        """总资产"""
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "total_value": self.total_value,
            "daily_pnl": self.daily_pnl,
            "total_pnl": self.total_pnl,
            "max_drawdown": self.max_drawdown
        }

class PaperTradingEngine:
    def __init__(self, account_id: str = "paper_account_001", initial_capital: float = 100000.0):
        self.account = TradingAccount(
            account_id=account_id,
            initial_capital=initial_capital,
            cash=initial_capital
        )
        
        # 交易记录
        self.trade_history: List[Dict[str, Any]] = []
        # 账户净值快照，用于区间收益计算
        self.equity_history: List[Dict[str, Any]] = []
        
        # 统计
        self.daily_trade_counts: Dict[str, int] = {}  # 每只股票每日交易次数
        self.weekly_trade_days: Dict[str, Dict[str, set]] = {}  # 每只股票每周交易天数 {symbol: {week_key: set(dates)}}
        
        # 交易规则限制（从配置导入）
        from config.settings import config
        self.max_daily_trades_per_stock = config.max_daily_trades_per_stock
        self.max_weekly_trading_days_per_stock = config.max_weekly_trading_days_per_stock
        self.record_equity_snapshot("init")
    
    
    async def execute_decision(self, decision: TradingDecision, current_price: float) -> Order:
        """执行交易决策"""
        
        # 1. 检查交易规则
        if not self._check_trading_rules(decision.symbol):
            return self._create_rejected_order(decision, "Exceeds trading limits")
        
        # 2. 创建订单
        order = self._create_order_from_decision(decision, current_price)
        if order.status == "REJECTED" or order.quantity <= 0:
            return order
        
        # 3. 模拟执行
        filled_order = await self._simulate_execution(order, current_price)
        if filled_order.status != "FILLED" or filled_order.filled_quantity <= 0:
            return filled_order
        
        # 4. 更新账户状态
        self._update_account(filled_order)
        
        # 5. 记录交易
        self._record_trade(filled_order, decision)
        
        return filled_order
    def _check_trading_rules(self, symbol: str) -> bool:
        """检查交易规则"""
        today = date.today()
        
        # 检查每日交易次数
        daily_key = f"{symbol}_{today}"
        if self.daily_trade_counts.get(daily_key, 0) >= self.max_daily_trades_per_stock:
            return False
        
        # 检查每周交易天数
        week_start = today - timedelta(days=today.weekday())
        week_key = f"{symbol}_{week_start}"
        
        # 初始化该股票的周交易记录
        if symbol not in self.weekly_trade_days:
            self.weekly_trade_days[symbol] = {}
        
        # 检查是否需要清理旧周的数据（保留当前周和上周的数据用于验证）
        weeks_to_remove = [wk for wk in self.weekly_trade_days[symbol].keys() if wk != week_key]
        for wk in weeks_to_remove:
            del self.weekly_trade_days[symbol][wk]
        
        # 获取当前周的交易天数
        current_week_days = self.weekly_trade_days[symbol].get(week_key, set())
        
        if len(current_week_days) >= self.max_weekly_trading_days_per_stock:
            if today not in current_week_days:
                return False
        return True

    def _create_order_from_decision(self, decision: TradingDecision, current_price: float) -> Order:
        """从交易决策创建订单"""
        if current_price <= 0:
            return self._create_rejected_order(decision, "Invalid market price")

        direction = str(decision.direction or "").upper().strip()
        if direction == "NO_TRADE":
            return self._create_rejected_order(decision, "NO_TRADE decision")

        decision_id = getattr(decision, "decision_id", str(uuid.uuid4()))
        symbol = str(decision.symbol or "").upper()
        position = self.account.positions.get(symbol)
        current_qty = float(position.quantity if position else 0.0)
        current_value = current_qty * current_price
        total_value = max(float(self.account.total_value), 1.0)

        # target_position 是账户资金占比（[-1,1]）；纸面账户当前仅支持 long-only 执行。
        target_ratio = abs(float(decision.target_position or 0.0))
        target_ratio = max(0.0, min(1.0, target_ratio))
        desired_value = target_ratio * total_value

        if direction in ("FLAT",):
            desired_value = 0.0
        elif direction == "SHORT":
            # 先不做裸卖空，避免负仓位污染资金曲线
            desired_value = 0.0

        delta_value = desired_value - current_value
        if abs(delta_value) < max(10.0, current_price * 0.05):
            return self._create_rejected_order(decision, "Delta too small")

        side = "BUY" if delta_value > 0 else "SELL"
        quantity = abs(delta_value) / current_price
        if side == "SELL":
            quantity = min(quantity, current_qty)
            if quantity <= 0:
                return self._create_rejected_order(decision, "No position to sell")
        else:
            affordable_qty = max(0.0, float(self.account.cash) / current_price)
            quantity = min(quantity, affordable_qty)
            if quantity <= 0:
                return self._create_rejected_order(decision, "Insufficient cash")

        quantity = float(max(0.0, quantity))
        if quantity <= 0:
            return self._create_rejected_order(decision, "Invalid quantity")

        order = Order(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=current_price,
            decision_id=decision_id
        )
        # 模拟滑点
        slippage = random.uniform(-0.001, 0.001)  # ±0.1%滑点
        execution_price = current_price * (1 + slippage)
        
        # 模拟手续费
        commission = order.quantity * execution_price * 0.0001  # 0.01%手续费
        
        # 更新订单状态
        order.status = "FILLED"
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.updated_at = datetime.now()
        
        return order
    async def _simulate_execution(self, order: Order, current_price: float) -> Order:
        """模拟订单执行"""
        # 订单已在_create_order_from_decision中填充
        # 此方法返回订单即可
        return order
    
    def _update_account(self, order: Order):
        """更新账户"""
        symbol = order.symbol
        trade_value = order.filled_quantity * order.filled_price
        
        # 更新现金
        if order.side == "BUY":
            self.account.cash -= trade_value
        else:
            self.account.cash += trade_value
        
        # 更新持仓
        if symbol not in self.account.positions:
            self.account.positions[symbol] = Position(symbol=symbol)
        
        position = self.account.positions[symbol]
        
        if order.side == "BUY":
            # 买入，更新平均成本
            total_cost = position.avg_cost * position.quantity + trade_value
            position.quantity += order.filled_quantity
            if position.quantity > 0:
                position.avg_cost = total_cost / position.quantity
        else:
            # 卖出，计算已实现盈亏
            realized = (order.filled_price - position.avg_cost) * order.filled_quantity
            position.realized_pnl += realized
            position.quantity -= order.filled_quantity
            
            if position.quantity <= 0:
                position.quantity = 0
                position.avg_cost = 0
        
        # 更新交易计数
        today = date.today()
        daily_key = f"{symbol}_{today}"
        self.daily_trade_counts[daily_key] = self.daily_trade_counts.get(daily_key, 0) + 1
        
        # 更新每周交易天数
        week_start = today - timedelta(days=today.weekday())
        week_key = f"{symbol}_{week_start}"
        
        if symbol not in self.weekly_trade_days:
            self.weekly_trade_days[symbol] = {}
        
        if week_key not in self.weekly_trade_days[symbol]:
            self.weekly_trade_days[symbol][week_key] = set()
        
        self.weekly_trade_days[symbol][week_key].add(today)
        
        # 清理过期的每日交易计数（保留最近7天）
        week_ago = today - timedelta(days=7)
        keys_to_remove = [k for k in self.daily_trade_counts.keys() 
                          if datetime.strptime(k.split('_')[-1], '%Y-%m-%d').date() < week_ago]
        for k in keys_to_remove:
            del self.daily_trade_counts[k]
        
        
        # 计算回撤
        current_value = self.account.total_value
        if current_value > self.account.peak_value:
            self.account.peak_value = current_value
        drawdown = (self.account.peak_value - current_value) / self.account.peak_value
        if drawdown > self.account.max_drawdown:
            self.account.max_drawdown = drawdown
        self._recalculate_account_metrics()
        self.record_equity_snapshot("trade")
    
    
    def _record_trade(self, order: Order, decision: TradingDecision):
        """记录交易"""
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "order": order.to_dict(),
            "decision_id": decision.decision_id if hasattr(decision, 'decision_id') else None,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.filled_quantity,
            "price": order.filled_price
        }
        self.trade_history.append(trade_record)
    
    def _create_rejected_order(self, decision: TradingDecision, reason: str) -> Order:
        """创建拒绝订单"""
        return Order(
            symbol=decision.symbol,
            side="REJECT",
            status="REJECTED",
            quantity=0,
            decision_id=str(uuid.uuid4())
        )
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要"""
        self._recalculate_account_metrics()
        return self.account.to_dict()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓列表"""
        return [pos.to_dict() for pos in self.account.positions.values()]
    
    def get_trade_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取交易历史"""
        if symbol:
            return [t for t in self.trade_history if t['order']['symbol'] == symbol]
        return self.trade_history
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """获取每日统计"""
        today = date.today()
        today_trades = [t for t in self.trade_history 
                        if datetime.fromisoformat(t['timestamp']).date() == today]
        
        return {
            "date": today.isoformat(),
            "total_trades": len(today_trades),
            "symbols_traded": list(set([t['order']['symbol'] for t in today_trades])),
            "daily_pnl": self.account.daily_pnl
        }

    def mark_to_market(self, symbol: str, price: float):
        """按最新行情更新持仓市值与账户指标。"""
        pos = self.account.positions.get(symbol)
        if not pos:
            return
        pos.update_price(price)
        self._recalculate_account_metrics()

    def _symbol_pnl_map(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for sym, pos in self.account.positions.items():
            out[str(sym).upper()] = float(pos.unrealized_pnl or 0.0) + float(pos.realized_pnl or 0.0)
        return out

    def _recalculate_account_metrics(self):
        total_unrealized = sum(float(p.unrealized_pnl or 0.0) for p in self.account.positions.values())
        total_realized = sum(float(p.realized_pnl or 0.0) for p in self.account.positions.values())
        self.account.total_pnl = total_unrealized + total_realized
        today = date.today().isoformat()
        today_snaps = [x for x in self.equity_history if str(x.get("timestamp", "")).startswith(today)]
        if today_snaps:
            day_open = float(today_snaps[0].get("total_value", self.account.initial_capital) or self.account.initial_capital)
            self.account.daily_pnl = self.account.total_value - day_open
        else:
            self.account.daily_pnl = self.account.total_value - self.account.initial_capital

    def record_equity_snapshot(self, reason: str = ""):
        """记录净值快照（含每股PnL），供周/月/半年/年收益查询。"""
        self._recalculate_account_metrics()
        now = datetime.now()
        snap = {
            "timestamp": now.isoformat(),
            "reason": reason,
            "total_value": float(self.account.total_value),
            "total_pnl": float(self.account.total_pnl),
            "cash": float(self.account.cash),
            "symbol_pnl": self._symbol_pnl_map(),
        }
        if self.equity_history:
            last = self.equity_history[-1]
            if (now - datetime.fromisoformat(last["timestamp"])).total_seconds() < 20 and \
               abs(float(last.get("total_value", 0.0)) - snap["total_value"]) < 1e-9:
                return
        self.equity_history.append(snap)
        if len(self.equity_history) > 12000:
            self.equity_history = self.equity_history[-12000:]

    def _find_snapshot_before(self, cutoff: datetime) -> Optional[Dict[str, Any]]:
        for row in reversed(self.equity_history):
            try:
                ts = datetime.fromisoformat(str(row.get("timestamp")))
            except Exception:
                continue
            if ts <= cutoff:
                return row
        return None

    def get_portfolio_performance(self) -> Dict[str, Any]:
        self._recalculate_account_metrics()
        now = datetime.now()
        periods = {
            "week": 7,
            "month": 30,
            "half_year": 182,
            "year": 365,
        }
        by_period: Dict[str, Optional[float]] = {}
        for key, days in periods.items():
            base = self._find_snapshot_before(now - timedelta(days=days))
            if not base:
                by_period[key] = float(self.account.total_pnl)
                continue
            by_period[key] = float(self.account.total_value) - float(base.get("total_value", self.account.total_value))
        return {
            "total_pnl": float(self.account.total_pnl),
            "total_value": float(self.account.total_value),
            "period_pnl": by_period,
            "as_of": now.isoformat(),
        }

    def get_stock_performance(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        now = datetime.now()
        periods = {
            "week": 7,
            "month": 30,
            "half_year": 182,
            "year": 365,
        }
        selected = {str(s).upper() for s in (symbols or [])}
        current_map = self._symbol_pnl_map()
        if not selected:
            selected = set(current_map.keys())
        rows: Dict[str, Any] = {}
        for sym in sorted(selected):
            current = float(current_map.get(sym, 0.0))
            pp: Dict[str, Optional[float]] = {}
            for key, days in periods.items():
                base = self._find_snapshot_before(now - timedelta(days=days))
                if not base:
                    pp[key] = current
                    continue
                base_map = dict(base.get("symbol_pnl") or {})
                pp[key] = current - float(base_map.get(sym, 0.0) or 0.0)
            rows[sym] = {
                "symbol": sym,
                "total_pnl": current,
                "period_pnl": pp,
            }
        return {"stocks": rows, "as_of": now.isoformat()}
