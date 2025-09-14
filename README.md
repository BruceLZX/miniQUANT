# MyQuant

学习型量化交易项目：Node.js 前端（Next.js）+ Python 后端（FastAPI），配合“纸上交易”与“模型监控”通道，逐步扩展数据、特征、策略与回测。

• 快速开始与排错：见 `QUICK_START.md`
• 结构说明：见 `docs/PROJECT_STRUCTURE.md`
• 阶段计划/进度：见 `docs/PHASE_A_PLAN.md`

## 一键启动（本地联调）

1) 安装依赖（项目根目录）
- `python3 -m pip install -r requirements.txt`
- `cd web && npm install`

2) 启动前后端（推荐）
- `npm run dev:all`
- 打开 `http://localhost:3000`，顶部应显示 Backend health: ok
- 页面唯一主动操作为“选定/更改股票”，其余为只读监控；底部含 Model Monitor 面板

3) 备用方式（分开启动）
- 后端：在仓库根目录运行 `PYTHONPATH=src python3 -m uvicorn myquant.api.server:app --reload --port 8000`
- 前端：`cd web && npm run dev`

4) Streamlit 备用 UI（只读/下单 demo）
- `streamlit run src/myquant/ui/streamlit_app.py`

## 主要功能（Phase A）

- FastAPI 后端：行情（bars/last）、账户/持仓/订单、健康检查
- 纸上交易：文件持久化撮合，支持市价/限价
- 前端仪表盘：选股 + 价格监控；Model Monitor 面板（8s 轮询）
- 模型监控通道：事件 JSONL（`logs/model/events.jsonl`）+ 状态汇总 API
- Demo 事件生成器：`python3 -m myquant.model.demo_events --symbol AAPL`

下一步（A5）
- 账户摘要：本金/总收益率/年化/周收益率（前端卡片 + 后端简化计算）
- 模型控制：可操作股票（Universe）盒子 + “禁买”开关（后端持久化与风控校验）

## 关键目录

- 后端：`src/myquant/api/server.py`
- 纸上交易：`src/myquant/execution/paper_broker.py`
- 模型监控：`src/myquant/model/{schemas,events,monitor,demo_events}.py`
- 前端：`web/pages/index.tsx`, `web/lib/api.ts`, `web/next.config.js`

## 常见问题

- Backend health: backend unreachable
  - 确认后端已启动：`PYTHONPATH=src python3 -m uvicorn myquant.api.server:app --reload --port 8000`
  - 或临时直连后端：在 `web` 目录用 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev`

## 免责声明
本项目仅供学习与技术交流，不构成任何投资建议。
