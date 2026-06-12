#!/bin/bash
# LitPilot 本地开发启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== LitPilot 本地开发启动 ==="

# 启动后端
echo "[1/2] 启动 FastAPI 后端..."
cd "$PROJECT_ROOT/backend"
if [ ! -d ".venv" ]; then
    echo "  创建 Python 虚拟环境..."
    python3.14 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID (http://localhost:8000)"

# 启动前端
echo "[2/2] 启动 Next.js 前端..."
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo "  安装前端依赖..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID (http://localhost:3000)"

echo ""
echo "=== LitPilot 已启动 ==="
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8000"
echo "  API:  http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

cleanup() {
    echo ""
    echo "停止服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

wait
