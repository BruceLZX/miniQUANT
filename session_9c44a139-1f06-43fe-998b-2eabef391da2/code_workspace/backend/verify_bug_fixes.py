"""
验证所有bug修复的脚本
"""
import sys
import traceback

def test_paper_trading_init():
    """测试 PaperTradingEngine 初始化是否包含所有必需属性"""
    print("=" * 60)
    print("测试 1: PaperTradingEngine 初始化")
    print("=" * 60)
    
    try:
        from trading.paper_trading import PaperTradingEngine
        
        engine = PaperTradingEngine()
        
        # 检查所有必需的属性
        required_attrs = [
            'account',
            'trade_history',
            'daily_trade_counts',
            'weekly_trade_days',
            'max_daily_trades_per_stock',
            'max_weekly_trading_days_per_stock'
        ]
        
        for attr in required_attrs:
            if not hasattr(engine, attr):
                print(f"❌ 缺少属性: {attr}")
                return False
            else:
                value = getattr(engine, attr)
                print(f"✓ 属性 {attr}: {value}")
        
        # 验证交易规则值
        if engine.max_daily_trades_per_stock != 2:
            print(f"❌ max_daily_trades_per_stock 应该是 2，实际是 {engine.max_daily_trades_per_stock}")
            return False
        
        if engine.max_weekly_trading_days_per_stock != 2:
            print(f"❌ max_weekly_trading_days_per_stock 应该是 2，实际是 {engine.max_weekly_trading_days_per_stock}")
            return False
        
        print("\n✓ PaperTradingEngine 初始化测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_api_main_no_duplicates():
    """测试 API main.py 没有重复定义"""
    print("\n" + "=" * 60)
    print("测试 2: API main.py 无重复定义")
    print("=" * 60)
    
    try:
        with open('api/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查 MaterialUploadRequest 是否只出现一次（作为类定义）
        material_upload_count = content.count('class MaterialUploadRequest(BaseModel):')
        print(f"MaterialUploadRequest 定义次数: {material_upload_count}")
        
        if material_upload_count != 1:
            print(f"❌ MaterialUploadRequest 定义了 {material_upload_count} 次，应该只有 1 次")
            return False
        
        # 检查 update_config 函数是否只出现一次
        update_config_count = content.count('async def update_config(request: UserConfigRequest):')
        print(f"update_config 函数定义次数: {update_config_count}")
        
        if update_config_count != 1:
            print(f"❌ update_config 定义了 {update_config_count} 次，应该只有 1 次")
            return False
        
        # 检查 startup_event 是否有装饰器
        startup_decorator_count = content.count('@app.on_event("startup")')
        startup_func_count = content.count('async def startup_event():')
        print(f"startup_event 装饰器次数: {startup_decorator_count}")
        print(f"startup_event 函数定义次数: {startup_func_count}")
        
        if startup_decorator_count != 1 or startup_func_count != 1:
            print(f"❌ startup_event 装饰器或函数定义有问题")
            return False
        
        print("\n✓ API main.py 无重复定义测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_imports():
    """测试所有必要的导入"""
    print("\n" + "=" * 60)
    print("测试 3: 必要的导入")
    print("=" * 60)
    
    try:
        print("导入 config.settings...")
        from config.settings import config
        print(f"✓ config.max_daily_trades_per_stock = {config.max_daily_trades_per_stock}")
        print(f"✓ config.max_weekly_trading_days_per_stock = {config.max_weekly_trading_days_per_stock}")
        
        print("\n导入 trading.paper_trading...")
        from trading.paper_trading import PaperTradingEngine
        print("✓ PaperTradingEngine 导入成功")
        
        print("\n✓ 所有导入测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_trading_rules_check():
    """测试交易规则检查功能"""
    print("\n" + "=" * 60)
    print("测试 4: 交易规则检查功能")
    print("=" * 60)
    
    try:
        from trading.paper_trading import PaperTradingEngine
        from datetime import date, timedelta
        
        engine = PaperTradingEngine()
        
        # 测试每日交易限制
        print("\n测试每日交易限制...")
        symbol = "AAPL"
        today = date.today()
        daily_key = f"{symbol}_{today}"
        
        # 第一次交易应该允许
        engine.daily_trade_counts[daily_key] = 0
        result1 = engine._check_trading_rules(symbol)
        print(f"第1次交易: {'✓ 允许' if result1 else '❌ 拒绝'}")
        
        # 第二次交易应该允许
        engine.daily_trade_counts[daily_key] = 1
        result2 = engine._check_trading_rules(symbol)
        print(f"第2次交易: {'✓ 允许' if result2 else '❌ 拒绝'}")
        
        # 第三次交易应该拒绝
        engine.daily_trade_counts[daily_key] = 2
        result3 = engine._check_trading_rules(symbol)
        print(f"第3次交易: {'✓ 拒绝' if not result3 else '❌ 允许（应该拒绝）'}")
        
        if result1 and result2 and not result3:
            print("\n✓ 每日交易限制测试通过！")
        else:
            print("\n❌ 每日交易限制测试失败！")
            return False
        
        # 测试每周交易天数限制
        print("\n测试每周交易天数限制...")
        engine2 = PaperTradingEngine()
        symbol2 = "GOOGL"
        week_start = today - timedelta(days=today.weekday())
        week_key = f"{symbol2}_{week_start}"
        
        # 初始化
        if symbol2 not in engine2.weekly_trade_days:
            engine2.weekly_trade_days[symbol2] = {}
        
        # 第一天交易
        engine2.weekly_trade_days[symbol2][week_key] = {today}
        result4 = engine2._check_trading_rules(symbol2)
        print(f"第1天交易: {'✓ 允许' if result4 else '❌ 拒绝'}")
        
        # 第二天交易
        day2 = today + timedelta(days=1)
        engine2.weekly_trade_days[symbol2][week_key].add(day2)
        result5 = engine2._check_trading_rules(symbol2)
        print(f"第2天交易: {'✓ 允许' if result5 else '❌ 拒绝'}")
        
        # 第三天交易应该拒绝
        day3 = today + timedelta(days=2)
        engine2.weekly_trade_days[symbol2][week_key].add(day3)
        result6 = engine2._check_trading_rules(symbol2)
        print(f"第3天交易: {'✓ 拒绝' if not result6 else '❌ 允许（应该拒绝）'}")
        
        if result4 and result5 and not result6:
            print("\n✓ 每周交易天数限制测试通过！")
        else:
            print("\n❌ 每周交易天数限制测试失败！")
            return False
        
        print("\n✓ 交易规则检查功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始验证所有 bug 修复")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("PaperTradingEngine 初始化", test_paper_trading_init()))
    results.append(("API main.py 无重复定义", test_api_main_no_duplicates()))
    results.append(("必要的导入", test_imports()))
    results.append(("交易规则检查功能", test_trading_rules_check()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！Bug 修复成功！")
        print("=" * 60)
        return 0
    else:
        print("❌ 部分测试失败，请检查！")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
