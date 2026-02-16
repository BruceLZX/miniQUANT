# 项目结构总览

## 目录结构

```
backend/
├── agents/                    # Agent模块
│   ├── __init__.py
│   ├── base_agent.py         # Agent基类和MockAgent
│   ├── analyst.py            # 分析者Agent（Round 1）
│   ├── critic.py             # 批评者Agent（Round 2）
│   └── decider.py            # 拍板者Agent（Round 3）
│
├── departments/              # 部门模块
│   ├── __init__.py
│   ├── base_department.py   # 部门基类（实现三轮讨论）
│   ├── d1_macro.py          # D1 宏观国际新闻部
│   ├── d2_industry.py       # D2 行业部
│   ├── d3_stock.py          # D3 单股新闻部
│   ├── d4_expert.py         # D4 专业材料部
│   ├── d6_ic.py             # D6 投资决策委员会
│   └── d7_stock_selection.py # D7 选股部
│
├── quantitative/             # 量化模块
│   ├── __init__.py
│   └── d5_quant.py          # D5 量化部（融合模型）
│
├── memory/                   # 记忆系统
│   ├── __init__.py
│   └── memory_store.py      # 三层记忆架构
│
├── trading/                  # 交易执行
│   ├── __init__.py
│   └── paper_trading.py     # Paper Trading引擎
│
├── data/                     # 数据收集
│   ├── __init__.py
│   └── data_collector.py    # 数据收集器
│
├── utils/                    # 工具模块
│   ├── __init__.py
│   └── evaluation.py        # 评估系统
│
├── core/                     # 核心调度
│   ├── __init__.py
│   └── scheduler.py         # 主调度器
│
├── api/                      # API接口
│   ├── __init__.py
│   └── main.py              # FastAPI应用
│
├── models/                   # 数据模型
│   ├── __init__.py
│   └── base_models.py       # 基础数据模型
│
├── config/                   # 配置
│   ├── __init__.py
│   └── settings.py          # 系统配置
│
├── tests/                    # 测试
│   └── test_system.py       # 系统测试
│
├── examples/                 # 示例代码
│   ├── basic_usage.py       # 基本使用示例
│   └── api_client.py        # API客户端示例
│
├── main.py                   # 主入口
├── requirements.txt          # Python依赖
├── Dockerfile               # Docker配置
├── .env.example             # 环境变量示例
├── start.sh                 # 启动脚本
├── README.md                # 项目文档
└── QUICKSTART.md            # 快速开始指南
```

## 核心组件说明

### 1. Agent系统 (agents/)
- **BaseAgent**: Agent基类，定义接口
- **AnalystAgent**: 分析者，输出立场、分数、置信度
- **CriticAgent**: 批评者，审查逻辑漏洞和风险
- **DeciderAgent**: 拍板者，做出最终裁决

### 2. 部门系统 (departments/)
- **BaseDepartment**: 实现三轮讨论机制
- **D1-D7**: 7个专业部门，各有特定职责
- 每个部门独立运行，产出结构化结论

### 3. 量化系统 (quantitative/)
- **D5QuantDepartment**: 量化融合模型
- 实现稳健的alpha生成和仓位管理
- 将LLM输出作为门控因子

### 4. 记忆系统 (memory/)
- **MemoryStore**: 记忆存储抽象
- **MemoryManager**: 记忆管理器
- 三层记忆：LTM/STM/Ephemeral
- 权限隔离，防止串线

### 5. 交易系统 (trading/)
- **PaperTradingEngine**: 模拟交易引擎
- 订单管理、持仓管理
- 风控规则、交易限制

### 6. 调度系统 (core/)
- **TradingPlatformScheduler**: 主调度器
- 协调各部门运行频率
- 管理股票案例生命周期

### 7. API系统 (api/)
- **FastAPI应用**: RESTful API
- 提供完整的HTTP接口
- 支持Swagger文档

## 数据流向

```
1. 用户添加股票
   ↓
2. D7选股部门筛选候选池
   ↓
3. D1-D4研究部门分析（并行）
   ↓
4. D5量化部融合计算
   ↓
5. D6投委会做出决策
   ↓
6. Paper Trading执行
   ↓
7. 评估系统评分反馈
```

## 关键特性

### 三轮讨论机制
```
Round 1: 分析者A/B/C → 独立分析
Round 2: 批评者 → 质疑审查
Round 3: 拍板者 → 最终裁决
```

### 量化融合公式
```
市场alpha = β₀ + β₁r + β₂z_vwap + β₃imb + β₄WF
门控 = sigmoid(γ₀ + γ₁LA' - γ₂Dis - γ₃EventRisk)
最终alpha = 门控 × 市场alpha
仓位 = clip(K × alpha/σ, -max, max)
```

### 交易规则
- 每日每股票最多2次交易
- 每周每股票最多2天交易
- 事件触发冷却15分钟

## 扩展点

1. **集成真实LLM**: 实现`BaseAgent.call_model()`
2. **接入数据源**: 扩展`DataCollector`
3. **持久化存储**: 替换`InMemoryStore`
4. **实盘交易**: 实现券商API对接
5. **前端界面**: 基于API开发Vue前端

## 配置管理

主要配置项（config/settings.py）：
- 调度频率
- 风控参数
- 模型选择
- API密钥
- 数据库连接

## 测试

运行测试：
```bash
python tests/test_system.py
```

## 部署

### 本地开发
```bash
python -m uvicorn api.main:app --reload
```

### Docker部署
```bash
docker build -t trading-platform .
docker run -p 8000:8000 trading-platform
```

### 生产环境
- 使用gunicorn + uvicorn
- 配置nginx反向代理
- 使用PostgreSQL数据库
- 配置Redis缓存
