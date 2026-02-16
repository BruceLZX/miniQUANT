# 快速开始指南

## 1. 环境准备

### 系统要求
- Python 3.11+
- pip 包管理器

### 安装步骤

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt
```

## 2. 配置

```bash
# 复制环境变量配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
# vim .env
```

## 3. 运行测试

```bash
# 运行单元测试
python tests/test_system.py
```

## 4. 启动服务

### 方式1：使用启动脚本（Linux/Mac）

```bash
chmod +x start.sh
./start.sh
```

### 方式2：直接运行

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式3：使用Docker

```bash
# 构建镜像
docker build -t trading-platform .

# 运行容器
docker run -p 8000:8000 trading-platform
```

## 5. 访问API文档

启动服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 6. 使用示例

### Python客户端示例

```python
import asyncio
from examples.api_client import TradingPlatformClient

async def main():
    client = TradingPlatformClient()
    
    # 添加股票
    await client.add_stock("AAPL")
    
    # 查看分析
    analysis = await client.get_analysis("AAPL")
    print(analysis)
    
    # 查看账户
    account = await client.get_account_status()
    print(account)

asyncio.run(main())
```

### 使用curl测试API

```bash
# 添加股票
curl -X POST http://localhost:8000/api/stocks/add \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'

# 查看股票列表
curl http://localhost:8000/api/stocks/list

# 查看分析结果
curl http://localhost:8000/api/analysis/AAPL

# 查看账户状态
curl http://localhost:8000/api/trading/account
```

## 7. 主要功能

### 7.1 多智能体审议工作流

系统自动运行7个部门的分析流程：
- D1: 宏观国际新闻部（每60分钟）
- D2: 行业部（每60分钟）
- D3: 单股新闻部（每60分钟）
- D4: 专业材料部（每6小时）
- D5: 量化部（每5分钟）
- D6: 投资决策委员会（每30分钟）
- D7: 选股部（每天一次）

### 7.2 三轮讨论机制

每个部门采用：
1. Round 1: 3个分析者独立分析
2. Round 2: 批评者质疑
3. Round 3: 拍板者裁决

### 7.3 量化融合

D5量化部将各部门结论融合为可执行的交易建议。

### 7.4 Paper Trading

模拟交易执行，记录所有交易历史。

## 8. 监控和调试

### 查看日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 查看系统状态

```bash
curl http://localhost:8000/api/system/status
```

## 9. 常见问题

### Q: 如何修改调度频率？
A: 编辑 `config/settings.py` 中的间隔参数。

### Q: 如何添加新的数据源？
A: 修改 `data/data_collector.py` 中的相应方法。

### Q: 如何集成真实的LLM API？
A: 实现 `agents/base_agent.py` 中的 `call_model` 方法。

## 10. 下一步

- 查看 `examples/basic_usage.py` 了解更多用法
- 阅读 `README.md` 了解系统架构
- 查看 `tests/test_system.py` 了解测试方法

## 支持

如有问题，请提交Issue或查看文档。
