@echo off
REM RAG文档分析助手 - Windows快速启动脚本
REM Quick Start Script for Windows

chcp 65001 >nul 2>&1
color 0A

echo ==========================================
echo 🚀 RAG 文档分析助手 - 快速启动
echo ==========================================
echo.

REM 检查Python
echo 📋 检查环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.8 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python 版本: %PYTHON_VERSION%

REM 检查环境变量
if "%DASHSCOPE_API_KEY%"=="" (
    echo.
    echo ⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量
    echo.
    echo 请设置API密钥：
    echo   方式1: 临时设置（本次运行有效）
    echo   set DASHSCOPE_API_KEY=your_api_key
    echo.
    echo   方式2: 永久设置（系统环境变量）
    echo   控制面板 ^> 系统 ^> 高级系统设置 ^> 环境变量
    echo.
    set /p continue="是否继续？(y/n): "
    if /i not "%continue%"=="y" exit /b 1
) else (
    echo ✓ API密钥已设置
)

REM 检查依赖
echo.
echo 📦 检查依赖包...
python -c "import gradio" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  未找到必要依赖包
    set /p install="是否自动安装依赖？(y/n): "
    if /i "%install%"=="y" (
        echo 正在安装依赖...
        pip install -r requirements.txt
        echo ✓ 依赖安装完成
    ) else (
        echo 请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
) else (
    echo ✓ 依赖包已安装
)

REM 创建必要目录
echo.
echo 📁 创建工作目录...
if not exist "knowledge_base" mkdir knowledge_base
if not exist "vector_store" mkdir vector_store
if not exist "logs" mkdir logs
if not exist ".rag_config" mkdir .rag_config
echo ✓ 目录创建完成

REM 启动后端
echo.
echo ==========================================
echo 🔧 启动后端服务 (端口 8000)
echo ==========================================
start "RAG后端" python start_backend.py
echo 后端服务已启动

REM 等待后端启动
echo.
echo ⏳ 等待后端服务启动...
timeout /t 5 /nobreak >nul

REM 检查后端是否启动成功
set MAX_WAIT=30
set WAIT_TIME=0
:wait_backend
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 后端服务已启动
    goto backend_ready
)
timeout /t 1 /nobreak >nul
set /a WAIT_TIME+=1
if %WAIT_TIME% lss %MAX_WAIT% goto wait_backend

echo ❌ 后端服务启动超时
echo 请检查日志: logs\app_*.log
pause
exit /b 1

:backend_ready

REM 启动前端
echo.
echo ==========================================
echo 🎨 启动前端服务 (端口 7862)
echo ==========================================
start "RAG前端" python start_fronted.py
echo 前端服务已启动

REM 等待前端启动
echo.
echo ⏳ 等待前端服务启动...
timeout /t 5 /nobreak >nul

echo.
echo ==========================================
echo ✅ 启动完成！
echo ==========================================
echo.
echo 📌 服务地址：
echo   前端界面: http://localhost:7862
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo.
echo 💡 提示：
echo   - 两个黑色窗口会自动打开（后端和前端）
echo   - 关闭窗口即可停止服务
echo   - 浏览器会自动打开前端界面
echo.

REM 自动打开浏览器
timeout /t 3 /nobreak >nul
start http://localhost:7862

echo 按任意键退出本窗口（服务将继续运行）...
pause >nul