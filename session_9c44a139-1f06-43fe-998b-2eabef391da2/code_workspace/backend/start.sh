#!/bin/bash

# AI Agent Stock Trading Platform 启动脚本

echo "==================================="
echo "AI Agent Stock Trading Platform"
echo "==================================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "Activating virtual environment..."
source venv/bin/activate

# 安装依赖
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit .env file with your API keys"
    fi
fi

echo ""
echo "Starting trading platform..."
echo ""

# 启动API服务
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
