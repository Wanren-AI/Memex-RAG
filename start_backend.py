"""
Backend Server Launcher
启动FastAPI后端服务器

- 检查环境变量（API_KEY等）
- 导入api_server
- 运行FastAPI服务器（uvicorn）
- 监听8000端口
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check environment
if not os.getenv("DASHSCOPE_API_KEY"):
    print("❌ 错误: 未设置 DASHSCOPE_API_KEY")
    print("请设置环境变量:")
    print("  export DASHSCOPE_API_KEY=your_key")
    sys.exit(1)

# Import and run

from api_server import main
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 启动 RAG API 服务器")
    print("=" * 60)
    print()
    print("API文档地址: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/health")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()

    main()