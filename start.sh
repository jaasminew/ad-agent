#!/bin/bash
# AD Agent - 启动完整系统 (前端 + 后端)

set -e

echo "======================================"
echo "AD Agent - Full Stack Launcher"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查后端环境变量
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}⚠️  Backend .env file not found!${NC}"
    echo "Please create backend/.env with required API keys"
    echo "See backend/.env.example for template"
    exit 1
fi

# 检查前端环境变量
if [ ! -f "frontend/.env" ]; then
    echo -e "${BLUE}📝 Creating frontend/.env...${NC}"
    cat > frontend/.env << EOF
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000
EOF
    echo -e "${GREEN}✓ Created frontend/.env${NC}"
    echo ""
fi

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo -e "${BLUE}📦 Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo ""
fi

# 检查 node
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "Please install Node.js >= 18 from https://nodejs.org"
    exit 1
fi

echo -e "${BLUE}🚀 Starting Backend...${NC}"
cd backend
uv run main.py &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo ""

# 等待后端启动
echo -e "${BLUE}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done
echo ""

echo -e "${BLUE}🎨 Starting Frontend...${NC}"
cd frontend

# 安装依赖 (如果需要)
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
    npm install
    echo ""
fi

npm run dev &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo ""

# 保存 PIDs
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo "======================================"
echo -e "${GREEN}✨ AD Agent is running!${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}📡 Backend API:${NC}  http://localhost:8000"
echo -e "${BLUE}📚 API Docs:${NC}     http://localhost:8000/docs"
echo -e "${BLUE}🌐 Frontend UI:${NC}  http://localhost:5173"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"
echo ""

# 捕获退出信号
cleanup() {
    echo ""
    echo -e "${BLUE}🛑 Stopping services...${NC}"
    
    if [ -f ".backend.pid" ]; then
        BACKEND_PID=$(cat .backend.pid)
        kill $BACKEND_PID 2>/dev/null || true
        rm .backend.pid
        echo -e "${GREEN}✓ Backend stopped${NC}"
    fi
    
    if [ -f ".frontend.pid" ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        kill $FRONTEND_PID 2>/dev/null || true
        rm .frontend.pid
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}👋 Goodbye!${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 保持脚本运行
wait

