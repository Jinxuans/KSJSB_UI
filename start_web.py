#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手极速版Web管理界面启动脚本
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading

def check_requirements():
    """检查依赖包"""
    required_packages = [
        'flask',
        'flask_socketio', 
        'flask_cors'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n💡 请运行以下命令安装依赖:")
        print("   pip install -r requirements.txt")
        print("\n或手动安装:")
        for pkg in missing_packages:
            print(f"   pip install {pkg}")
        return False
    
    return True

def check_files():
    """检查必要文件"""
    required_files = ['app.py', 'index.html', 'KSJSB_Launcher.py']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少以下文件:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def create_default_files():
    """创建默认配置文件"""
    # 创建默认accounts.json
    if not os.path.exists('accounts.json'):
        with open('accounts.json', 'w', encoding='utf-8') as f:
            f.write('[]')
        print("✅ 已创建默认 accounts.json")
    
    # 创建默认config.json
    if not os.path.exists('config.json'):
        default_config = {
            "LX_KM": "",
            "LX_YH": False,
            "DEV_MODE": False,
            "LX_TASK_BLACKLIST": "",
            "MAX_CONCURRENCY": 5,
            "WITHDRAW_HOUR": None,
            "WITHDRAW_AMOUNT": None,
            "COIN_THRESHOLD": None
        }
        with open('config.json', 'w', encoding='utf-8') as f:
            import json
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print("✅ 已创建默认 config.json")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(3)  # 等待3秒让服务器启动
    try:
        webbrowser.open('http://localhost:5000')
        print("🌐 已在浏览器中打开管理界面")
    except Exception as e:
        print(f"⚠️ 无法自动打开浏览器: {e}")
        print("请手动在浏览器中访问: http://localhost:5000")

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 快手极速版Web管理界面启动器")
    print("=" * 60)
    
    # 检查依赖
    print("🔍 检查依赖包...")
    if not check_requirements():
        sys.exit(1)
    print("✅ 依赖包检查通过")
    
    # 检查文件
    print("🔍 检查必要文件...")
    if not check_files():
        print("\n❌ 文件检查失败，请确保所有必要文件都存在")
        sys.exit(1)
    print("✅ 文件检查通过")
    
    # 创建默认配置文件
    print("🔍 检查配置文件...")
    create_default_files()
    print("✅ 配置文件检查完成")
    
    print("\n🌟 启动Web服务...")
    print("📁 工作目录:", os.getcwd())
    print("🌐 Web界面地址: http://localhost:5000")
    print("=" * 60)
    
    # 启动浏览器（在后台线程中）
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        # 启动Flask应用
        from app import app, socketio
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n\n👋 正在关闭服务...")
    except Exception as e:
        print(f"\n❌ 服务启动失败: {e}")
        print("\n💡 可能的解决方案:")
        print("1. 检查端口5000是否被占用")
        print("2. 检查Python环境是否正确")
        print("3. 重新安装依赖: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == '__main__':
    main()
