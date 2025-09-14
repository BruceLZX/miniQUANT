# 阶段 A 详细计划（最小闭环）

目标：以最快速度跑通“可视化下单 + 行情展示 + 纸上交易持仓/订单持久化”，并为后续阶段（数据管道、新闻/AI、回测）打好接口与代码结构基础。

---

## Phase A 路线图（A1→A5，已按顺序整理）

- A1 后端基础（已完成）
  - FastAPI 应用、CORS、健康检查；市场/账户/订单核心路由。
  - 代码：`src/myquant/api/server.py`（bars/last/account/positions/orders/health）。
- A2 前端基础（已完成）
  - Next.js 仪表盘：唯一主动操作为“选定/更改股票”；价格只读监控。
  - 代码：`web/pages/index.tsx`、`web/lib/api.ts`。
- A3 一体化与开发体验（已完成）
  - `dev:all` 并发启动、代理与路径修正、.gitignore、Quick Start 文档。
  - 代码：`web/package.json`、`web/next.config.js`、`QUICK_START.md`、`.gitignore`。
- A4 模型监控通道（已完成）
  - 后端：schemas/events/monitor + API（`/api/model/status`, `/api/model/events`）。
  - 前端：Model Monitor 面板 + 8s 轮询；Demo 事件生成器。
  - 代码：`src/myquant/model/*`、`web/pages/index.tsx`。
- A5 账户与模型控制（进行中 / 下一步）
  - A5.1 账户摘要：本金、总收益率、年化收益率、周收益率（前端卡片 + 后端简化计算）。
  - A5.2 模型操作范围：Universe 盒子（搜索+ADD/移除）与“禁买”开关（后端持久化 + 风控校验）。

当前状态小结：A1–A4 已完成可用；A5 待实现（优先账户摘要，其次 Universe/禁买）。

## A 的范围与交付

- 范围：Streamlit 网页 UI、简化数据获取（yfinance 或演示数据）、纸上交易撮合与基础风控。
- 不做：实盘券商对接、完整回测引擎、复杂指标/研究性功能。
- 交付物：
  - 可运行 UI：`streamlit run src/myquant/ui/streamlit_app.py`
  - 稳定的“纸上交易”状态持久化：`data/paper_trading_state.json`
  - 基础风控校验与成交逻辑，基本的 PnL 和账户信息（现金/净值）
  - UI 组件化与指标开关，便于后续扩展

---

## A1 UI：组件化与指标

目标：将现有单文件 UI 拆成组件，支持基础技术指标与可切换开关；完善下单表单的校验与交互反馈。

功能清单：
- 股票选择与观察列表：从文本输入转为可配置来源（环境变量或配置文件）。
- 图表：
  - K 线 + 成交量；可选均线（MA5/10/20）和布林带（Bollinger）开关。
  - 区间选择（近 1M/3M/6M/1Y）。
- 下单面板：
  - 校验：数量>0；限价单需价格；市价单依赖最新价。
  - 反馈：提交后显示订单编号与成交价/拒绝原因。
- 持仓/订单表：
  - 新增盈亏列（未实现则先展示 NaN）；
  - 订单表展示成交价、成本、费用（如启用）。
- 新闻区：继续使用占位或读取 `data/news/news_sample.csv`。

代码结构：
- `src/myquant/ui/streamlit_app.py`（保留为入口）
- `src/myquant/ui/components/charts.py`：绘图与指标（Plotly）
- `src/myquant/ui/components/order_form.py`：下单表单与校验
- `src/myquant/ui/components/tables.py`：持仓/订单表
- `src/myquant/ui/components/news.py`：新闻列表渲染
- `src/myquant/ui/state.py`：会话状态与轻量缓存
- `src/myquant/ui/constants.py`：常量（默认观察列表、指标默认开关）

验收标准（DoD）：
- 单击开关可即时显示/隐藏指标；
- 表单校验生效，非法输入阻止下单并提示原因；
- 观察列表可通过配置覆盖，默认提供一组示例；
- 所有组件化文件被入口引入并正常渲染。

---

## A2 执行：PaperBroker 风控与 PnL

目标：在不牺牲简单性的前提下，增强 PaperBroker 的账户维度与基本风控能力。

功能清单：
- 账户字段：`cash`, `equity`, `positions`, `orders`, `trades`, `fees`。
- 风控规则（可配置，默认合理值）：
  - 单票最大仓位占净值上限（如 20%）。
  - 单笔最大下单金额/数量上限。
  - 总体仓位上限（多头净敞口）。
- 成交与费用：
  - 市价/限价即时成交（保持简单）；
  - 费用模型：按比例费率和/或最小门槛（可设为 0 关闭）。
- PnL 计算：
  - 未实现盈亏（基于最新价）；
  - 实现盈亏（卖出结转）；
  - 账户净值 = 现金 + 持仓市值。
- 状态持久化：兼容当前 JSON 文件结构，增加必要字段并提供版本号。

代码结构与接口：
- `src/myquant/execution/paper_broker.py`
  - 新增：账户对象、风控校验、费用模型、PnL 计算函数。
  - 新增：`get_account()` 返回汇总信息（现金/净值/持仓市值/杠杆等）。
- `src/myquant/execution/risk.py`（最小实现）：规则校验与错误码。

验收标准（DoD）：
- 超限下单被拒绝并返回明确原因；
- UI 能展示账户现金/净值与基本 PnL；
- 状态文件可删除以重置，重建后无崩溃；
- 回归：不配置风控与费用时的行为与当前一致或预期一致。

---

## A3 数据：适配器与缓存

目标：抽象一个最小的数据提供器接口，优先接入 yfinance；若失败则回退到演示数据；增加轻量缓存以减少重复请求。

功能清单：
- Provider 抽象：
  - `list_symbols()`（可选）、`fetch_bars(symbol, start, end, freq)`, `get_last_price(symbol)`。
- yfinance 实现：失败则抛出异常，UI 层接演示数据回退。
- 缓存：
  - 将最近一次 K 线数据以 Parquet 缓存在 `data/cache/`，TTL 配置（如 1 小时）。

代码结构：
- `src/myquant/data/market/provider_base.py`：接口定义
- `src/myquant/data/market/yfinance_provider.py`：实现（可直接复用 UI 现有逻辑）
- `src/myquant/data/market/storage.py`：读写 Parquet、TTL 判断
- UI 替换数据入口：`ui/components/charts.py` 调用 Provider 而非直接 yfinance

验收标准（DoD）：
- 正常网络下，UI 走 yfinance；无网络时，UI 自动回退演示数据；
- 二次打开同样区间，命中缓存明显更快；
- 接口边界明确、返回字段稳定，便于后续对接其它数据源。

---

## 实施顺序与粒度（建议）

1) A1-1 组件化拆分（不改功能）
2) A1-2 指标开关与图表增强（MA/Volume/Bollinger，可逐项合入）
3) A1-3 下单校验与表单 UX（校验/提示）
4) A2-1 账户与 PnL 字段（不启用风控/费用）
5) A2-2 风控与费用（可先开默认关闭）
6) A3-1 Provider 抽象 + yfinance 实现（UI 接入）
7) A3-2 缓存（Parquet + TTL）

每一小步都可独立合入，便于回滚与验证。

---

## 配置与参数（阶段 A）

- `.env` / 配置项（建议在后续 `config/settings.py` 接入）：
  - `UI_WATCHLIST="AAPL,MSFT,TSLA"`
  - `BROKER_MAX_SYMBOL_WEIGHT=0.2`（单票最大仓位）
  - `BROKER_MAX_ORDER_NOTIONAL=100000`（最大下单金额）
  - `BROKER_FEE_RATE=0.0005`（万五，0 表示关闭）
  - `DATA_CACHE_TTL_MINUTES=60`

---

## 最小验证清单（手工）

- UI 能启动并显示图表；切换指标可用；
- 提交限价/市价单：
  - 正常成交，持仓与订单表更新；
  - 超过风控阈值时被拒绝；
- 账户信息显示：现金、净值、未实现盈亏；
- 断网情况下仍能用演示数据画图和下单；
- 删除 `data/paper_trading_state.json` 后可重建，不报错。

---

准备好后，可按本计划从 A1-1 开始提交实现与验证。

---

# Node 前端 + FastAPI 后端（Phase A 变体）

为满足“前端用 Node.js、打开页面即可连上服务”的需求，阶段A提供等价的分离式方案：

## 架构与目录

- 后端（Python）：FastAPI 暴露最小交易与行情 API，复用 PaperBroker 和数据适配器。
  - 入口：`src/myquant/api/server.py`
  - 命令：`uvicorn myquant.api.server:app --reload --port 8000`
- 前端（Node.js）：Next.js(Typescript) 仪表盘，K线/下单/持仓订单/新闻。
  - 根目录：`web/`
  - API 客户端：`web/lib/api.ts`
  - 组件：`web/components/*`
- 本地一体化启动：
  - `web/package.json` 中定义 `dev:all` 使用 `concurrently` 同时启动 FastAPI 与 Next.js；
  - Next.js `next.config.js` 配置 `rewrites`，将 `/api/*` 代理到 `http://localhost:8000/api/*`，保证前端相对路径即可调用后端。

示例（计划层面，实施时落地）：
- `pip install -r requirements.txt` 安装后端依赖
- `npm run dev:all` = `concurrently "npm run dev" "uvicorn myquant.api.server:app --reload --port 8000"`
- 浏览器打开 `http://localhost:3000`，页面即刻能访问后端 API。

## 最小 API（Phase A 范围）

- 健康检查：`GET /api/health` → `{ status: "ok", ts }`
- 行情：
  - `GET /api/market/bars?symbol&start&end&freq`
  - `GET /api/market/last?symbol`
- 新闻：`GET /api/news?symbol&since`
- 账户：`GET /api/account`、`GET /api/positions`、`GET /api/orders`
- 下单：`POST /api/orders`
  - Body: `{ symbol, side: "BUY"|"SELL", qty: number, type: "MARKET"|"LIMIT", price?: number }`
 - Resp: `{ id, ts, status, fill_price, ... }`

备注：Phase A 的行情可由 yfinance 或演示数据驱动；账户字段可先精简，A2 再补齐。

---

## 补充：账户收益指标与模型控制（新增需求对齐）

一、账户收益指标（A2 扩展）
- 指标定义：
  - 本金 `principal`（默认通过环境变量配置，示例 `BROKER_PRINCIPAL=1_000_000`）。
  - 总收益/收益率：`total_return = equity - principal`；`total_return_pct = total_return / principal`。
  - 年化收益率：基于每日净值序列年化（按 252 交易日）或按起止日期换算（简化实现择一）。
  - 周收益率：`equity[t] / equity[t-7d] - 1`（需要记录每日净值）。
- 数据落地：
  - 每日收盘/定时将 `equity` 追加到 `logs/account/equity.csv`（date,equity）。
- 前端展示：
  - 账户摘要卡片：本金/年化/总收益率/周收益率（只读）。

二、模型控制与操作范围（A5 新增）
- 前端盒子：
  - Positions Box：只读展示持仓。
  - Operated Stocks（Universe Box）：展示“模型可操作的股票”，搜索框 + ADD 加入，支持移除。
  - 禁买开关：对某股票切换“禁止买入”，模型只能卖出、不可买入。
- 后端与持久化：
  - `data/model/universe.json`：`{"symbols": ["AAPL", ...]}`。
  - `data/model/controls.json`：`{"no_buy": ["TSLA", ...]}`。
- API 设计：
  - `GET /api/model/universe` → `{ symbols: string[] }`
  - `POST /api/model/universe` → `{ symbol }`（加入）
  - `DELETE /api/model/universe` → `{ symbol }`（移除）
  - `GET /api/model/controls` → `{ no_buy: string[] }`
  - `POST /api/model/controls/no_buy` → `{ symbol }`（添加禁买）
  - `DELETE /api/model/controls/no_buy` → `{ symbol }`（移除禁买）
  - 风控校验：BUY 请求若命中 `no_buy` 列表则拒绝。
- DoD：
  - 前端可管理 Universe；禁买开关生效并持久化；
  - 模型（或 demo）发出的 BUY 在禁买时被拒绝；
  - 刷新后状态一致、文件被 .gitignore 忽略。

三、进度快照补充
- [ ] A2N-2 增强账户摘要卡片（本金/年化/总收益率/周收益率）
- [ ] A5-1 Universe 与禁买控制的后端与持久化
- [ ] A5-2 前端 Operated Stocks 盒子（搜索 + ADD、禁买开关、移除）

## 阶段A（Node 变体）任务拆解与 DoD（更新：前端仅做“选定/更改股票”，其他模块只读监控）

- A1N 后端最小化（FastAPI）
  - 任务：实现上述路由，接入 `PaperBroker`；加 CORS；封装 yfinance/演示数据获取。
  - DoD：curl 下单可成交；能返回一段时间 K 线或演示数据；`/api/health` 返回 ok。
- A2N 前端骨架（Next.js + TS）
  - 任务：页面布局（股票选择为唯一主动操作；价格监控为只读；可选只读的账户/持仓/订单展示后续补充）。移除下单面板。
  - DoD：打开 `http://localhost:3000`，初始为空白选择框；选择股票后显示价格监控；可随时“更改”股票并刷新。
- A3N 一体化与打磨
  - 任务：`dev:all` 并发启动；`next.config.js` 代理 `/api/*`；空态/错误提示；健康检查提示“后端未运行”时的引导文案；（账户摘要为可选只读）。

---

## A4 模型监控（新增到阶段A范围）

目标：在不引入真实训练/推理复杂度的前提下，提供“模型状态与事件监控”的端到端通路（数据模型 → 事件持久化 → API → 前端展示）。

功能清单：
- 后端：
  - `schemas`：统一模型状态与事件的字段（status、last_run、symbol、signal、confidence、reason、risk_flags、error）。
  - `events`：将事件写入 `logs/model/events.jsonl`，提供读取最近 N 条的函数。
  - `monitor`：聚合运行状态（最近一次事件 + 基本统计）。
  - API：`GET /api/model/status`、`GET /api/model/events?limit=100`。
- 前端：
  - `Model Monitor` 面板：
    - 顶部显示 status/last_run/当前监控标的/数据延迟等概要；
    - 下方列表显示最近事件（时间、类型、信号、置信度、摘要）。
  - 轮询刷新（例如每 5–10s）和手动刷新按钮。

验收标准（DoD）：
- 配置或脚本可写入示例事件到 `logs/model/events.jsonl`；
- 前端能拉到 status 与最近事件列表并渲染；
- 空态与错误提示清晰，不依赖真实模型即可演示监控闭环。

实施顺序：
1) A4-1 定义 `schemas.py` 与示例事件格式
2) A4-2 `events.py` 写入/读取 JSONL + `monitor.py` 汇总状态
3) A4-3 API 路由 `/api/model/status`、`/api/model/events`
4) A4-4 前端 `Model Monitor` 面板与轮询
5) A4-5 补充文档与样例数据（可提供脚本生成 demo 事件）
  - DoD：一条命令启动前后端；页面各模块稳定可用；后端异常时前端能友好提示。

## 实施顺序（建议）

1) A1N-1 `server.py` 桩 + `/api/health`
2) A1N-2 行情/下单/账户/订单路由（不带风控）
3) A2N-1 Next.js scaffold + 基本页面与 API 客户端
4) A2N-2 K线组件与下单表单联通后端
5) A3N-1 `dev:all` 并发启动与代理配置
6) A3N-2 表单校验/错误提示/账户摘要

## 一体化开发体验（打开页面即可使用）

- 方案：通过 `npm run dev:all` 同时启动后端与前端；
- 浏览器只需访问 `http://localhost:3000`，前端自动走 `/api/*` 代理至后端；
- 可选：Docker Compose（后续阶段），`docker compose up` 即可并在 `localhost:3000` 使用。
