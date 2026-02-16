#!/usr/bin/env python3
"""简单语法测试"""
import sys

# 测试 backend/api/main.py
print("测试 backend/api/main.py...")
try:
    with open("backend/api/main.py", 'r') as f:
        code = f.read()
    compile(code, "backend/api/main.py", 'exec')
    print("✓ backend/api/main.py 语法正确")
except SyntaxError as e:
    print(f"✗ backend/api/main.py 语法错误:")
    print(f"  行 {e.lineno}: {e.msg}")
    sys.exit(1)

# 测试 backend/trading/paper_trading.py
print("测试 backend/trading/paper_trading.py...")
try:
    with open("backend/trading/paper_trading.py", 'r') as f:
        code = f.read()
    compile(code, "backend/trading/paper_trading.py", 'exec')
    print("✓ backend/trading/paper_trading.py 语法正确")
except SyntaxError as e:
    print(f"✗ backend/trading/paper_trading.py 语法错误:")
    print(f"  行 {e.lineno}: {e.msg}")
    sys.exit(1)

print("\n✓ 所有文件语法检查通过！")
