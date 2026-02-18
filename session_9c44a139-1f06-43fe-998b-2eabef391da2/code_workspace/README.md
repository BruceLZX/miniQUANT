# MyQuant

MyQuant 是一个多 Agent 驱动的量化交易控制台：
- 前端用于配置、监控和人工干预。
- 后端负责 D1-D7 分析链路、D5 量化融合、D6 决策与模拟交易执行。

## 核心能力
- 多部门协作分析（D1 宏观、D2 行业、D3 单股、D4 材料、D5 量化、D6 投委会、D7 选股）
- 每股独立进度与决策闭环
- 可配置多模型（OpenAI/Kimi/GLM/DeepSeek）与实时可用性检测
- D7 分短中长期推荐，人工确认入池
- Paper trading 执行与交易约束（每日/每周交易规则）
- 记忆系统（有用保留、无用淘汰、重启恢复）

## 快速启动
```bash
cd session_9c44a139-1f06-43fe-998b-2eabef391da2/code_workspace/backend
python3.11 -m venv .venv
./.venv/bin/pip install -r requirements.txt

cd ../
./start_services.sh
```

启动后：
- Frontend: `http://127.0.0.1:5273`
- Backend: `http://127.0.0.1:8000`
- API Docs: `http://127.0.0.1:8000/docs`

停止：
```bash
./stop_services.sh
```

## 目录概览
```text
code_workspace/
├── backend/                # FastAPI + 调度 + 交易 + 记忆 + agents
├── frontend/               # HTML 控制台页面
├── manual.md               # 运行手册（用户操作导向）
├── PROJECT_MANAGEMENT.md   # 项目管理与工程协作文档
├── start_services.sh
└── stop_services.sh
```

## 说明
- `manual.md` 偏“使用与部署”。
- `PROJECT_MANAGEMENT.md` 偏“团队开发管理与工程规范”。
