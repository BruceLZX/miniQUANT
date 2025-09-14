# MyQuant 快速开始

> 目标：在本地快速启动“Node.js 前端 + FastAPI 后端”的监控面板（前端唯一主动操作为“选定/更改股票”，其余只读监控），并提供 Streamlit 备用入口与排错指南。

---

## 1) 环境与依赖

- Python 3.10+
- 建议使用虚拟环境：
  - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`
  - Windows: `python -m venv .venv && .\\.venv\\Scripts\\activate`
- 安装依赖（统一）：`python3 -m pip install -r requirements.txt`
- 可选：复制 `.env.example` 为 `.env` 并填写你的 API Key（如果后续启用真实数据源/AI 服务）。

---

## 2) 启动 Node 前端 + FastAPI（推荐）

- 前端依赖：`cd web && npm install`
- 一键启动前后端：`npm run dev:all`（脚本会在根目录设置 `PYTHONPATH=src` 并启动后端）
- 打开：`http://localhost:3000`
- 页面说明：初始为空白选择框；输入如 `AAPL` 并点击 Select 开始监控；点击 Change 可更换标的；其余模块为只读监控。

---

## 3) 启动 Streamlit 备用 UI（纸上交易）

- 运行命令：`streamlit run src/myquant/ui/streamlit_app.py`（已包含在统一依赖中）
- 功能概览：
  - K 线图、最新价与涨跌幅
  - 新闻与情绪占位（从 `data/news/news_sample.csv` 读取示例）
  - 下单（买/卖、市价/限价），成交回写 `data/paper_trading_state.json`
  - 持仓与订单展示（基于 `PaperBroker` 文件持久化）
- 重置纸上交易数据：删除 `data/paper_trading_state.json`

---

## 4) 数据与文件约定

- 新闻样例：`data/news/news_sample.csv`
  - 列：`ts,symbol,title,summary,sentiment`
  - `ts` 为 UTC 时间，例如 `2025-01-01T12:00:00Z`
- 市场数据：默认尝试 `yfinance`，失败时生成演示数据，保证 UI 可用。
- 日志输出目录：`logs/`（后续完善统一日志）

---

## 5) 项目结构关键入口

- UI：`src/myquant/ui/streamlit_app.py`
- 纸上交易：`src/myquant/execution/paper_broker.py`
- 项目结构说明：`docs/PROJECT_STRUCTURE.md`

---

## 6) 路线图与优先级（可勾选）

- [x] A1 UI：Streamlit 下单与行情展示（已加入）
- [x] A2 执行：`PaperBroker` 文件持久化（已加入）
- [ ] A3 数据：将 UI 的数据源替换为 `src/myquant/data/market/*` Provider
- [ ] B1 Provider：实现 `provider_base.py` 与一个真实 Provider（AkShare/TuShare/YFinance）
- [ ] B2 存储：`data/storage.py` 读写 Parquet/SQLite 与缓存
- [ ] B3 调度：`ingestion/scheduler.py` APScheduler 定时抓取
- [ ] C1 爬虫：`news/crawler/rss_crawler.py`（优先 RSS）
- [ ] C2 清洗：`parser/clean.py`、`parser/dedupe.py`
- [ ] C3 AI：`sentiment_pipeline.py`（摘要/情绪/主题）
- [ ] C4 融合：`features/fusion.py`（新闻因子与行情对齐）
- [ ] D1 因子：`features/factors.py`（动量/波动等）
- [ ] D2 策略：`strategy/example_mom_news.py`
- [ ] D3 回测：`backtest/engine.py` 与 `metrics.py`
- [ ] E1 订单：`execution/order_router.py` 更多订单类型
- [ ] E2 风控：`execution/risk.py` 规则化风控
- [ ] F1 CLI：`cli/main.py` 提供 `ingest/backtest/live` 子命令
- [ ] F2 日志：统一日志到 `logs/`
- [ ] F3 配置：`.env` + `config/settings.py`
- [ ] F4 测试：为核心模块补单测
- [ ] F5 部署：Docker/Compose（可选）

---

## 7) 常见问题 / 排错

- 无法拉取行情：
  - 检查网络或先忽略，UI 会使用演示数据继续工作。
  - 日后切换为本地缓存数据/其它数据源。
- 订单成交价为空：
  - 市价单依赖“最新价”，若无行情数据会被拒绝；请切换为限价单或确保行情获取正常。

- 前端显示“Backend health: backend unreachable”：
  - 确保后端已运行（在仓库根目录）：`PYTHONPATH=src python3 -m uvicorn myquant.api.server:app --reload --port 8000`
  - 若在 `web/` 目录运行：`python3 -m uvicorn myquant.api.server:app --reload --port 8000 --app-dir ../src`
  - 确保前端代理生效：`web/next.config.js` 将 `/api/*` 代理到 `http://localhost:8000`
  - 一键启动命令在 `web/package.json` 中使用 `python3 -m uvicorn`（已配置）

- pip/python 命令不可用：
  - 使用 `python3 -m pip ...`；若缺少 pip：`python3 -m ensurepip --upgrade`

- 端口被占用：
  - 后端改端口：`python3 -m uvicorn myquant.api.server:app --reload --port 8001`
  - 前端代理也需相应改写 `web/next.config.js`

---

## 8) Git 忽略与提交建议

- 已在根目录添加 `.gitignore`，忽略：
  - Python venv/缓存、数据与日志（`data/paper_trading_state.json`, `data/cache/`, `logs/`）
  - Node/Next 产物（`web/node_modules/`, `web/.next/`, 各类 lock/log）
- 如果构建产物已被 Git 追踪，可移除索引但保留文件：
  - `git rm -r --cached web/.next web/node_modules node_modules data/paper_trading_state.json data/cache logs`

---

（以上步骤已在前文覆盖，这里不再重复）

---

如需，我可以继续：
- 初始化 `data/market/provider_base.py` 与一个示例 Provider
- 新增 `.env.example` 字段与 `config/settings.py` 的最小配置读取
- 搭建 `ingestion/scheduler.py` 的定时抓取骨架

---

## 9) 模型监控 Demo（可选）

- 启动后端后，在新终端运行事件生成器（仓库根目录）：
  - `python3 -m myquant.model.demo_events --symbol AAPL --interval 8 --jitter 2`
- 打开前端页面的 “Model Monitor”，应每隔数秒看到新事件与状态刷新。
