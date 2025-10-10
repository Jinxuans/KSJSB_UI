@echo off
chcp 65001
echo ======================================================
echo 🚀 快手极速版Web管理界面启动器
echo ======================================================
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到环境变量
    echo 💡 请先安装Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查是否存在必要文件
if not exist "app.py" (
    echo ❌ 缺少文件: app.py
    pause
    exit /b 1
)

if not exist "index.html" (
    echo ❌ 缺少文件: index.html
    pause
    exit /b 1
)

if not exist "KSJSB_Launcher.py" (
    echo ❌ 缺少文件: KSJSB_Launcher.py
    pause
    exit /b 1
)

echo ✅ 必要文件检查通过

REM 安装依赖
echo 🔧 检查并安装依赖包...
pip install -r requirements.txt

REM 启动Web服务
echo.
echo 🌟 启动Web服务...
echo 🌐 Web界面地址: http://localhost:5000
echo 📡 请在浏览器中访问上述地址
echo ======================================================
echo 按 Ctrl+C 停止服务
echo.

python start_web.py

pause
