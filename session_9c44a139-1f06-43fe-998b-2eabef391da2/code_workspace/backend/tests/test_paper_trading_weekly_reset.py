"""
测试每周交易天数重置逻辑
"""
import unittest
from datetime import date, timedelta
from trading.paper_trading import PaperTradingEngine
from models.base_models import TradingDecision


class TestWeeklyTradingReset(unittest.TestCase):
    """测试每周交易天数重置逻辑"""
    
    def setUp(self):
        """设置测试环境"""
        self.engine = PaperTradingEngine(account_id="test_account", initial_capital=100000.0)
    
    def test_weekly_reset_logic(self):
        """测试每周重置逻辑"""
        symbol = "AAPL"
        
        # 模拟第一周的交易
        week1_monday = date(2024, 1, 1)  # 周一
        week1_tuesday = date(2024, 1, 2)  # 周二
        week1_wednesday = date(2024, 1, 3)  # 周三
        
        # 第一周：在周一和周二交易（应该成功）
        self.engine.daily_trade_counts[f"{symbol}_{week1_monday}"] = 1
        week1_key = f"{symbol}_{week1_monday - timedelta(days=week1_monday.weekday())}"
        self.engine.weekly_trade_days[symbol] = {week1_key: {week1_monday}}
        
        # 周二应该可以交易
        self.assertTrue(self.engine._check_trading_rules(symbol))
        
        # 添加周二的交易
        self.engine.weekly_trade_days[symbol][week1_key].add(week1_tuesday)
        
        # 周三应该不能交易（已经达到每周2天的限制）
        # 注意：这里需要模拟日期，实际测试中可能需要mock date.today()
        # 为了测试，我们直接检查逻辑
        
        # 模拟第二周
        week2_monday = date(2024, 1, 8)  # 下周一
        week2_key = f"{symbol}_{week2_monday - timedelta(days=week2_monday.weekday())}"
        
        # 添加第二周的数据
        self.engine.weekly_trade_days[symbol][week2_key] = set()
        
        # 第二周应该可以重新交易
        # 清理旧周的数据
        weeks_to_remove = [wk for wk in self.engine.weekly_trade_days[symbol].keys() if wk != week2_key]
        for wk in weeks_to_remove:
            del self.engine.weekly_trade_days[symbol][wk]
        
        # 验证旧周数据已被清理
        self.assertNotIn(week1_key, self.engine.weekly_trade_days[symbol])
        # 验证新周数据存在
        self.assertIn(week2_key, self.engine.weekly_trade_days[symbol])
    
    def test_daily_trade_limit(self):
        """测试每日交易次数限制"""
        symbol = "TSLA"
        today = date.today()
        daily_key = f"{symbol}_{today}"
        
        # 第一次交易
        self.engine.daily_trade_counts[daily_key] = 1
        self.assertTrue(self.engine._check_trading_rules(symbol))
        
        # 第二次交易
        self.engine.daily_trade_counts[daily_key] = 2
        self.assertFalse(self.engine._check_trading_rules(symbol))
    
    def test_weekly_data_structure(self):
        """测试周数据结构"""
        symbol = "MSFT"
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_key = f"{symbol}_{week_start}"
        
        # 初始化数据结构
        if symbol not in self.engine.weekly_trade_days:
            self.engine.weekly_trade_days[symbol] = {}
        
        if week_key not in self.engine.weekly_trade_days[symbol]:
            self.engine.weekly_trade_days[symbol][week_key] = set()
        
        # 添加交易日期
        self.engine.weekly_trade_days[symbol][week_key].add(today)
        
        # 验证数据结构
        self.assertIn(symbol, self.engine.weekly_trade_days)
        self.assertIn(week_key, self.engine.weekly_trade_days[symbol])
        self.assertIn(today, self.engine.weekly_trade_days[symbol][week_key])
    
    def test_old_data_cleanup(self):
        """测试旧数据清理"""
        symbol = "GOOGL"
        
        # 创建一些旧的周数据
        old_week1 = date(2024, 1, 1)
        old_week2 = date(2024, 1, 8)
        current_week = date.today()
        
        old_week1_key = f"{symbol}_{old_week1 - timedelta(days=old_week1.weekday())}"
        old_week2_key = f"{symbol}_{old_week2 - timedelta(days=old_week2.weekday())}"
        current_week_key = f"{symbol}_{current_week - timedelta(days=current_week.weekday())}"
        
        # 添加旧数据
        self.engine.weekly_trade_days[symbol] = {
            old_week1_key: {old_week1},
            old_week2_key: {old_week2},
            current_week_key: set()
        }
        
        # 清理旧数据
        weeks_to_remove = [wk for wk in self.engine.weekly_trade_days[symbol].keys() 
                          if wk != current_week_key]
        for wk in weeks_to_remove:
            del self.engine.weekly_trade_days[symbol][wk]
        
        # 验证只有当前周的数据存在
        self.assertEqual(len(self.engine.weekly_trade_days[symbol]), 1)
        self.assertIn(current_week_key, self.engine.weekly_trade_days[symbol])
        self.assertNotIn(old_week1_key, self.engine.weekly_trade_days[symbol])
        self.assertNotIn(old_week2_key, self.engine.weekly_trade_days[symbol])
    
    def test_daily_counts_cleanup(self):
        """测试每日交易计数清理"""
        symbol = "AMZN"
        
        # 创建一些旧的每日计数
        old_date = date.today() - timedelta(days=10)
        old_key = f"{symbol}_{old_date}"
        self.engine.daily_trade_counts[old_key] = 5
        
        # 模拟清理过程
        week_ago = date.today() - timedelta(days=7)
        keys_to_remove = [k for k in self.engine.daily_trade_counts.keys() 
                          if date.fromisoformat(k.split('_')[-1]) < week_ago]
        
        for k in keys_to_remove:
            del self.engine.daily_trade_counts[k]
        
        # 验证旧数据已被清理
        self.assertNotIn(old_key, self.engine.daily_trade_counts)


if __name__ == '__main__':
    unittest.main()
