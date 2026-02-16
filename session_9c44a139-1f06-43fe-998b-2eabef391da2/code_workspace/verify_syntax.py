#!/usr/bin/env python3
"""验证Python语法"""
import py_compile
import sys

files_to_check = [
    "backend/api/main.py",
    "backend/trading/paper_trading.py"
]

all_ok = True
for file_path in files_to_check:
    try:
        py_compile.compile(file_path, doraise=True)
        print(f"✓ {file_path}: 语法正确")
    except py_compile.PyCompileError as e:
        print(f"✗ {file_path}: 语法错误")
        print(f"  错误: {e}")
        all_ok = False

if all_ok:
    print("\n✓ 所有文件语法检查通过")
    sys.exit(0)
else:
    print("\n✗ 存在语法错误")
    sys.exit(1)
