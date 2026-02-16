#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.run"
FRONTEND_PORT=5273
BACKEND_PORT=8000
mkdir -p "$LOG_DIR"

wait_http_ok() {
  local url="$1"
  local name="$2"
  local retries=20
  local i
  for i in $(seq 1 "$retries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "$name 启动失败，检查日志: $LOG_DIR/${name}.log"
  return 1
}

find_listen_pid() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n1 || true
}

if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
  echo "backend 虚拟环境不存在：$BACKEND_DIR/.venv"
  echo "请先运行: cd $BACKEND_DIR && python3.11 -m venv .venv && ./.venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

# backend
backend_pid=""
if [ -f "$LOG_DIR/backend.pid" ] && kill -0 "$(cat "$LOG_DIR/backend.pid")" 2>/dev/null; then
  backend_pid="$(cat "$LOG_DIR/backend.pid")"
  echo "backend 已在运行 (pid=$backend_pid)"
elif backend_pid="$(find_listen_pid "$BACKEND_PORT")" && [ -n "$backend_pid" ]; then
  echo "$backend_pid" >"$LOG_DIR/backend.pid"
  echo "backend 端口已被占用，复用现有进程 (pid=$backend_pid)"
else
  (
    cd "$BACKEND_DIR"
    nohup ./.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port "$BACKEND_PORT" </dev/null >"$LOG_DIR/backend.log" 2>&1 &
    echo $! >"$LOG_DIR/backend.pid"
  )
  echo "backend 已启动 (pid=$(cat "$LOG_DIR/backend.pid"))"
fi
wait_http_ok "http://127.0.0.1:$BACKEND_PORT/health" "backend"

# frontend
frontend_pid=""
if [ -f "$LOG_DIR/frontend.pid" ] && kill -0 "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null; then
  frontend_pid="$(cat "$LOG_DIR/frontend.pid")"
  echo "frontend 已在运行 (pid=$frontend_pid)"
elif frontend_pid="$(find_listen_pid "$FRONTEND_PORT")" && [ -n "$frontend_pid" ]; then
  echo "$frontend_pid" >"$LOG_DIR/frontend.pid"
  echo "frontend 端口已被占用，复用现有进程 (pid=$frontend_pid)"
else
  (
    cd "$FRONTEND_DIR"
    nohup python3 -m http.server "$FRONTEND_PORT" </dev/null >"$LOG_DIR/frontend.log" 2>&1 &
    echo $! >"$LOG_DIR/frontend.pid"
  )
  echo "frontend 已启动 (pid=$(cat "$LOG_DIR/frontend.pid"))"
fi
wait_http_ok "http://127.0.0.1:$FRONTEND_PORT/index.html" "frontend"

echo "前端地址: http://127.0.0.1:$FRONTEND_PORT"
echo "后端地址: http://127.0.0.1:$BACKEND_PORT"
