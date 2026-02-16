#!/usr/bin/env python3
"""
完整Bug修复验证脚本
验证所有Critical Bug已修复
"""
import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_api_syntax():
    """测试1: API main.py语法"""
    print("\n" + "="*70)
    print("测试1: backend/api/main.py 语法检查")
    print("="*70)
    try:
        with open("backend/api/main.py", 'r') as f:
            code = f.read()
        compile(code, "backend/api/main.py", 'exec')
        print("✓ 语法正确")
        return True
    except SyntaxError as e:
        print(f"✗ 语法错误:")
        print(f"  行 {e.lineno}: {e.msg}")
        print(f"  {e.text}")
        return False

def test_paper_trading_syntax():
    """测试2: Paper Trading语法"""
    print("\n" + "="*70)
    print("测试2: backend/trading/paper_trading.py 语法检查")
    print("="*70)
    try:
        with open("backend/trading/paper_trading.py", 'r') as f:
            code = f.read()
        compile(code, "backend/trading/paper_trading.py", 'exec')
        print("✓ 语法正确")
        return True
    except SyntaxError as e:
        print(f"✗ 语法错误:")
        print(f"  行 {e.lineno}: {e.msg}")
        print(f"  {e.text}")
        return False

def test_paper_trading_attributes():
    """测试3: PaperTradingEngine属性初始化"""
    print("\n" + "="*70)
    print("测试3: PaperTradingEngine 属性初始化检查")
    print("="*70)
    try:
        from trading.paper_trading import PaperTradingEngine
        engine = PaperTradingEngine()
        
        # 检查必需属性
        assert hasattr(engine, 'max_daily_trades_per_stock'), "缺少 max_daily_trades_per_stock"
        assert hasattr(engine, 'max_weekly_trading_days_per_stock'), "缺少 max_weekly_trading_days_per_stock"
        
        print(f"✓ max_daily_trades_per_stock = {engine.max_daily_trades_per_stock}")
        print(f"✓ max_weekly_trading_days_per_stock = {engine.max_weekly_trading_days_per_stock}")
        return True
    except Exception as e:
        print(f"✗ 属性检查失败: {e}")
        return False

def test_weekly_reset_logic():
    """测试4: 每周重置逻辑"""
    print("\n" + "="*70)
    print("测试4: 每周交易天数重置逻辑检查")
    print("="*70)
    try:
        from trading.paper_trading import PaperTradingEngine
        from datetime import date, timedelta
        
        engine = PaperTradingEngine()
        
        # 检查数据结构
        assert isinstance(engine.weekly_trade_days, dict), "weekly_trade_days 应该是 dict"
        print("✓ weekly_trade_days 数据结构正确")
        
        # 模拟交易
        symbol = "TEST001"
        week1_start = date.today() - timedelta(days=7)
        week1_key = f"{symbol}_{week1_start}"
        
        # 添加第一周的数据
        engine.weekly_trade_days[symbol] = {
            week1_key: {date.today() - timedelta(days=7), date.today() - timedelta(days=6)}
        }
        
        # 检查当前周
        can_trade = engine._check_trading_rules(symbol)
        print(f"✓ 当前周可以交易: {can_trade}")
        
        # 验证旧周数据被清理
        week2_start = date.today() - timedelta(days=date.today().weekday())
        week2_key = f"{symbol}_{week2_start}"
        
        assert week1_key not in engine.weekly_trade_days[symbol], "旧周数据应该被清理"
        print("✓ 旧周数据已清理")
        
        return True
    except Exception as e:
        print(f"✗ 周重置逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_random():
    """测试5: import random"""
    print("\n" + "="*70)
    print("测试5: import random 检查")
    print("="*70)
    try:
        with open("backend/trading/paper_trading.py", 'r') as f:
            content = f.read()
        
        if 'import random' in content:
            print("✓ import random 已添加")
            return True
        else:
            print("✗ 缺少 import random")
            return False
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False

def test_order_creation():
    """测试6: 订单创建逻辑"""
    print("\n" + "="*70)
    print("测试6: 订单创建逻辑检查")
    print("="*70)
    try:
        from trading.paper_trading import PaperTradingEngine
        from models.base_models import TradingDecision
        
        engine = PaperTradingEngine()
        
        # 创建测试决策
        decision = TradingDecision(
            decision_id="test_001",
            symbol="TEST001",
            direction="LONG",
            target_position=100,
            rationale="Test order creation"
        )
        
        # 创建订单
        order = engine._create_order_from_decision(decision, 100.0)
        
        assert order is not None, "订单不应为None"
        assert order.symbol == "TEST001", "股票代码不匹配"
        assert order.quantity == 100, "数量不匹配"
        
        print(f"✓ 订单创建成功: {order.order_id}")
        print(f"  股票: {order.symbol}")
        print(f"  数量: {order.quantity}")
        print(f"  价格: {order.filled_price}")
        return True
    except Exception as e:
        print(f"✗ 订单创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """测试7: API端点定义"""
    print("\n" + "="*70)
    print("测试7: API端点定义检查")
    print("="*70)
    try:
        with open("backend/api/main.py", 'r') as f:
            content = f.read()
        
        required_endpoints = [
            '@app.post("/api/config/update")',
            '@app.get("/api/system/status")',
            '@app.post("/api/system/start")',
            '@app.post("/api/system/stop")'
        ]
        
        all_found = True
        for endpoint in required_endpoints:
            if endpoint in content:
                print(f"✓ {endpoint}")
            else:
                print(f"✗ 缺少 {endpoint}")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("\n" + "#"*70)
    print("# AI Agent股票交易平台 - Bug修复验证")
    print("#"*70)
    
    tests = [
        ("API语法检查", test_api_syntax),
        ("Paper Trading语法检查", test_paper_trading_syntax),
        ("属性初始化", test_paper_trading_attributes),
        ("周重置逻辑", test_weekly_reset_logic),
        ("import random", test_import_random),
        ("订单创建", test_order_creation),
        ("API端点定义", test_api_endpoints),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ 测试 {test_name} 抛出异常: {e}")
            results.append((test_name, False))
    
    # 总结
    print("\n" + "#"*70)
    print("# 测试总结")
    print("#"*70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:.<50} {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n" + "="*70)
        print("✓✓✓ 所有Bug已成功修复！系统可以正常运行。")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print("✗✗✗ 仍有Bug未修复，需要继续处理。")
        print("="*70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
