#!/bin/bash

# xRAG文档分析助手 - 快速启动脚本
# Quick Start Script for xRAG Document Assistant

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 RAG 文档分析助手 - 快速启动"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Python版本
echo "📋 检查环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 Python3${NC}"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查环境变量
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量${NC}"
    echo ""
    echo "请设置API密钥："
    echo "  export DASHSCOPE_API_KEY='your_api_key'"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ API密钥已设置${NC}"
fi

# 检查依赖
echo ""
echo "📦 检查依赖包..."
if ! python3 -c "import gradio" &> /dev/null; then
    echo -e "${YELLOW}⚠️  未找到必要依赖包${NC}"
    read -p "是否自动安装依赖？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在安装依赖..."
        pip install -r requirements.txt --break-system-packages
        echo -e "${GREEN}✓ 依赖安装完成${NC}"
    else
        echo "请手动运行: pip install -r requirements.txt"
        exit 1
    fi
else
    echo -e "${GREEN}✓ 依赖包已安装${NC}"
fi

# 创建必要目录
echo ""
echo "📁 创建工作目录..."
mkdir -p knowledge_base
mkdir -p vector_store
mkdir -p logs
mkdir -p .rag_config
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 启动后端
echo ""
echo "=========================================="
echo "🔧 启动后端服务 (端口 8000)"
echo "=========================================="
python3 start_backend.py &
BACKEND_PID=$!
echo "后端进程 PID: $BACKEND_PID"

# 等待后端启动
echo ""
echo "⏳ 等待后端服务启动..."
MAX_WAIT=30
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务已启动${NC}"
        break
    fi
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
    echo -n "."
done
echo ""

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ 后端服务启动超时${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 启动前端
echo ""
echo "=========================================="
echo "🎨 启动前端服务 (端口 7862)"
echo "=========================================="
python3 start_fronted.py &
FRONTEND_PID=$!
echo "前端进程 PID: $FRONTEND_PID"

# 等待前端启动
echo ""
echo "⏳ 等待前端服务启动..."
sleep 5

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 启动完成！${NC}"
echo "=========================================="
echo ""
echo "📌 服务地址："
echo "  前端界面: http://localhost:7862"
echo "  后端API:  http://localhost:8000"
echo "  API文档:  http://localhost:8000/docs"
echo ""
echo "📝 进程信息："
echo "  后端 PID: $BACKEND_PID"
echo "  前端 PID: $FRONTEND_PID"
echo ""
echo "⚠️  按 Ctrl+C 停止所有服务"
echo ""

# 保存PID到文件
echo $BACKEND_PID > .rag_backend.pid
echo $FRONTEND_PID > .rag_frontend.pid

# 等待用户中断
trap "echo ''; echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .rag_backend.pid .rag_frontend.pid; echo -e '${GREEN}✓ 服务已停止${NC}'; exit 0" INT TERM

# 保持脚本运行
wait