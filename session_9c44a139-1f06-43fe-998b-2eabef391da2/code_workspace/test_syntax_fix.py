#!/usr/bin/env python3
"""测试语法修复"""
import ast
import sys

def check_syntax(file_path):
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

# 检查关键文件
files = [
    "backend/api/main.py",
    "backend/trading/paper_trading.py"
]

print("=" * 60)
print("语法验证测试")
print("=" * 60)

all_ok = True
for file_path in files:
    ok, error = check_syntax(file_path)
    if ok:
        print(f"✓ {file_path}")
        print(f"  状态: 语法正确")
    else:
        print(f"✗ {file_path}")
        print(f"  错误: {error}")
        all_ok = False
    print()

print("=" * 60)
if all_ok:
    print("✓ 所有文件语法检查通过")
    sys.exit(0)
else:
    print("✗ 存在语法错误，需要修复")
    sys.exit(1)
