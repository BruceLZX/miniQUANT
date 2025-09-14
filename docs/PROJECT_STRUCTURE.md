# MyQuant 项目结构（建议草案）
 
> 面向学习与实践量化交易：覆盖“股市数据接口 + 新闻/舆情采集 + AI 分析 + 策略/回测 + 交易执行”。本结构便于后续逐步落地，每个模块都可替换/扩展。
 
---
 
## 1) 模块划分概览
 
- 市场数据接口：对接股票行情与基本面等数据源（可多数据源并存）。
- 新闻/舆情采集：RSS/网页爬虫，内容清洗去重，时间对齐。
- AI/NLP 接口：调用大模型进行摘要、情感/主题分类、实体识别等。
- 因子/特征工程：将行情与新闻信号融合成可用于建模的特征。
- 策略与信号：因子组合、打分与下单信号生成，含风控与仓位控制。
- 回测与评估：事件驱动或日频回测，绩效指标与报告。
- 交易执行：券商/仿真/纸上交易接口，订单路由与成交回报。
- 可视化 UI：Streamlit 网页端下单面板，行情/新闻/下单/持仓展示。
- 可视化 UI（可选 Node）：Next.js 前端（TS），通过 FastAPI 后端提供的 `/api/*` 服务联通。前端唯一主动操作为“选定/更改股票”，其余均为只读监控。
 - 模型监控：监控模型运行状态、最近决策/信号、下单动作、风控与绩效；提供后端 API 与前端面板。
- 数据存储与缓存：本地 Parquet/SQLite 或外部数据库，统一读写。
- 调度与管道：定时抓取/清洗/特征/训练/执行的一体化流水线。
- 配置与密钥：环境变量与配置模板，避免泄露敏感信息。
 
---
 
## 2) 建议目录结构（含已实现部分）
 
```text
MyQuant/
├─ README.md                    # 可选：总览/索引
├─ QUICK_START.md               # 快速开始（新增）
├─ .env.example                 # API Key 示例（请复制为 .env 并填写）
├─ pyproject.toml or requirements.txt  # 统一依赖（包含后端与 Streamlit UI）
├─ notebooks/                   # 研究/实验 Notebook
├─ docs/
│  └─ PROJECT_STRUCTURE.md      # 本文档
├─ data/                        # 原始数据与中间结果（可 .gitignore）
├─ logs/                        # 运行日志
├─ src/
│  └─ myquant/
│     ├─ __init__.py
│     ├─ config/
│     │  ├─ settings.py         # 统一读取 .env / YAML 配置
│     │  └─ secrets_template.yaml
│     ├─ data/
│     │  ├─ market/
│     │  │  ├─ provider_base.py     # 市场数据接口抽象
│     │  │  ├─ tushare_provider.py  # 示例占位（可替换/扩展）
│     │  │  ├─ yfinance_provider.py # 示例占位
│     │  │  └─ storage.py           # 统一存取（parquet/sql）
│     │  ├─ news/
│     │  │  ├─ crawler/
│     │  │  │  ├─ base.py           # 爬虫抽象（遵守 robots.txt）
│     │  │  │  ├─ rss_crawler.py    # RSS 源抓取
│     │  │  │  └─ web_crawler.py    # 网页抓取（需频控、去重）
│     │  │  ├─ parser/
│     │  │  │  ├─ clean.py          # HTML 清洗、正文提取
│     │  │  │  └─ dedupe.py         # 去重/聚类
│     │  │  └─ sentiment/
│     │  │     ├─ ai_client_base.py     # AI 客户端抽象
│     │  │     ├─ openai_client.py      # 示例占位（可本地/云端）
│     │  │     └─ sentiment_pipeline.py # 摘要/情感/主题打分流水线
│     │  └─ ingestion/
│     │     ├─ pipelines.py        # ETL/ELT 数据流水线编排
│     │     └─ scheduler.py        # 定时任务（如 APScheduler）
│     ├─ features/
│     │  ├─ factors.py             # 价量/财务/事件等因子
│     │  └─ fusion.py              # 行情与新闻信号融合/对齐
│     ├─ strategy/
│     │  ├─ base.py                # 策略与信号接口
│     │  └─ example_mom_news.py    # 示例：动量 + 新闻情感
│     ├─ backtest/
│     │  ├─ engine.py              # 回测引擎（事件/日频）
│     │  ├─ metrics.py             # 收益/波动/回撤/IC 等
│     │  └─ reports.py             # 可视化/报告
│     ├─ model/
│     │  ├─ __init__.py
│     │  ├─ runner.py              # 模型运行入口（轮询/事件驱动）
│     │  ├─ monitor.py             # 采集运行状态、汇总指标
│     │  ├─ schemas.py             # 状态/事件/信号的数据模型
│     │  └─ events.py              # 事件记录与持久化（JSONL/NDJSON）
│     ├─ execution/
│     │  ├─ broker_base.py         # 券商/交易接口抽象
│     │  ├─ paper_broker.py        # 纸上交易/仿真（已添加，文件持久化）
│     │  ├─ order_router.py        # 订单路由与撮合适配
│     │  └─ risk.py                # 风控与仓位管理
│     ├─ ui/
│     │  ├─ __init__.py
│     │  └─ streamlit_app.py       # 可视化下单面板（已添加）
│     ├─ api/
│     │  └─ server.py              # FastAPI 后端（Node 前端方案所需）
│     ├─ cli/
│     │  ├─ main.py                # 命令行入口（ingest/backtest/live）
│     │  └─ jobs/
│     │     ├─ ingest_data.py
│     │     ├─ run_backtest.py
│     │     └─ run_live.py
│     └─ utils/
│        ├─ logging.py             # 统一日志
│        ├─ time.py                # 交易日/时区
│        └─ cache.py               # 简单缓存/速率限制
└─ tests/                          # 单元/集成测试

（Node 前端可选结构）
web/
├─ package.json                    # 包含 `dev:all` 并发启动脚本（前后端）
├─ next.config.js                  # `/api/*` 代理至后端 FastAPI
├─ app/ 或 pages/                  # 页面路由
├─ components/                     # Chart/ModelMonitor/News 等
└─ lib/api.ts                      # API 客户端（可用 React Query）

根目录
├─ .gitignore                      # 忽略 venv、node_modules、.next、数据与日志等
```

---

## 已实现组件（快速索引）

- 后端 API：`src/myquant/api/server.py`（健康检查/行情/账户与订单/模型监控）
- 纸上交易：`src/myquant/execution/paper_broker.py`（文件持久化）
- 模型监控：
  - `src/myquant/model/schemas.py`（结构）
  - `src/myquant/model/events.py`（事件读写，`logs/model/events.jsonl`）
  - `src/myquant/model/monitor.py`（状态聚合）
  - `src/myquant/model/demo_events.py`（示例事件生成器）
- 前端（Node）：
  - 页面：`web/pages/index.tsx`（选股 + 价格监控 + Model Monitor）
  - API 客户端：`web/lib/api.ts`
  - 启动与代理：`web/package.json`, `web/next.config.js`

## 下一步（短期）

- 前端：加入只读 K 线图与账户摘要卡片
- 数据：实现 `data/market` Provider 抽象 + `yfinance_provider` + 缓存
- 前端 UX：完善错误/空态与加载提示

## 3) 数据流与处理步骤（高层）
 
1. 市场数据抓取：按日/分钟频率拉取行情与基础数据，落地存储。
2. 新闻采集：RSS/网页源抓取，内容清洗、去重、时间戳与标的映射。
3. AI 分析：对新闻做摘要、情感/主题打分、实体识别（公司/事件）。
4. 特征工程：将行情因子与新闻因子按时间对齐，构造成训练/推理特征。
5. 策略与信号：基于特征计算多空/权重信号，附风控与持仓约束。
6. 回测评估：产出收益、回撤、信息比率、IC、Turnover 等指标与报告。
7. 交易执行：在仿真/实盘中下单与跟踪成交，记录日志与报表。
 
简图：
 
```
[Market Data] ─┐
                ├─> [Storage] ─> [Features] ─> [Strategy] ─> [Backtest/Live]
[News/Crawler] ─┘             └> [AI Sentiment/Topics] ─┘
```

---

## 4) 接口抽象（建议最小集合）
 
```python
# 市场数据（示意）
class MarketDataProvider:
    def list_symbols(self): ...
    def fetch_bars(self, symbol, start, end, freq="1d"): ...
    def fundamentals(self, symbol, fields=None): ...

# 新闻爬虫（示意）
class NewsCrawler:
    def crawl(self, since): ...          # 返回 [Article]
    def fetch_feed(self, url, since): ...

# AI 客户端（示意）
class AIClient:
    def summarize(self, text, max_tokens=256): ...
    def sentiment(self, text): ...
    def classify(self, text, labels): ...

# 券商/交易接口（示意）
class Broker:
    def get_positions(self): ...
    def place_order(self, symbol, side, qty, order_type, price=None): ...
    def cancel_order(self, order_id): ...
```
 
---
 
## 5) 配置与密钥管理
 
- `.env.example`：提供所需的环境变量模板（如数据源 Token、AI Key、券商 Key）。
- `src/myquant/config/settings.py`：集中加载 `.env`/YAML 并暴露配置对象。
- 运行时通过环境变量覆盖，避免在代码中硬编码敏感信息。

---

## 6) 爬虫与合规注意
 
- 遵守网站 `robots.txt` 与服务条款；仅抓取允许的公开信息。
- 加入速率限制、重试与指纹隔离；保留抓取日志与来源字段。
- 尽量优先 RSS、官方公告渠道，减少对目标站点压力与合规风险。

---

## 7) 网页 UI 说明（已落地）

- 路径：`src/myquant/ui/streamlit_app.py`
- 依赖：统一在 `requirements.txt` 中（`streamlit`, `plotly`, `pandas`, `numpy`, `yfinance` 等）
- 功能：
  - 股票选择、日期与频率切换，K 线展示
  - 新闻与情绪占位读取：`data/news/news_sample.csv`
  - 下单表单（买/卖、市价/限价），成交回写到 `data/paper_trading_state.json`
  - 持仓与订单列表展示
- 运行：`streamlit run src/myquant/ui/streamlit_app.py`

---

## 8) 项目实施路线图（细化与优先级）

阶段 A：最小闭环（已进行/优先完成）
- A1 UI：Streamlit 下单面板与行情可视化（已添加，继续完善折线/K线指标）
- A2 执行：`PaperBroker` 文件持久化、基础风控参数（单票/总仓上限）
- A3 数据：临时使用 `yfinance` 或本地演示数据，保证 UI 可用

阶段 B：数据与管道
- B1 市场数据：实现 `data/market/provider_base.py` 与一个真实 Provider（如 AkShare/TuShare/YFinance）
- B2 存储：`data/storage.py` 统一 Parquet/SQLite 读写，缓存日线/分钟线
- B3 调度：`data/ingestion/scheduler.py` 使用 APScheduler 定时抓取与清洗

阶段 C：新闻与 AI
- C1 爬虫：`data/news/crawler/rss_crawler.py` 优先 RSS；`web_crawler.py` 次之
- C2 清洗：`parser/clean.py`、`parser/dedupe.py` 去噪/抽取/去重
- C3 AI：`sentiment/ai_client_base.py` + `openai_client.py`；`sentiment_pipeline.py` 产生摘要/情绪/主题
- C4 融合：`features/fusion.py` 将新闻因子与行情因子时间对齐

阶段 D：策略与回测
- D1 因子：`features/factors.py` 动量/波动/价值等基础因子
- D2 策略：`strategy/example_mom_news.py` 动量 + 新闻情绪示例策略
- D3 回测：`backtest/engine.py` 与 `metrics.py`，生成绩效与报告

阶段 E：交易与风控强化
- E1 订单：`execution/order_router.py` 支持更多订单类型与撮合模拟
- E2 风控：`execution/risk.py` 规则化风控（单票/行业/整体杠杆）
- E3 券商：对接第三方仿真或实盘 API（按需）

阶段 F：工程化与可运维
- F1 CLI：`cli/main.py` 提供 `ingest/backtest/live` 子命令
- F2 日志：统一日志与追踪，`logs/` 结构标准化
- F3 配置：`.env` + `config/settings.py` 支持多环境
- F4 测试：为 `broker`, `features`, `backtest` 核心模块补单测
- F5 部署：Dockerfile/Compose（可选），本地/云端运行

每阶段的完成定义（DoD）建议写入 `QUICK_START.md` 或 `README.md`，便于跨工作区协作。

---

## 9) 跨工作区协作提示

- 固定入口：
  - 网页 UI：`streamlit run src/myquant/ui/streamlit_app.py`
  - 数据存储：`data/`；新闻样例：`data/news/news_sample.csv`
  - 纸上交易状态：`data/paper_trading_state.json`（删除可重置）
- 环境：复制 `.env.example` 为 `.env` 并填充必要 Key。
- 依赖：`pip install -r requirements.txt`（或按需使用 `pyproject.toml`）

---

如需，我可以：
- 初始化 `data/market/provider_base.py` 与一个 Provider 骨架
- 加入 `.env.example` 模板字段与 `config/settings.py` 最小实现
- 搭建 `ingestion/scheduler.py` 与 `pipelines.py` 的最小可运行版本
数据与日志（建议）
- `logs/model/events.jsonl`：模型事件（决策、下单、风险、异常）按行记录，便于追溯。
- `data/cache/`：行情缓存；`data/news/`：新闻与情绪。

后端新增 API（模型监控，计划中）
- `GET /api/model/status`：当前状态（idle/running/error、last_run、watch_symbol、latency 等）
- `GET /api/model/events?limit=100`：最近事件列表（决策/下单/风险/异常），来源于 JSONL 或内存缓冲。
