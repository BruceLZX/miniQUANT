# AI Agent Stock Trading Platform

一个基于多智能体审议工作流的量化交易平台，将AI Agent与量化交易相结合。

## 项目概述

本平台采用"模块化量化交易系统 + 多智能体审议工作流"的架构，实现了：

- **7个专业部门**：宏观国际新闻部(D1)、行业部(D2)、单股新闻部(D3)、专业材料部(D4)、量化部(D5)、投资决策委员会(D6)、选股部(D7)
- **三轮讨论机制**：独立分析 → 批评质疑 → 拍板裁决
- **三层记忆系统**：长期记忆(LTM)、短期记忆(STM)、会话记忆
- **稳健风控**：分歧惩罚、事件风险控制、仓位管理
- **Paper Trading**：模拟交易执行与评估

## 系统架构

```
backend/
├── agents/              # Agent模块
│   ├── base_agent.py   # Agent基类
│   ├── analyst.py      # 分析者Agent
│   ├── critic.py       # 批评者Agent
│   └── decider.py      # 拍板者Agent
├── departments/         # 部门模块
│   ├── base_department.py
│   ├── d1_macro.py     # 宏观国际新闻部
│   ├── d2_industry.py  # 行业部
│   ├── d3_stock.py     # 单股新闻部
│   ├── d4_expert.py    # 专业材料部
│   ├── d6_ic.py        # 投资决策委员会
│   └── d7_stock_selection.py  # 选股部
├── quantitative/        # 量化模块
│   └── d5_quant.py     # 量化部
├── memory/             # 记忆系统
│   └── memory_store.py
├── trading/            # 交易执行
│   └── paper_trading.py
├── data/               # 数据收集
│   └── data_collector.py
├── utils/              # 工具模块
│   └── evaluation.py   # 评估系统
├── core/               # 核心调度
│   └── scheduler.py
├── api/                # API接口
│   └── main.py
├── models/             # 数据模型
│   └── base_models.py
├── config/             # 配置
│   └── settings.py
└── main.py            # 主入口
```

## 核心特性

### 1. 多智能体审议工作流

每个部门采用三轮讨论机制：

- **Round 1 - 独立分析**：3个分析者（使用不同模型）独立输出立场、分数、置信度和证据
- **Round 2 - 批评质疑**：批评者审查逻辑漏洞、证据不足、尾部风险
- **Round 3 - 拍板裁决**：拍板者综合前两轮，做出最终结论

### 2. 量化融合模型

D5量化部实现稳健的融合模型：

```
市场alpha = β₀ + β₁r_t + β₂z_vwap + β₃imb_t + β₄WF_t
研究门控 = sigmoid(γ₀ + γ₁LA' - γ₂Dis - γ₃EventRisk)
最终alpha = 门控 × 市场alpha
仓位 = clip(K × alpha/σ, -pos_max, pos_max)
```

### 3. 三层记忆系统

- **长期记忆(LTM)**：政策框架、行业规律、公司档案
- **短期记忆(STM)**：近期事件、待验证假设
- **会话记忆**：本轮讨论纪要

记忆权限隔离，防止部门间串线。

### 4. 交易规则

- 每天每只股票最多交易2次
- 每周每只股票最多选择3天交易
- 事件触发冷却时间15分钟

## 安装与运行

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 启动API服务

```bash
python -m api.main
```

服务将在 `http://localhost:8000` 启动

### API文档

访问 `http://localhost:8000/docs` 查看Swagger文档

## 主要API接口

### 股票管理

- `POST /api/stocks/add` - 添加股票到监控列表
- `POST /api/stocks/remove` - 移除股票
- `GET /api/stocks/list` - 获取监控股票列表

### 分析结果

- `GET /api/analysis/{symbol}` - 获取单只股票分析结果
- `GET /api/analysis/all` - 获取所有股票分析结果
- `GET /api/departments/{symbol}` - 获取各部门输出详情

### 交易相关

- `GET /api/trading/account` - 获取账户状态
- `GET /api/trading/positions` - 获取持仓信息
- `GET /api/trading/history` - 获取交易历史

### 系统管理

- `GET /api/system/status` - 获取系统状态
- `POST /api/system/start` - 启动系统
- `POST /api/system/stop` - 停止系统

## 配置说明

在 `config/settings.py` 中可以配置：

- 调度频率（各部门运行间隔）
- 风控参数（最大仓位、止损止盈）
- 模型提供商（Kimi、ChatGPT、GLM5、DeepSeek）
- API密钥

## 开发计划

- [ ] 集成真实的LLM API（OpenAI、Claude等）
- [ ] 接入实时市场数据源
- [ ] 实现数据库持久化
- [ ] 添加前端界面
- [ ] 实现回测功能
- [ ] 添加更多技术指标

## 注意事项

⚠️ **重要提示**：
1. 本平台仅用于研究和学习目的
2. Paper Trading为模拟交易，不涉及真实资金
3. 实盘交易需要接入券商API，并遵守相关法规
4. AI分析结果仅供参考，不构成投资建议

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。
