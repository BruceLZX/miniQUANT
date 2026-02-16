#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/.run"
BACKEND_PORT=8000
FRONTEND_PORT=5273

stop_one() {
  local name="$1"
  local pid_file="$LOG_DIR/$name.pid"
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      echo "$name 已停止 (pid=$pid)"
    else
      echo "$name 进程不存在 (pid=$pid)"
    fi
    rm -f "$pid_file"
  else
    echo "$name 未运行"
  fi
}

stop_port() {
  local name="$1"
  local port="$2"
  local pid
  pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
  if [ -n "$pid" ]; then
    kill "$pid" || true
    echo "$name 端口进程已停止 (pid=$pid, port=$port)"
  fi
}

stop_one backend
stop_one frontend
stop_port backend "$BACKEND_PORT"
stop_port frontend "$FRONTEND_PORT"
