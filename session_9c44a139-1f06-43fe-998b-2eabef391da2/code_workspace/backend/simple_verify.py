"""
简单验证脚本 - 验证关键 bug 修复
"""

print("=" * 60)
print("验证 Bug 修复")
print("=" * 60)

# 测试 1: 检查 paper_trading.py 的 __init__ 方法
print("\n1. 检查 PaperTradingEngine.__init__ 方法...")
try:
    with open('trading/paper_trading.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否包含必需的属性初始化
    checks = [
        ('self.trade_history', 'trade_history'),
        ('self.daily_trade_counts', 'daily_trade_counts'),
        ('self.weekly_trade_days', 'weekly_trade_days'),
        ('self.max_daily_trades_per_stock', 'max_daily_trades_per_stock'),
        ('self.max_weekly_trading_days_per_stock', 'max_weekly_trading_days_per_stock'),
    ]
    
    all_present = True
    for check_str, attr_name in checks:
        if check_str in content:
            print(f"  ✓ 找到属性初始化: {attr_name}")
        else:
            print(f"  ❌ 缺少属性初始化: {attr_name}")
            all_present = False
    
    # 检查是否从 config 导入
    if 'from config.settings import config' in content:
        print("  ✓ 找到 config 导入")
    else:
        print("  ❌ 缺少 config 导入")
        all_present = False
    
    if all_present:
        print("✓ PaperTradingEngine.__init__ 修复成功！")
    else:
        print("❌ PaperTradingEngine.__init__ 修复不完整！")
        
except Exception as e:
    print(f"❌ 检查失败: {e}")

# 测试 2: 检查 api/main.py 的重复定义
print("\n2. 检查 API main.py 重复定义...")
try:
    with open('api/main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查 MaterialUploadRequest
    material_count = content.count('class MaterialUploadRequest(BaseModel):')
    print(f"  MaterialUploadRequest 定义次数: {material_count}")
    if material_count == 1:
        print("  ✓ MaterialUploadRequest 无重复定义")
    else:
        print(f"  ❌ MaterialUploadRequest 定义了 {material_count} 次")
    
    # 检查 update_config
    update_config_count = content.count('async def update_config(request: UserConfigRequest):')
    print(f"  update_config 定义次数: {update_config_count}")
    if update_config_count == 1:
        print("  ✓ update_config 无重复定义")
    else:
        print(f"  ❌ update_config 定义了 {update_config_count} 次")
    
    # 检查 startup_event
    startup_decorator = content.count('@app.on_event("startup")')
    startup_func = content.count('async def startup_event():')
    print(f"  startup_event 装饰器: {startup_decorator}, 函数: {startup_func}")
    if startup_decorator == 1 and startup_func == 1:
        print("  ✓ startup_event 有正确的装饰器")
    else:
        print(f"  ❌ startup_event 装饰器或函数有问题")
    
    if material_count == 1 and update_config_count == 1 and startup_decorator == 1 and startup_func == 1:
        print("✓ API main.py 重复定义修复成功！")
    else:
        print("❌ API main.py 重复定义修复不完整！")
        
except Exception as e:
    print(f"❌ 检查失败: {e}")

# 测试 3: 验证配置文件中的交易规则
print("\n3. 检查配置文件中的交易规则...")
try:
    with open('config/settings.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_daily = 'max_daily_trades_per_stock: int = 2' in content
    has_weekly = 'max_weekly_trading_days_per_stock: int = 2' in content
    
    if has_daily:
        print("  ✓ 找到 max_daily_trades_per_stock = 2")
    else:
        print("  ❌ 缺少 max_daily_trades_per_stock = 2")
    
    if has_weekly:
        print("  ✓ 找到 max_weekly_trading_days_per_stock = 2")
    else:
        print("  ❌ 缺少 max_weekly_trading_days_per_stock = 2")
    
    if has_daily and has_weekly:
        print("✓ 配置文件中的交易规则正确！")
    else:
        print("❌ 配置文件中的交易规则不完整！")
        
except Exception as e:
    print(f"❌ 检查失败: {e}")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)
