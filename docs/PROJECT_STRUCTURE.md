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
- 数据存储与缓存：本地 Parquet/SQLite 或外部数据库，统一读写。
- 调度与管道：定时抓取/清洗/特征/训练/执行的一体化流水线。
- 配置与密钥：环境变量与配置模板，避免泄露敏感信息。
 
---
 
## 2) 建议目录结构
 
```text
MyQuant/
├─ README.md
├─ .env.example                 # API Key 示例（请复制为 .env 并填写）
├─ pyproject.toml or requirements.txt
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
│     ├─ execution/
│     │  ├─ broker_base.py         # 券商/交易接口抽象
│     │  ├─ paper_broker.py        # 纸上交易/仿真
│     │  ├─ order_router.py        # 订单路由与撮合适配
│     │  └─ risk.py                # 风控与仓位管理
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
```
 
---
 
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
 
## 7) 初期落地建议（按优先级）
 
1. 选定编程语言与运行环境（默认 Python 3.10+）。
2. 确认数据源（如 TuShare/AkShare/YFinance 等）与最小行情字段集。
3. 选择 2–3 个稳定新闻源（优先 RSS/公告），做清洗+时间对齐。
4. 接一个 AI 客户端（本地或云端）用于摘要/情感，形成首个“新闻因子”。
5. 用简单动量因子 + 新闻情感因子做日频策略，跑通回测链路。
6. 接入纸上交易接口，形成端到端最小可用闭环。
 
---
 
如需，我可以基于该结构帮你：
- 初始化 `src/` 代码骨架与占位类
- 提供最小的 `cli` 命令（抓数据/跑回测/跑实时）
- 加入 `.env.example` 与基础配置读取

