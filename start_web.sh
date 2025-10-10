#!/bin/bash

# 设置脚本编码
export LANG=zh_CN.UTF-8

echo "======================================================"
echo "🚀 快手极速版Web管理界面启动器"
echo "======================================================"
echo

# 检查Python是否可用
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python未安装或未添加到环境变量"
    echo "💡 请先安装Python: https://www.python.org/downloads/"
    exit 1
fi

# 优先使用python3
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PIP_CMD=pip3
else
    PYTHON_CMD=python
    PIP_CMD=pip
fi

echo "✅ Python环境检查通过 ($PYTHON_CMD)"

# 检查是否存在必要文件
required_files=("app.py" "index.html" "KSJSB_Launcher.py")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少文件: $file"
        exit 1
    fi
done

echo "✅ 必要文件检查通过"

# 安装依赖
echo "🔧 检查并安装依赖包..."
$PIP_CMD install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "⚠️ 依赖安装可能有问题，尝试继续启动..."
fi

# 启动Web服务
echo
echo "🌟 启动Web服务..."
echo "🌐 Web界面地址: http://localhost:5000"
echo "📡 请在浏览器中访问上述地址"
echo "======================================================"
echo "按 Ctrl+C 停止服务"
echo

$PYTHON_CMD start_web.py
