# MyQuant 项目手册（运行 + 架构 + 设计 + 文档方向）

最后更新：2026-02-16

## 1. 手册目标
这份文档用于四件事：
1. 快速启动系统（前端操作 + 后端自动运行）。
2. 说明当前工程架构与关键模块职责。
3. 说明关键设计规则（交易规则、调度、记忆、D4/D5特殊逻辑）。
4. 给出后续文档维护方向，避免项目继续“靠口头同步”。

---

## 2. 快速启动（How To Start）

### 2.1 首次准备（只做一次）
```bash
cd session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace/backend
python3.11 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

如果你机器没有 `python3.11`，可用 `python3` 创建 venv，但要确保依赖可安装。

### 2.2 一键启动前后端
```bash
cd session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace
./start_services.sh
```

启动成功后：
- 前端：`http://127.0.0.1:5273`
- 后端：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/docs`

### 2.3 停止服务
```bash
cd session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace
./stop_services.sh
```

### 2.4 日志位置
- `session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace/.run/backend.log`
- `session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace/.run/frontend.log`

---

## 3. 用户侧标准流程
1. 打开前端页面。
2. 在 Settings 填 API Key 与模型 ID。
3. 先做可用性检测（`/api/config/validate`）。
4. 运行 D7（手动触发）拿候选池。
5. 人工把候选股票加入交易池。
6. 运行一轮 D1-D6（`run-once`）或让调度器自动跑。
7. 在 Dashboard 查看每只股票卡片、部门状态、最终交易决策。

---

## 4. 项目架构（Architecture）

### 4.1 目录结构
```text
code_workspace/
├── backend/
│   ├── api/main.py                 # FastAPI 路由入口
│   ├── core/scheduler.py           # 调度中枢（D1-D7编排/持久化/任务）
│   ├── departments/                # D1 D2 D3 D4 D6 D7
│   ├── quantitative/d5_quant.py    # D5 量化融合与训练
│   ├── trading/paper_trading.py    # 模拟交易引擎与交易约束
│   ├── memory/memory_store.py      # 记忆系统（STM/LTM/Ephemeral）
│   ├── data/data_collector.py      # 市场/新闻数据采集
│   ├── config/settings.py          # 系统配置（频率/模型/风控）
│   └── .runtime_state.json         # 运行态持久化
├── frontend/
│   ├── index.html                  # 配置入口
│   └── platform.html               # 交易平台主界面
├── start_services.sh               # 一键启动脚本
└── stop_services.sh                # 一键停止脚本
```

### 4.2 运行分层
- UI 层：`frontend/index.html` + `frontend/platform.html`
- API 层：`backend/api/main.py`
- 编排层：`backend/core/scheduler.py`
- 策略层：`backend/departments/*` + `backend/quantitative/d5_quant.py`
- 执行层：`backend/trading/paper_trading.py`
- 记忆层：`backend/memory/memory_store.py`
- 数据层：`backend/data/data_collector.py`

---

## 5. 关键设计细节（当前实现口径）

### 5.1 部门职责与关系
- D1（宏观）/D5（量化）为共享部门。
- D2 D3 D4 D6 为每只股票独立运行。
- D7 独立，负责推荐，不自动入池。

### 5.2 交易硬规则
- 每只股票：每天最多交易 2 次。
- 每只股票：每周最多 2 个交易日可交易。
- 规则在交易执行前强制校验，不是仅 UI 提示。

### 5.3 调度与频率
默认（可在配置中修改）：
- D1: 60 分钟
- D2: 60 分钟
- D3: 60 分钟
- D4: 360 分钟
- D5: 可配置（当前为高频）
- D6: 30 分钟
- D7: 手动触发

### 5.4 D4 材料策略（已按最新需求）
- 用户粘贴的原始文本/图片：不持久化（进程内临时队列）。
- D4 分析结论：持久化到记忆和股票案例。
- 目的：保护隐私 + 减少无用存储，同时保留可复用结论。

### 5.5 记忆策略（MCP风格）
记忆分层：
- LTM：长期（高价值、结构性结论）
- STM：中短期（近期策略与判断）
- Ephemeral：低价值短暂记忆

写入时自动评估：
- 根据分数、置信度、证据数、风险/行动语义决定是否保留。
- 低价值信息会丢弃。
- 高价值信息会进入 STM/LTM。
- 所有保留条目附带时间戳和保留决策元数据。
- 超容量时自动裁剪（按重要性/访问频次/时效）。

### 5.6 D5 策略与训练
- D5 不依赖外部 LLM API 才能运行核心量化逻辑。
- 训练为“运行时在线校准”，不是离线大模型训练流水线。
- D5 现已改为按股票并发执行，避免“排队感”。

### 5.7 D7 选股策略
- 输出短/中/长三类候选。
- 会排除已在交易池内股票。
- 会参考历史推荐避免过高重复。
- 用户手动决定是否入池。

### 5.8 行情与交易数据
- 实时行情优先走公开行情源，失败则用历史缓存，不再随机造假数据。
- 若行情源不可用，会明确返回 unavailable/fallback，而不是伪造“正常数据”。

---

## 6. 核心 API 清单（按功能分组）

### 6.1 股票与分析
- `POST /api/stocks/add`
- `POST /api/stocks/remove`
- `GET /api/stocks/list`
- `GET /api/analysis/all`
- `GET /api/analysis/{symbol}`
- `GET /api/departments/{symbol}`

### 6.2 系统调度
- `POST /api/system/start`
- `POST /api/system/stop`
- `POST /api/system/run-once`
- `POST /api/system/run-d7`
- `GET /api/system/progress`
- `GET /api/system/jobs`
- `GET /api/system/status`

### 6.3 D7 / D4 / D5
- `GET /api/d7/recommendations`
- `POST /api/d7/select`
- `POST /api/materials/upload`
- `GET /api/materials/list`
- `POST /api/d5/train`
- `GET /api/d5/train/report`

### 6.4 配置与模型
- `POST /api/config/update`
- `GET /api/config/current`
- `POST /api/config/validate`
- `GET /api/config/models/{provider}`

### 6.5 交易与行情
- `GET /api/trading/account`
- `GET /api/trading/positions`
- `GET /api/trading/history`
- `GET /api/market/quote/{symbol}`

### 6.6 健康检查
- `GET /health`

---

## 7. 运行态持久化策略

### 7.1 当前会持久化
- 股票池、股票案例、部门结论
- D5训练状态与交易引擎状态
- 任务进度、D7推荐历史
- 记忆条目（经保留策略筛选后）

### 7.2 当前不会持久化
- D4 用户上传的原始文本/图片内容

---

## 8. 常见问题（Troubleshooting）

### 8.1 前端提交配置报 `Failed to fetch`
优先检查：
1. 后端是否启动：`curl http://127.0.0.1:8000/health`
2. 页面里的后端地址是否为 `http://127.0.0.1:8000`
3. 浏览器是否有跨域/端口冲突插件拦截

### 8.2 模型验证失败（401）
- API Key 无效或前后有空格/换行。
- Provider 与模型 ID 不匹配。
- Kimi 在美国区应走 `https://api.moonshot.ai/v1`。

### 8.3 某股票数据缺失
- 先确认代码有效（避免 APPL 这类拼写错误）。
- 检查 `/api/market/quote/{symbol}` 返回详情。

### 8.4 D5 看起来不工作
- 看 `/api/system/progress` 的 D5 状态。
- 看 `/api/d5/train/report` 是否样本不足（这不是故障，是当前训练策略的保护逻辑）。

---

## 9. 文档维护方向（Documentation Direction）
后续建议文档拆分为 5 条主线，并固定更新责任：

1. `docs/architecture.md`
- 目标：系统全景图、模块边界、调用链。
- 更新触发：新增/移除模块，或大改编排策略。

2. `docs/api-contract.md`
- 目标：所有 API 入参/出参/错误码。
- 更新触发：任何接口字段变更。

3. `docs/strategy-rules.md`
- 目标：交易规则、D5融合逻辑、D7选股规则、风控阈值。
- 更新触发：策略参数调整、规则变化。

4. `docs/state-persistence.md`
- 目标：哪些数据会/不会持久化，重启恢复行为。
- 更新触发：持久化字段变化（尤其 D4、memory）。

5. `docs/ops-runbook.md`
- 目标：部署/启动/监控/回滚/排障流程。
- 更新触发：启动方式、依赖版本、运维脚本变化。

建议把这份 `manual.md` 当“用户+开发入口手册”，上面 5 份是“深入手册”。

### 9.1 记忆/MCP 路线图
当前已完成：
1. 语义检索 + 规则检索混合召回（memory retrieval）。
2. 交易结果反馈学习（根据 PnL 动态调整 memory importance）。

下一阶段（未来计划）：
3. 标准 MCP 服务化：
- 把记忆系统从应用内模块抽成独立 MCP Memory Service。
- 提供标准化 resource/tool 接口给各部门调用。
- 增加跨进程权限控制与审计追踪，支持外部 agent 统一接入。

---

## 10. 版本变更记录（本次）
- 明确一键启动与停止流程。
- 补全当前架构分层和目录职责。
- 写清 D4 原始材料不持久化、D4结论持久化。
- 写清记忆保留策略（有用保留、无用淘汰）。
- 写清 D5 并发执行与在线校准定位。
- 补全 API 分组索引与文档维护方向。
