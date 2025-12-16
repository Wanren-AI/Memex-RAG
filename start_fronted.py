"""
Frontend Web UI Launcher
启动Gradio前端界面
- 检查后端是否已启动
- 导入web_ui_api
- 运行Gradio服务器
- 监听7862端口
"""
import sys
from pathlib import Path
import requests

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_backend():
    """检查后端服务器是否运行"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🎨 启动 Web UI (前端)")
    print("=" * 60)
    print()

    # Check backend
    print("🔍 检查后端服务器...")
    if check_backend():
        print("✅ 后端服务器正在运行")
    else:
        print("⚠️  警告: 后端服务器未运行")
        print()
        print("请先启动后端服务器:")
        print("  python start_backend.py")
        print()
        print("或者选择:")
        print("  1. 按 Enter 继续启动前端（需要手动启动后端）")
        print("  2. 按 Ctrl+C 取消")
        try:
            input()
        except KeyboardInterrupt:
            print("\n已取消")
            sys.exit(0)

    print()
    print("Web界面地址: http://localhost:7862")
    print()
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    print()

    # Import and run
    from web_ui_api import main

    main()