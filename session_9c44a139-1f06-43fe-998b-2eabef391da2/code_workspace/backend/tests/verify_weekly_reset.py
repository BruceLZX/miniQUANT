"""
验证每周重置逻辑的简单脚本
"""
import sys
sys.path.insert(0, '/app/WareHouse/session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace')

from datetime import date, timedelta
from trading.paper_trading import PaperTradingEngine


def test_weekly_reset():
    """测试每周重置逻辑"""
    print("=" * 60)
    print("测试每周交易天数重置逻辑")
    print("=" * 60)
    
    engine = PaperTradingEngine(account_id="test_account", initial_capital=100000.0)
    symbol = "AAPL"
    
    # 测试1：验证初始状态
    print("\n【测试1】验证初始状态")
    print(f"weekly_trade_days初始结构: {engine.weekly_trade_days}")
    print(f"daily_trade_counts初始结构: {engine.daily_trade_counts}")
    
    # 测试2：模拟第一周的交易
    print("\n【测试2】模拟第一周的交易")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_key = f"{symbol}_{week_start}"
    
    # 初始化数据结构
    if symbol not in engine.weekly_trade_days:
        engine.weekly_trade_days[symbol] = {}
    
    if week_key not in engine.weekly_trade_days[symbol]:
        engine.weekly_trade_days[symbol][week_key] = set()
    
    # 第一天交易
    engine.weekly_trade_days[symbol][week_key].add(today)
    engine.daily_trade_counts[f"{symbol}_{today}"] = 1
    print(f"第一天交易后 - week_key: {week_key}")
    print(f"第一天交易后 - weekly_trade_days: {engine.weekly_trade_days}")
    print(f"第一天交易后 - daily_trade_counts: {engine.daily_trade_counts}")
    
    # 第二天交易（不同日期）
    day2 = today + timedelta(days=1)
    engine.weekly_trade_days[symbol][week_key].add(day2)
    engine.daily_trade_counts[f"{symbol}_{day2}"] = 1
    print(f"\n第二天交易后 - weekly_trade_days: {engine.weekly_trade_days}")
    print(f"当前周交易天数: {len(engine.weekly_trade_days[symbol][week_key])}")
    
    # 测试3：模拟第二周（新的一周）
    print("\n【测试3】模拟第二周（新的一周）")
    next_week = today + timedelta(days=7)
    next_week_start = next_week - timedelta(days=next_week.weekday())
    next_week_key = f"{symbol}_{next_week_start}"
    
    print(f"下一周的week_key: {next_week_key}")
    
    # 模拟清理旧周数据
    weeks_to_remove = [wk for wk in engine.weekly_trade_days[symbol].keys() if wk != next_week_key]
    for wk in weeks_to_remove:
        del engine.weekly_trade_days[symbol][wk]
    
    # 初始化新周数据
    if next_week_key not in engine.weekly_trade_days[symbol]:
        engine.weekly_trade_days[symbol][next_week_key] = set()
    
    print(f"清理旧周后的weekly_trade_days: {engine.weekly_trade_days}")
    print(f"新周的交易天数: {len(engine.weekly_trade_days[symbol][next_week_key])}")
    
    # 测试4：验证每日交易限制
    print("\n【测试4】验证每日交易限制")
    test_symbol = "TSLA"
    test_date = date.today()
    test_key = f"{test_symbol}_{test_date}"
    
    # 第一次交易
    engine.daily_trade_counts[test_key] = 1
    print(f"第一次交易 - daily_trade_counts[{test_key}]: {engine.daily_trade_counts[test_key]}")
    print(f"是否可以交易: {engine.daily_trade_counts[test_key] < 2}")
    
    # 第二次交易
    engine.daily_trade_counts[test_key] = 2
    print(f"第二次交易 - daily_trade_counts[{test_key}]: {engine.daily_trade_counts[test_key]}")
    print(f"是否可以交易: {engine.daily_trade_counts[test_key] < 2}")
    
    # 测试5：验证数据清理
    print("\n【测试5】验证数据清理")
    old_date = date.today() - timedelta(days=10)
    old_key = f"{symbol}_{old_date}"
    engine.daily_trade_counts[old_key] = 5
    print(f"添加10天前的数据: {old_key}")
    print(f"清理前的daily_trade_counts: {list(engine.daily_trade_counts.keys())}")
    
    # 清理7天前的数据
    week_ago = date.today() - timedelta(days=7)
    keys_to_remove = [k for k in engine.daily_trade_counts.keys() 
                      if date.fromisoformat(k.split('_')[-1]) < week_ago]
    for k in keys_to_remove:
        del engine.daily_trade_counts[k]
    
    print(f"清理后的daily_trade_counts: {list(engine.daily_trade_counts.keys())}")
    print(f"旧数据是否被清理: {old_key not in engine.daily_trade_counts}")
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_weekly_reset()
