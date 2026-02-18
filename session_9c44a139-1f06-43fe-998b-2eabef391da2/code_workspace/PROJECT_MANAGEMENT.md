# MyQuant Project Management

本文件用于研发协作，不替代 `manual.md`。

## 1. 项目目标
- 交付可持续迭代的多 Agent 交易平台（而不是一次性 Demo）。
- 保证“可运行、可追踪、可审计、可维护”。

## 2. 代码结构与职责

## 2.1 Backend
- `api/main.py`: API 边界与请求协议。
- `core/scheduler.py`: 全局编排（D1-D7、任务状态、持久化）。
- `agents/`: Analyst/Critic/Decider 提示词与模型调用。
- `departments/`: 各部门业务逻辑与证据收集。
- `quantitative/d5_quant.py`: 量化融合与在线训练。
- `trading/paper_trading.py`: 模拟交易执行与规则限制。
- `memory/memory_store.py`: 记忆存储、检索、反馈学习。
- `data/`: 行情/新闻采集。

## 2.2 Frontend
- `frontend/index.html`: 配置入口。
- `frontend/platform.html`: 主控制台（状态、决策、股票卡片、D4、D5、Jobs）。

## 2.3 Scripts
- `start_services.sh` / `stop_services.sh`: 本地一键启停。

## 3. 当前工程约束
- 默认运行模式：paper trading（真实券商暂不启用）。
- D7 仅推荐，入池需要人工确认。
- D4 原始用户粘贴内容不持久化，仅分析结论入记忆。
- 交易硬规则：每股每天最多2次、每周最多2个交易日。

## 4. 开发流程（建议）

## 4.1 分支策略
- `main`: 稳定可运行。
- feature 分支命名：`feat/<area>-<topic>`。
- bugfix 分支命名：`fix/<area>-<topic>`。

## 4.2 提交流程
1. 修改代码
2. 本地验证
3. 更新相关文档
4. 提交 PR
5. Review 通过后合并

## 4.3 最低验证清单
- 后端启动成功：`/health` 返回 200
- 前端页面可加载并能成功刷新
- 至少跑通一轮：`run-d7` -> `d7/select` -> `run-once`
- 不提交敏感数据（`.env`、runtime state、附件）

## 5. 文档策略
- `manual.md`: 用户和部署导向
- `README.md`: 项目总览导向
- `PROJECT_MANAGEMENT.md`: 团队协作与治理导向

## 6. 后续路线（管理视角）
- M1: 提升策略质量（D7 多样化、D6 决策一致性）
- M2: 记忆系统增强（语义召回质量 + 反馈学习校准）
- M3: 标准 MCP 服务化（memory service 拆分）
- M4: 真实券商接入（可插拔 broker engine）

## 7. 不应提交到仓库的内容
- API Key / `.env`
- `.runtime_state.json` / `.runtime_config.json`
- 本地日志、附件、虚拟环境目录

