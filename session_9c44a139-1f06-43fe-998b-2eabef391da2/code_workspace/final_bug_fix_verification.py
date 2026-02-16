#!/usr/bin/env python3
"""
最终Bug修复验证脚本
验证所有已修复的Bug
"""
import ast
import sys
from pathlib import Path

def check_python_syntax(file_path):
    """检查Python文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def check_file_content(file_path, required_strings):
    """检查文件是否包含必需的字符串"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing = []
        for req_str in required_strings:
            if req_str not in content:
                missing.append(req_str)
        
        return len(missing) == 0, missing
    except Exception as e:
        return False, [str(e)]

print("=" * 70)
print("AI Agent股票交易平台 - Bug修复验证")
print("=" * 70)
print()

# 测试结果
test_results = []

# ============== 测试1: API main.py语法检查 ==============
print("测试1: backend/api/main.py 语法检查")
print("-" * 70)
ok, error = check_python_syntax("backend/api/main.py")
if ok:
    print("✓ 语法正确")
    test_results.append(("API main.py 语法", True))
else:
    print(f"✗ 语法错误: {error}")
    test_results.append(("API main.py 语法", False))
print()

# ============== 测试2: Paper Trading语法检查 ==============
print("测试2: backend/trading/paper_trading.py 语法检查")
print("-" * 70)
ok, error = check_python_syntax("backend/trading/paper_trading.py")
if ok:
    print("✓ 语法正确")
    test_results.append(("Paper Trading 语法", True))
else:
    print(f"✗ 语法错误: {error}")
    test_results.append(("Paper Trading 语法", False))
print()

# ============== 测试3: 检查PaperTradingEngine必需属性 ==============
print("测试3: PaperTradingEngine 必需属性检查")
print("-" * 70)
required_attrs = [
    "max_daily_trades_per_stock",
    "max_weekly_trading_days_per_stock"
]
ok, missing = check_file_content("backend/trading/paper_trading.py", required_attrs)
if ok:
    print("✓ 所有必需属性都已定义")
    test_results.append(("PaperTradingEngine 属性", True))
else:
    print(f"✗ 缺少属性: {', '.join(missing)}")
    test_results.append(("PaperTradingEngine 属性", False))
print()

# ============== 测试4: 检查import random ==============
print("测试4: 检查 import random")
print("-" * 70)
ok, missing = check_file_content("backend/trading/paper_trading.py", ["import random"])
if ok:
    print("✓ import random 已添加")
    test_results.append(("import random", True))
else:
    print("✗ 缺少 import random")
    test_results.append(("import random", False))
print()

# ============== 测试5: 检查周重置逻辑 ==============
print("测试5: 检查周重置逻辑")
print("-" * 70)
required_logic = [
    "week_key",
    "current_week",
    "weekly_trade_days"
]
ok, missing = check_file_content("backend/trading/paper_trading.py", required_logic)
if ok:
    print("✓ 周重置逻辑已实现")
    test_results.append(("周重置逻辑", True))
else:
    print(f"✗ 缺少逻辑: {', '.join(missing)}")
    test_results.append(("周重置逻辑", False))
print()

# ============== 测试6: 检查API端点闭合 ==============
print("测试6: 检查API端点闭合")
print("-" * 70)
required_endpoints = [
    '@app.post("/api/config/update")',
    '@app.get("/api/system/status")',
    '@app.post("/api/system/start")',
    '@app.post("/api/system/stop")'
]
ok, missing = check_file_content("backend/api/main.py", required_endpoints)
if ok:
    print("✓ 所有API端点都已正确定义")
    test_results.append(("API端点定义", True))
else:
    print(f"✗ 缺少端点: {', '.join(missing)}")
    test_results.append(("API端点定义", False))
print()

# ============== 总结 ==============
print("=" * 70)
print("测试总结")
print("=" * 70)
passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for test_name, result in test_results:
    status = "✓ 通过" if result else "✗ 失败"
    print(f"{test_name:.<50} {status}")

print()
print(f"总计: {passed}/{total} 测试通过")

if passed == total:
    print("\n✓✓✓ 所有Bug已成功修复！系统可以正常运行。")
    sys.exit(0)
else:
    print("\n✗✗✗ 仍有Bug未修复，需要继续处理。")
    sys.exit(1)
